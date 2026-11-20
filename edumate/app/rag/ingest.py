import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pymupdf as fitz
import chromadb
from chromadb.utils import embedding_functions

from app.config import (
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    logger,
)
from app.db.database import insert_document

# Global Chroma client and collection handle
_chroma_client = None
_collection = None


def get_chroma_collection():
    """Initializes and returns the persistent Chroma collection with local embeddings."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    try:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Chroma collection '{CHROMA_COLLECTION_NAME}' loaded with local embeddings.")
        return _collection
    except Exception as e:
        logger.error(f"Failed to initialize Chroma collection: {e}", exc_info=True)
        raise RuntimeError(f"ChromaDB initialization failed: {e}")


def clean_text(raw_text: str) -> str:
    """Cleans extracted PDF text by normalizing spaces and stripping noise."""
    if not raw_text:
        return ""
    # Replace non-breaking spaces and strange unicode spaces
    cleaned = raw_text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Replace consecutive spaces and tabs with single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Collapse 3 or more newlines into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def chunk_page_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Splits a page's cleaned text into overlapping chunks of approx chunk_size characters."""
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # Try to break at a natural sentence boundary or newline
        split_idx = -1
        for sep in [". ", "\n\n", "\n", "? ", "! ", "; "]:
            candidate = text.rfind(sep, start + chunk_size // 2, end)
            if candidate != -1:
                split_idx = candidate + len(sep)
                break

        # If no punctuation boundary found, try space
        if split_idx == -1:
            candidate = text.rfind(" ", start + chunk_size // 2, end)
            if candidate != -1:
                split_idx = candidate + 1
            else:
                split_idx = end

        chunk_str = text[start:split_idx].strip()
        if chunk_str:
            chunks.append(chunk_str)

        # Advance start with overlap
        start = max(start + 1, split_idx - overlap)

    return chunks


def extract_and_chunk_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extracts text page by page from a PDF and chunks it with page metadata.
    
    Returns:
        List of dicts: [{"page_number": int, "chunk_index": int, "text": str}]
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise ValueError(f"Could not open or parse PDF file '{pdf_path.name}': {e}")

    if doc.page_count == 0:
        raise ValueError(f"The PDF '{pdf_path.name}' is empty (0 pages).")

    all_chunks = []
    global_chunk_idx = 0
    total_extracted_chars = 0

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = clean_text(page.get_text("text"))
        total_extracted_chars += len(page_text)

        if not page_text:
            continue

        page_chunks = chunk_page_text(page_text)
        for chunk in page_chunks:
            all_chunks.append({
                "page_number": page_num,
                "chunk_index": global_chunk_idx,
                "text": chunk
            })
            global_chunk_idx += 1

    doc.close()

    if total_extracted_chars < 20 or not all_chunks:
        raise ValueError(
            f"The PDF '{pdf_path.name}' has no readable text. It might be scanned/image-only or encrypted."
        )

    return all_chunks


def ingest_pdf_document(
    pdf_path: Path,
    file_name: str,
    student_id: str = "student_1",
    subject: str = "General",
    chapter: str = "General"
) -> Dict[str, Any]:
    """Ingests a PDF into SQLite metadata and Chroma vector database."""
    logger.info(f"Starting ingestion for '{file_name}' (Subject: {subject}, Chapter: {chapter})")

    # 1. Parse and chunk PDF
    chunks = extract_and_chunk_pdf(pdf_path)

    # 2. Get total pages
    doc = fitz.open(str(pdf_path))
    page_count = doc.page_count
    doc.close()

    # 3. Store document metadata in SQLite
    doc_id = insert_document(
        student_id=student_id,
        file_name=file_name,
        subject=subject,
        chapter=chapter,
        page_count=page_count,
        chunk_count=len(chunks)
    )

    # 4. Prepare batch vectors for Chroma
    collection = get_chroma_collection()

    ids = []
    documents = []
    metadatas = []

    for item in chunks:
        chunk_id = f"doc_{doc_id}_page_{item['page_number']}_chunk_{item['chunk_index']}"
        ids.append(chunk_id)
        documents.append(item["text"])
        metadatas.append({
            "document_id": doc_id,
            "document_name": file_name,
            "page_number": item["page_number"],
            "chunk_index": item["chunk_index"],
            "subject": subject,
            "chapter": chapter
        })

    # Add to Chroma in batches to prevent payload limits
    batch_size = 64
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )

    logger.info(f"Ingested doc_id={doc_id}: {len(chunks)} chunks across {page_count} pages stored in Chroma.")

    return {
        "document_id": doc_id,
        "document_name": file_name,
        "number_of_pages": page_count,
        "number_of_chunks": len(chunks),
        "subject": subject,
        "chapter": chapter
    }

