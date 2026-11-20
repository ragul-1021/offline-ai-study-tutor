import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.prompt_templates import (
    extract_marks_from_question,
    get_effective_marks,
    get_mark_guidelines,
    build_direct_chat_prompt,
    build_rag_prompt
)
from app.api.routes_chat import calculate_token_budget

def test_marks_extraction():
    print("--- Testing Marks Extraction ---")
    assert extract_marks_from_question("Explain AC generator for 12 marks") == 12
    assert extract_marks_from_question("What is Ohm's law (2 marks)") == 2
    assert extract_marks_from_question("Explain photo-electric effect in 5 marks question") == 5
    assert extract_marks_from_question("Give a 16-mark essay on transformers") == 16
    assert extract_marks_from_question("Just explain Ohm's Law please") is None
    print("Marks extraction PASSED!")

def test_effective_marks_and_token_budget():
    print("--- Testing Effective Marks and Token Budgets ---")
    # Explicit target_marks takes priority
    assert get_effective_marks(12, "Explain Ohm's law") == 12
    assert get_effective_marks(None, "Explain Ohm's law for 5 marks") == 5
    assert get_effective_marks(None, "Explain Ohm's law") is None

    # Token budget scaling (optimized for edge CPU)
    assert calculate_token_budget(2, "") == 130
    assert calculate_token_budget(5, "") == 280
    assert calculate_token_budget(10, "") == 550
    assert calculate_token_budget(12, "") == 550
    assert calculate_token_budget(16, "") == 750
    assert calculate_token_budget(None, "no marks mentioned", default_tokens=300) == 300
    # Auto detection in token budget
    assert calculate_token_budget(None, "Explain transformer for 12 marks") == 550
    print("Effective marks and token budgets PASSED!")

def test_prompt_generation_with_marks():
    print("--- Testing Prompt Generation ---")
    # 1. 12 marks direct prompt
    p12 = build_direct_chat_prompt("Explain AC Generator", student_level="Class 12", target_marks=12)
    assert "12-MARK" in p12
    assert "Introduction & Formal Definition" in p12
    assert "Detailed Mechanism & Working" in p12
    assert "Mathematical Formula" in p12

    # 2. 2 marks direct prompt
    p2 = build_direct_chat_prompt("Define Ohm's law", student_level="Class 12", target_marks=2)
    assert "2-MARK" in p2
    assert "40-60 words" in p2

    # 3. General (None) direct prompt
    p_gen = build_direct_chat_prompt("Explain Ohm's law", student_level="Class 12", target_marks=None)
    assert "EXAM SPECIFICATION" not in p_gen
    assert "200-250 words" in p_gen

    # 4. RAG prompt with 12 marks
    chunks = [{"document_name": "Physics.pdf", "page_number": 5, "text": "An AC generator converts mechanical energy..."}]
    p_rag = build_rag_prompt("Explain AC generator", chunks, student_level="Class 12", target_marks=12)
    assert "12 MARKS" in p_rag
    assert "CRITICAL EXAM REQUIREMENT" in p_rag
    print("Prompt generation with marks PASSED!")

if __name__ == "__main__":
    test_marks_extraction()
    test_effective_marks_and_token_budget()
    test_prompt_generation_with_marks()
    print("\nALL MARKS TESTS COMPLETED SUCCESSFULLY!")
