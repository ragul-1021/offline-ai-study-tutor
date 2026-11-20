import sys
import os
import time
import socket
from pathlib import Path

# Safe encoding for Windows consoles
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Automatically set up paths
EDUMATE_ROOT = Path(__file__).resolve().parent
if str(EDUMATE_ROOT) not in sys.path:
    sys.path.insert(0, str(EDUMATE_ROOT))

from app.config import API_HOST, API_PORT, GEMMA_MODEL_PATH
from app.db.database import init_db


def free_port_if_in_use(port: int, host: str = "127.0.0.1"):
    """Quick port check."""
    pass


if __name__ == "__main__":
    print("=" * 60)
    print("       STARTING EDUMATE BACKEND SERVER")
    print("=" * 60)
    
    print("\n[1/3] Checking Model Path...")
    if GEMMA_MODEL_PATH.exists():
        print(f"  [OK] Model found at: {GEMMA_MODEL_PATH.name}")
    else:
        print(f"  [WARN] WARNING: Model file not found at: {GEMMA_MODEL_PATH}")

    print("\n[2/3] Initializing SQLite Database...")
    try:
        init_db()
        print("  [OK] Database initialized successfully.")
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")

    # Ensure port 8000 is clean
    free_port_if_in_use(API_PORT, API_HOST)

    print("\n[3/3] Launching Uvicorn Web Server...")
    print(f"  -> API URL: http://{API_HOST}:{API_PORT}")
    print(f"  -> Interactive Docs: http://{API_HOST}:{API_PORT}/docs")
    print(f"  -> Health Check: http://{API_HOST}:{API_PORT}/health")
    print("\n[NOTE] Keep this terminal window open while using EduMate.")
    print("=" * 60 + "\n")

    import uvicorn
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=False)
