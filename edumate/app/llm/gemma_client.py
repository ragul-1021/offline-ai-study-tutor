import os
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Generator

# Automatically discover and add NVIDIA CUDA runtime & cuBLAS DLLs from pip packages if available
if hasattr(os, "add_dll_directory"):
    try:
        import site
        for sp in site.getsitepackages():
            for sub in ["nvidia/cuda_runtime/bin", "nvidia/cublas/bin", "llama_cpp/lib"]:
                p = Path(sp) / sub
                if p.exists():
                    os.add_dll_directory(str(p))
    except Exception:
        pass

from app.config import (
    GEMMA_MODEL_PATH,
    GEMMA_N_CTX,
    GEMMA_THREADS,
    GEMMA_BATCH_SIZE,
    GEMMA_N_GPU_LAYERS,
    CPU_COUNT,
    logger,
)

# Mutex to ensure thread-safe llama-cpp inference
_llm_lock = threading.Lock()
_model_instance = None


def get_gemma_model():
    """Lazy-loads and caches the singleton Llama model instance."""
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    with _llm_lock:
        if _model_instance is not None:
            return _model_instance

        if not GEMMA_MODEL_PATH.exists():
            err_msg = f"Model file not found at: {GEMMA_MODEL_PATH}"
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)

        logger.info(f"Loading Gemma model from: {GEMMA_MODEL_PATH}")
        logger.info(f"Optimized settings -> n_ctx: {GEMMA_N_CTX}, threads: {GEMMA_THREADS}, batch: {GEMMA_BATCH_SIZE}, gpu_layers: {GEMMA_N_GPU_LAYERS}")

        try:
            from llama_cpp import Llama
            _model_instance = Llama(
                model_path=str(GEMMA_MODEL_PATH),
                n_ctx=GEMMA_N_CTX,
                n_threads=GEMMA_THREADS,
                n_threads_batch=CPU_COUNT,
                n_batch=GEMMA_BATCH_SIZE,
                n_gpu_layers=GEMMA_N_GPU_LAYERS,
                verbose=False,
            )
            logger.info("Gemma model loaded successfully!")
            return _model_instance
        except Exception as e:
            logger.error(f"Failed to load Gemma model: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize Gemma GGUF model: {e}")


def generate_answer(prompt: str, max_tokens: int = 384, temperature: float = 0.2) -> str:
    """Generates an answer from the local Gemma GGUF model for a given prompt."""
    model = get_gemma_model()
    messages = [{"role": "user", "content": prompt}]

    with _llm_lock:
        try:
            response = model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            answer = response["choices"][0]["message"]["content"]
            return answer.strip()
        except Exception as e:
            logger.error(f"Inference error with Gemma model: {e}", exc_info=True)
            raise RuntimeError(f"Gemma model generation failed: {e}")


def generate_answer_stream(prompt: str, max_tokens: int = 384, temperature: float = 0.2) -> Generator[str, None, None]:
    """Yields token strings in real-time as they are computed by the model."""
    model = get_gemma_model()
    messages = [{"role": "user", "content": prompt}]

    with _llm_lock:
        try:
            stream = model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"Streaming inference error: {e}", exc_info=True)
            yield f"\n[Error generating response: {e}]"


def check_llm_health() -> Dict[str, Any]:
    """Returns the health status and metadata of the local Gemma model."""
    file_exists = GEMMA_MODEL_PATH.exists()
    is_loaded = _model_instance is not None

    return {
        "status": "healthy" if file_exists else "model_file_missing",
        "model_path": str(GEMMA_MODEL_PATH),
        "file_exists": file_exists,
        "is_loaded": is_loaded,
        "n_ctx": GEMMA_N_CTX,
        "threads": GEMMA_THREADS,
        "gpu_layers": GEMMA_N_GPU_LAYERS,
    }
