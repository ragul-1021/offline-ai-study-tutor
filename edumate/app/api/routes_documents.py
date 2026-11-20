import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.config import UPLOADS_DIR, logger
from app.rag.ingest import ingest_pdf_document, get_chroma_collection
from app.db.database import list_documents, get_document, get_db_connection
from app.db.models import DocumentResponse

router = APIRouter(tags=["Documents"])


@router.post("/upload-document", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF study notes or textbook chapter"),
    student_id: str = Form("student_1", description="Student ID"),
    subject: str = Form("General", description="Subject name"),
    chapter: str = Form("General", description="Chapter or unit name"),
):
    """Uploads a PDF study document, extracts text page by page, chunks, embeds, and stores in SQLite and Chroma."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported (.pdf extension required)."
        )

    # Save uploaded file to disk safely
    clean_filename = Path(file.filename).name
    save_path = UPLOADS_DIR / clean_filename

    # If file with same name exists, append timestamp or counter
    counter = 1
    stem = save_path.stem
    while save_path.exists():
        save_path = UPLOADS_DIR / f"{stem}_{counter}.pdf"
        counter += 1

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file to disk: {str(e)}"
        )

    # Ingest document into SQLite & Chroma
    try:
        result = ingest_pdf_document(
            pdf_path=save_path,
            file_name=save_path.name,
            student_id=student_id,
            subject=subject,
            chapter=chapter,
        )
        return DocumentResponse(**result)
    except ValueError as val_err:
        # E.g. empty or unreadable PDF
        if save_path.exists():
            save_path.unlink()  # Clean up failed file
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err)
        )
    except Exception as err:
        logger.error(f"Error during PDF ingestion: {err}", exc_info=True)
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index PDF: {str(err)}"
        )


@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(student_id: Optional[str] = None):
    """Retrieves all indexed study documents."""
    docs = list_documents(student_id=student_id)
    return [
        DocumentResponse(
            document_id=d["document_id"],
            document_name=d["file_name"],
            number_of_pages=d["page_count"] or 0,
            number_of_chunks=d["chunk_count"] or 0,
            subject=d.get("subject", "General"),
            chapter=d.get("chapter", "General"),
        )
        for d in docs
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: int):
    """Retrieves metadata for a specific document."""
    doc = get_document(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentResponse(
        document_id=doc["document_id"],
        document_name=doc["file_name"],
        number_of_pages=doc["page_count"] or 0,
        number_of_chunks=doc["chunk_count"] or 0,
        subject=doc.get("subject", "General"),
        chapter=doc.get("chapter", "General"),
    )

