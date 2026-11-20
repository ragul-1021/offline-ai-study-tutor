import sys
import os
import time
from pathlib import Path

# Add edumate to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import llama_cpp
import chromadb
from app.config import GEMMA_MODEL_PATH, CHROMA_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL_NAME
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.prompt_templates import build_rag_prompt

print("=" * 70)
print("     EDUMATE INFERENCE PERFORMANCE & PROFILING DIAGNOSTIC")
print("=" * 70)

# -------------------------------------------------------------
# 1. HARDWARE & BACKEND INSPECTION
# -------------------------------------------------------------
print("\n[1] BACKEND & CAPABILITIES INSPECTION")
print(f"  * llama_cpp version: {llama_cpp.__version__}")
gpu_offload = llama_cpp.llama_supports_gpu_offload()
print(f"  * llama_supports_gpu_offload: {gpu_offload}")
print(f"  * llama_supports_mmap: {llama_cpp.llama_supports_mmap()}")
print(f"  * llama_supports_mlock: {llama_cpp.llama_supports_mlock()}")

if not gpu_offload:
    print("  [!] CRITICAL FINDING: llama_cpp backend was compiled WITHOUT GPU support (CPU only).")
    print("      Even if n_gpu_layers is passed, 0 layers will be offloaded to the GPU.")

# -------------------------------------------------------------
# 2. MODEL LOADING MEASUREMENT
# -------------------------------------------------------------
print("\n[2] MODEL LOAD TIMING")
t0 = time.perf_counter()
model = llama_cpp.Llama(
    model_path=str(GEMMA_MODEL_PATH),
    n_ctx=2048,
    n_threads=6,
    n_batch=512,
    verbose=False,
)
load_time = time.perf_counter() - t0
print(f"  - Model path: {GEMMA_MODEL_PATH.name}")
print(f"  - Model file size: {GEMMA_MODEL_PATH.stat().st_size / (1024**3):.2f} GB")
print(f"  - Initial model load time: {load_time:.3f} s")

# -------------------------------------------------------------
# 3. DIRECT INFERENCE BENCHMARK (NO RAG, 128 TOKENS)
# -------------------------------------------------------------
print("\n[3] DIRECT INFERENCE BENCHMARK (128 TOKENS, NO RAG)")
direct_prompt = "Explain the fundamental principles of energy conservation in physics."
messages = [{"role": "user", "content": direct_prompt}]

# Warm-up single token
model.create_chat_completion(messages=[{"role": "user", "content": "Hi"}], max_tokens=1)

t_start = time.perf_counter()
t_first_token = None
tokens_generated = 0

stream = model.create_chat_completion(
    messages=messages,
    max_tokens=128,
    temperature=0.2,
    stream=True
)

for chunk in stream:
    delta = chunk["choices"][0].get("delta", {}).get("content", "")
    if delta:
        if t_first_token is None:
            t_first_token = time.perf_counter()
        tokens_generated += 1

t_end = time.perf_counter()
direct_ttft = (t_first_token - t_start) if t_first_token else 0.0
direct_total = t_end - t_start
direct_gen_time = t_end - (t_first_token or t_start)
direct_tps = (tokens_generated - 1) / direct_gen_time if direct_gen_time > 0 and tokens_generated > 1 else 0.0

print(f"  - Prompt length: {len(direct_prompt)} chars")
print(f"  - Generated tokens: {tokens_generated}")
print(f"  - Time to First Token (TTFT): {direct_ttft:.3f} s")
print(f"  - Generation time (excl. TTFT): {direct_gen_time:.3f} s")
print(f"  - Total inference time: {direct_total:.3f} s")
print(f"  - Generation speed: {direct_tps:.2f} tokens/sec")

# -------------------------------------------------------------
# 4. RAG PIPELINE DETAILED TIMING BREAKDOWN
# -------------------------------------------------------------
print("\n[4] RAG PIPELINE TIMING BREAKDOWN")
rag_query = "BASICS OF NANOCHEMISTRY"

# Step A: Query Embedding + Retrieval
t_ret_start = time.perf_counter()
chunks = retrieve_relevant_chunks(rag_query, top_k=4)
t_ret_end = time.perf_counter()
retrieval_time = t_ret_end - t_ret_start
print(f"  - Step A - Chroma Retrieval & Embedding time: {retrieval_time:.4f} s (retrieved {len(chunks)} chunks)")

# Step B: Prompt Construction
t_prompt_start = time.perf_counter()
rag_prompt = build_rag_prompt(rag_query, chunks, student_level="Class 12")
t_prompt_end = time.perf_counter()
prompt_construct_time = t_prompt_end - t_prompt_start
prompt_char_len = len(rag_prompt)
# Approximate tokens in prompt (~4 chars/token)
approx_prompt_tokens = prompt_char_len // 4
print(f"  - Step B - Prompt Construction time: {prompt_construct_time:.6f} s")
print(f"  - Prompt size: {prompt_char_len} chars (~{approx_prompt_tokens} tokens)")

# Step C: RAG Generation
t_rag_start = time.perf_counter()
t_rag_first = None
rag_tokens_generated = 0

rag_stream = model.create_chat_completion(
    messages=[{"role": "user", "content": rag_prompt}],
    max_tokens=128,
    temperature=0.2,
    stream=True
)

for chunk in rag_stream:
    delta = chunk["choices"][0].get("delta", {}).get("content", "")
    if delta:
        if t_rag_first is None:
            t_rag_first = time.perf_counter()
        rag_tokens_generated += 1

t_rag_end = time.perf_counter()
rag_ttft = (t_rag_first - t_rag_start) if t_rag_first else 0.0
rag_total = t_rag_end - t_rag_start
rag_gen_time = t_rag_end - (t_rag_first or t_rag_start)
rag_tps = (rag_tokens_generated - 1) / rag_gen_time if rag_gen_time > 0 and rag_tokens_generated > 1 else 0.0

print(f"  - Step C - RAG TTFT (Prompt Ingestion / Prefill): {rag_ttft:.3f} s")
print(f"  - Step D - RAG Generation time: {rag_gen_time:.3f} s ({rag_tokens_generated} tokens)")
print(f"  - Step E - RAG Generation speed: {rag_tps:.2f} tokens/sec")
print(f"  - Total RAG response time: {rag_total + retrieval_time:.3f} s")

# -------------------------------------------------------------
# 5. DIRECT VS RAG COMPARISON
# -------------------------------------------------------------
print("\n[5] DIRECT VS RAG COMPARISON")
print(f"  {'Metric':<30} | {'Direct (Short Prompt)':<22} | {'RAG (Context + Rules)':<22}")
print(f"  {'-'*30}-|-{'-'*22}-|-{'-'*22}")
print(f"  {'Prompt Size':<30} | {len(direct_prompt):>6} chars (~{len(direct_prompt)//4:>3} tok) | {prompt_char_len:>6} chars (~{approx_prompt_tokens:>3} tok)")
print(f"  {'Time to First Token (TTFT)':<30} | {direct_ttft:>19.3f} s | {rag_ttft:>19.3f} s")
print(f"  {'Token Generation Speed':<30} | {direct_tps:>13.2f} tok/s | {rag_tps:>13.2f} tok/s")
print(f"  {'Total Latency (128 tok)':<30} | {direct_total:>19.3f} s | {rag_total + retrieval_time:>19.3f} s")

print("\n" + "=" * 70)
