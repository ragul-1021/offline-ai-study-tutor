import sys
import time
import os
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.prompt_templates import build_direct_chat_prompt, build_quiz_generation_prompt
from app.llm.gemma_client import generate_answer
from app.api.routes_quiz import extract_json_from_llm
from app.rag.retriever import retrieve_relevant_chunks

def test_direct_inference():
    print("\n--- 1. Testing Fast Direct Text-to-Text Mode ---")
    prompt = build_direct_chat_prompt(
        question="What is Newton's second law of motion in simple terms?",
        student_level="Class 12"
    )
    t0 = time.perf_counter()
    answer = generate_answer(prompt, max_tokens=150, temperature=0.3)
    elapsed = time.perf_counter() - t0
    print(f"Elapsed Time: {elapsed:.2f}s")
    print(f"Direct Response:\n{answer.strip()}\n")
    assert len(answer) > 20, "Answer is too short!"
    print("Direct text-to-text test PASSED!")

def test_fast_quiz_generation():
    print("\n--- 2. Testing Fast Practice Quiz Generation ---")
    # Retrieve 2 chunks
    chunks = retrieve_relevant_chunks(query="Physics nanoparticles", top_k=2)
    if not chunks:
        # Fallback dummy chunk if Chroma has no docs yet in test
        chunks = [{
            "chunk_id": "test_1",
            "document_name": "TestNotes.pdf",
            "page_number": 1,
            "text": "Nanoparticles are particles between 1 and 100 nanometres in size. They exhibit high surface area to volume ratio."
        }]
    print(f"Retrieved {len(chunks)} chunks for prompt.")

    prompt = build_quiz_generation_prompt(
        topic="Nanoparticles",
        difficulty="medium",
        number_of_questions=2,
        question_types=["mcq", "short_answer"],
        retrieved_chunks=chunks
    )

    t0 = time.perf_counter()
    raw = generate_answer(prompt, max_tokens=350, temperature=0.2)
    elapsed = time.perf_counter() - t0
    print(f"Quiz Generation Time: {elapsed:.2f}s")
    print(f"Raw Output:\n{raw}\n")

    parsed = extract_json_from_llm(raw)
    print("Parsed JSON:", parsed)
    assert parsed is not None and "questions" in parsed and len(parsed["questions"]) > 0, "Failed to parse questions JSON"
    print(f"Successfully generated and parsed {len(parsed['questions'])} questions!")
    print("Quiz generation test PASSED!")

if __name__ == "__main__":
    test_direct_inference()
    test_fast_quiz_generation()
