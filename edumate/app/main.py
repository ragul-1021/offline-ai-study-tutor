import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of execution directory
EDUMATE_ROOT = Path(__file__).resolve().parent.parent
if str(EDUMATE_ROOT) not in sys.path:
    sys.path.insert(0, str(EDUMATE_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import API_HOST, API_PORT, logger
from app.db.database import init_db
from app.llm.gemma_client import check_llm_health, get_gemma_model
from app.api.routes_documents import router as documents_router
from app.api.routes_chat import router as chat_router
from app.api.routes_quiz import router as quiz_router
from app.api.routes_progress import router as progress_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing EduMate database and services...")
    init_db()
    logger.info("Pre-warming Gemma LLM model into RAM...")
    try:
        get_gemma_model()
        logger.info("Gemma LLM model pre-warmed successfully!")
    except Exception as e:
        logger.warning(f"Could not pre-warm model at startup: {e}")
    logger.info("EduMate backend is ready to serve requests.")
    yield
    # Shutdown actions
    logger.info("Shutting down EduMate backend.")


app = FastAPI(
    title="EduMate - Offline AI Study Tutor API",
    description="A fully local, offline RAG-powered study tutor built with Gemma GGUF, Chroma, and PyMuPDF.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Streamlit / web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(quiz_router)
app.include_router(progress_router)


@app.get("/", tags=["General"])
def root():
    return {
        "status": "online",
        "app": "EduMate Offline AI Study Tutor",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["General"])
def health_check():
    """Health check verifying model configuration and database availability."""
    llm_health = check_llm_health()
    return {
        "api_status": "healthy",
        "llm": llm_health,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=False)
