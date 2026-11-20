from typing import List, Dict, Any, Optional
from app.rag.ingest import get_chroma_collection
from app.config import DEFAULT_TOP_K, logger


def retrieve_relevant_chunks(
    query: str,
    document_ids: Optional[List[int]] = None,
    top_k: int = DEFAULT_TOP_K,
    subject: Optional[str] = None,
    chapter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves the top_k most similar chunks for a query from ChromaDB with optional filtering.
    
    Args:
        query: User question or topic string.
        document_ids: Optional list of integer document_ids to filter by.
        top_k: Number of chunks to retrieve (default: 4).
        subject: Optional subject string filter.
        chapter: Optional chapter string filter.

    Returns:
        List of dicts: [
            {
                "document_id": int,
                "document_name": str,
                "page_number": int,
                "chunk_index": int,
                "subject": str,
                "chapter": str,
                "text": str,
                "distance": float
            }
        ]
    """
    collection = get_chroma_collection()

    total_chunks = collection.count()
    if total_chunks == 0:
        logger.warning("Chroma collection is currently empty. No chunks to retrieve.")
        return []

    # Build Chroma 'where' filter
    where_clauses = []

    if document_ids:
        if len(document_ids) == 1:
            where_clauses.append({"document_id": document_ids[0]})
        elif len(document_ids) > 1:
            where_clauses.append({"document_id": {"$in": document_ids}})

    if subject:
        where_clauses.append({"subject": subject})

    if chapter:
        where_clauses.append({"chapter": chapter})

    where_filter = None
    if len(where_clauses) == 1:
        where_filter = where_clauses[0]
    elif len(where_clauses) > 1:
        where_filter = {"$and": where_clauses}

    actual_k = min(top_k, total_chunks)

    try:
        results = collection.query(
            query_texts=[query],
            n_results=actual_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"Error querying ChromaDB: {e}", exc_info=True)
        # If where clause failed (e.g., no documents match filter), return empty
        return []

    if not results or not results.get("documents") or not results["documents"][0]:
        return []

    retrieved_chunks = []
    docs = results["documents"][0]
    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
    dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

    for doc_text, meta, dist in zip(docs, metas, dists):
        retrieved_chunks.append({
            "document_id": meta.get("document_id", 0),
            "document_name": meta.get("document_name", "Unknown Document"),
            "page_number": meta.get("page_number", 1),
            "chunk_index": meta.get("chunk_index", 0),
            "subject": meta.get("subject", "General"),
            "chapter": meta.get("chapter", "General"),
            "text": doc_text,
            "distance": round(dist, 4) if dist is not None else 0.0
        })

    logger.info(f"Retrieved {len(retrieved_chunks)} chunks for query: '{query[:40]}...'")
    return retrieved_chunks

