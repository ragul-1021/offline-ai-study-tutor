import os
import sys
import logging
from pathlib import Path

# Define base paths
APP_DIR = Path(__file__).resolve().parent
EDUMATE_DIR = APP_DIR.parent
DATA_DIR = EDUMATE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
DB_PATH = DATA_DIR / "edumate.db"
MODELS_DIR = EDUMATE_DIR / "models"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from edumate/.env
ENV_FILE = EDUMATE_DIR / ".env"
try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE)
    else:
        load_dotenv()
except ImportError:
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# Gemma GGUF model settings
DEFAULT_MODEL_PATH = MODELS_DIR / "google_gemma-4-E4B-it-qat-q4_0-gguf" / "gemma-4-E4B_q4_0-it.gguf"
raw_model_path = os.getenv("GEMMA_MODEL_PATH", str(DEFAULT_MODEL_PATH))
if not Path(raw_model_path).is_absolute():
    GEMMA_MODEL_PATH = (EDUMATE_DIR / raw_model_path).resolve()
else:
    GEMMA_MODEL_PATH = Path(raw_model_path).resolve()

# Performance tuning: 4096 context window supports complete 16-mark exhaustive answers without cutoff
GEMMA_N_CTX = int(os.getenv("GEMMA_N_CTX", "4096"))
CPU_COUNT = os.cpu_count() or 4
GEMMA_THREADS = int(os.getenv("GEMMA_THREADS", str(max(1, CPU_COUNT // 2))))
GEMMA_BATCH_SIZE = int(os.getenv("GEMMA_BATCH_SIZE", "512"))
GEMMA_N_GPU_LAYERS = int(os.getenv("GEMMA_N_GPU_LAYERS", "0"))

# Enforce local/offline execution for HuggingFace Hub to prevent network timeout retries
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Resolve local snapshot path for embedding model to avoid online repository checks
CACHE_SNAPSHOTS = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
if CACHE_SNAPSHOTS.exists():
    _snaps = list(CACHE_SNAPSHOTS.glob("*"))
    LOCAL_EMBEDDING_MODEL_PATH = str(_snaps[0]) if _snaps else "sentence-transformers/all-MiniLM-L6-v2"
else:
    LOCAL_EMBEDDING_MODEL_PATH = "sentence-transformers/all-MiniLM-L6-v2"

# RAG & Embeddings settings
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", LOCAL_EMBEDDING_MODEL_PATH)
CHROMA_COLLECTION_NAME = "edumate_study_materials"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 4

# API settings
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Configure logging to stdout so Windows PowerShell does not treat info logs as NativeCommandError
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("edumate")
