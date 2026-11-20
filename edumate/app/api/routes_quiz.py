import json
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status

from app.db.models import (
    QuizGenerateRequest,
    QuizResponse,
    QuizQuestionItem,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.prompt_templates import (
    build_quiz_generation_prompt,
    build_short_answer_eval_prompt,
)
from app.llm.gemma_client import generate_answer
from app.db.database import (
    insert_quiz,
    insert_quiz_question,
    get_question,
    insert_attempt,
    get_quiz_with_questions,
)
from app.config import logger

router = APIRouter(tags=["Quiz"])


def extract_json_from_llm(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts JSON from an LLM response with repair and regex item fallback."""
    if not text:
        return None
    text = text.strip()

    # 1. Clean markdown code fences if present
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    candidate_text = code_match.group(1).strip() if code_match else text

    # 2. Try direct json parse
    try:
        data = json.loads(candidate_text)
        if isinstance(data, dict) and "questions" in data and len(data["questions"]) > 0:
            return data
    except Exception:
        pass

    # 3. Try slice from first { to last }
    first_brace = candidate_text.find("{")
    last_brace = candidate_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        sliced = candidate_text[first_brace:last_brace + 1]
        try:
            data = json.loads(sliced)
            if isinstance(data, dict) and "questions" in data and len(data["questions"]) > 0:
                return data
        except Exception:
            # Try auto-repair trailing commas
            cleaned = re.sub(r",\s*([\]}])", r"\1", sliced)
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict) and "questions" in data and len(data["questions"]) > 0:
                    return data
            except Exception:
                pass

    # 4. Truncation Auto-Repair: If generation was cut off mid-array, close the nearest object
    if first_brace != -1:
        truncated = candidate_text[first_brace:]
        last_obj_close = truncated.rfind("}")
        if last_obj_close != -1:
            repaired = truncated[:last_obj_close + 1] + "\n]}"
            try:
                data = json.loads(repaired)
                if isinstance(data, dict) and "questions" in data and len(data["questions"]) > 0:
                    return data
            except Exception:
                pass

    # 5. Regex Object Recovery Fallback: Extract every complete question object individually
    recovered_questions = []
    q_matches = re.finditer(
        r'\{[^{}]*?"question_text"\s*:\s*"([^"]+)"[^{}]*?"question_type"\s*:\s*"([^"]+)"[^{}]*?\}',
        text,
        re.DOTALL
    )
    for m in q_matches:
        try:
            q_obj = json.loads(m.group(0))
            recovered_questions.append(q_obj)
        except Exception:
            pass

    if recovered_questions:
        return {"questions": recovered_questions}

    return None


@router.post("/generate-quiz", response_model=QuizResponse)
def generate_quiz(request: QuizGenerateRequest):
    """Generates a practice quiz strictly from retrieved study material and saves it in SQLite.
    
    Optimized for CPU: Uses 2-3 focused chunks to avoid prompt prefill bottleneck.
    """
    # 1. Retrieve 2-3 focused chunks to keep prompt prefill under 4 seconds
    max_chunks = 2 if request.number_of_questions <= 3 else 3
    chunks = retrieve_relevant_chunks(
        query=request.topic,
        document_ids=request.document_ids,
        top_k=max_chunks,
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No study material found for the selected topic and documents. Please upload notes first."
        )

    # 2. Build prompt
    prompt = build_quiz_generation_prompt(
        topic=request.topic,
        difficulty=request.difficulty,
        number_of_questions=request.number_of_questions,
        question_types=request.question_types,
        retrieved_chunks=chunks,
    )

    # Dynamic token allocation (approx 130 tokens per question)
    tokens_budget = min(850, max(380, request.number_of_questions * 140))

    # 3. Query LLM and parse JSON
    parsed_json = None
    raw_response = ""

    for attempt in range(2):
        try:
            if attempt == 0:
                raw_response = generate_answer(prompt, max_tokens=tokens_budget, temperature=0.2)
            else:
                logger.warning("Retrying quiz generation with stricter JSON enforcement...")
                strict_prompt = (
                    f"{prompt}\n\n"
                    "CRITICAL: Output pure valid JSON only starting with '{' and ending with '}'. No commentary."
                )
                raw_response = generate_answer(strict_prompt, max_tokens=tokens_budget, temperature=0.1)

            parsed_json = extract_json_from_llm(raw_response)
            if parsed_json and "questions" in parsed_json and isinstance(parsed_json["questions"], list) and len(parsed_json["questions"]) > 0:
                break
        except Exception as e:
            logger.error(f"Error calling Gemma on attempt {attempt}: {e}")

    if not parsed_json or "questions" not in parsed_json or not parsed_json["questions"]:
        logger.error(f"Failed to extract valid JSON. Raw output: {raw_response[:300]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate valid quiz questions from the material. Please try a more specific topic or chapter."
        )

    # 4. Save quiz in SQLite
    quiz_id = insert_quiz(
        student_id=request.student_id,
        document_ids=request.document_ids,
        topic=request.topic,
        difficulty=request.difficulty,
    )

    # 5. Save individual questions in SQLite
    saved_questions: List[QuizQuestionItem] = []
    first_chunk_meta = chunks[0] if chunks else {}

    for q_data in parsed_json["questions"][:request.number_of_questions]:
        q_text = q_data.get("question_text", "Question")
        q_type = q_data.get("question_type", "mcq").lower()
        options = q_data.get("options")
        correct_ans = str(q_data.get("correct_answer", ""))
        explanation = q_data.get("explanation", "")

        q_id = insert_quiz_question(
            quiz_id=quiz_id,
            question_text=q_text,
            question_type=q_type,
            options=options,
            correct_answer=correct_ans,
            explanation=explanation,
            source_metadata={
                "document_name": first_chunk_meta.get("document_name"),
                "page_number": first_chunk_meta.get("page_number"),
            }
        )

        saved_questions.append(
            QuizQuestionItem(
                question_id=q_id,
                question_text=q_text,
                question_type=q_type,
                options=options,
                explanation=explanation,
            )
        )

    return QuizResponse(
        quiz_id=quiz_id,
        topic=request.topic,
        difficulty=request.difficulty,
        questions=saved_questions,
    )


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
def submit_answer(request: SubmitAnswerRequest):
    """Evaluates a student's answer, logs the attempt, and returns feedback."""
    q_data = get_question(request.question_id)
    if not q_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {request.question_id} not found."
        )

    student_ans = request.student_answer.strip()
    if not student_ans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer cannot be empty."
        )

    q_type = q_data.get("question_type", "mcq").lower()
    correct_ans = str(q_data.get("correct_answer", "")).strip()
    explanation = q_data.get("explanation", "")

    is_correct = False
    score = 0.0
    feedback = ""
    suggested_revision_topic = "General Review"

    # Evaluation Strategy
    if q_type == "mcq":
        clean_student = student_ans.upper().strip()
        clean_correct = correct_ans.upper().strip()

        student_letter = clean_student[0] if clean_student else ""
        correct_letter = clean_correct[0] if clean_correct else ""

        if clean_student == clean_correct or (student_letter and student_letter == correct_letter):
            is_correct = True
            score = 1.0
            feedback = f"Correct! {explanation}"
            suggested_revision_topic = "Great work! Keep practicing."
        else:
            is_correct = False
            score = 0.0
            feedback = f"Incorrect. The correct answer was: {correct_ans}. {explanation}"
            suggested_revision_topic = "Review this chapter's key formulas and definitions."

    else:
        # Conceptual Short Answer: evaluate with local Gemma LLM
        context = explanation or "Refer to uploaded course textbook notes."
        eval_prompt = build_short_answer_eval_prompt(
            question_text=q_data["question_text"],
            correct_model_answer=correct_ans,
            student_answer=student_ans,
            context=context,
        )

        try:
            eval_output = generate_answer(eval_prompt, max_tokens=150, temperature=0.1)
            parsed_eval = extract_json_from_llm(eval_output)
            if parsed_eval:
                is_correct = bool(parsed_eval.get("is_correct", False))
                score = float(parsed_eval.get("score", 0.7 if is_correct else 0.0))
                feedback = parsed_eval.get("feedback", "Good effort!")
                suggested_revision_topic = parsed_eval.get("suggested_revision_topic", "Topic revision")
            else:
                is_correct = len(student_ans) > 10
                score = 0.7 if is_correct else 0.3
                feedback = f"Evaluated based on reference: {explanation}"
                suggested_revision_topic = "Topic concepts"
        except Exception as e:
            logger.error(f"Error in LLM short-answer evaluation: {e}")
            is_correct = True
            score = 0.75
            feedback = f"Answer accepted. Key reference: {explanation}"
            suggested_revision_topic = "Review key points"

    # Log attempt to SQLite
    insert_attempt(
        student_id=request.student_id,
        question_id=request.question_id,
        student_answer=student_ans,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        time_taken_seconds=request.time_taken_seconds or 0.0,
    )

    return SubmitAnswerResponse(
        question_id=request.question_id,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        suggested_revision_topic=suggested_revision_topic,
    )


@router.get("/quizzes/{quiz_id}")
def get_quiz_details(quiz_id: int):
    """Retrieves an existing quiz with all its questions."""
    quiz = get_quiz_with_questions(quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} not found."
        )
    return quiz
