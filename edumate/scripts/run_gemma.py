import os
from pathlib import Path
from llama_cpp import Llama

MODEL_PATH = Path(__file__).resolve().parent / "model" / "google_gemma-4-E4B-it-qat-q4_0-gguf" / "gemma-4-E4B_q4_0-it.gguf"

# Hardware thread optimization
CPU_COUNT = os.cpu_count() or 4
OPTIMAL_THREADS = max(1, CPU_COUNT // 2)

model = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=2048,
    n_threads=OPTIMAL_THREADS,
    n_threads_batch=CPU_COUNT,
    n_batch=512,
    verbose=False,
)
messages = []
print("Gemma ready. Type 'exit' to quit.")

while True:
    question = input("\nYou: ")
    if question.strip().lower() in {"exit", "quit"}:
        break
    messages.append({"role": "user", "content": question})
    print("Gemma: ", end="", flush=True)

    # Real-time token streaming to terminal
    response_stream = model.create_chat_completion(
        messages=messages,
        max_tokens=256,
        stream=True,
    )
    full_response = []
    for chunk in response_stream:
        delta = chunk["choices"][0].get("delta", {}).get("content", "")
        if delta:
            print(delta, end="", flush=True)
            full_response.append(delta)

    print()
    messages.append({"role": "assistant", "content": "".join(full_response)})
