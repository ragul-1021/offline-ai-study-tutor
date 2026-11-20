import json
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.db.models import ChatRequest, ChatResponse, SourceChunk
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.prompt_templates import (
    build_rag_prompt,
    build_direct_chat_prompt,
    get_effective_marks,
)
from app.llm.gemma_client import generate_answer, generate_answer_stream
from app.config import logger

router = APIRouter(tags=["Chat"])

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def calculate_token_budget(target_marks: Optional[int], question: str, default_tokens: int = 300) -> int:
    """Scales maximum generation tokens dynamically according to requested exam mark weightage.
    
    Tuned for edge CPU execution: High information density without excessive token latency.
    """
    effective_marks = get_effective_marks(target_marks, question)
    if not effective_marks:
        return default_tokens
    if effective_marks <= 2:
        return 130   # ~50-60 words (concise, ~15s on CPU)
    elif effective_marks <= 5:
        return 280   # ~150-180 words (~35-45s on CPU)
    elif effective_marks <= 12:
        return 550   # ~300-380 words (~65-80s on CPU, all 8 sections covered cleanly)
    else:  # 15, 16+ marks
        return 750   # ~420-550 words (~90-110s on CPU, exhaustive 16-mark essay)


@router.post("/chat", response_model=ChatResponse)
def chat_with_tutor(request: ChatRequest):
    """Answers student questions either via Direct Text-to-Text mode or Grounded RAG mode.
    
    Scales response size and depth automatically based on target exam marks.
    If the requested topic is not found in the notes, seamlessly falls back to the LLM.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    token_budget = calculate_token_budget(request.target_marks, question, default_tokens=350)

    # Fast Direct Text-to-Text Mode
    if request.direct_mode:
        prompt = build_direct_chat_prompt(
            question=question,
            student_level=request.student_level or "Class 12",
            target_marks=request.target_marks,
        )
        try:
            answer = generate_answer(prompt=prompt, max_tokens=token_budget, temperature=0.3)
            return ChatResponse(answer=answer, sources=[])
        except Exception as e:
            logger.error(f"Error in direct generation: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Inference error while generating tutor response: {str(e)}"
            )

    # Grounded RAG Mode
    effective_marks = get_effective_marks(request.target_marks, question)
    # Use 2-3 focused chunks to keep CPU prompt prefill under 4-5s
    top_k = min(request.top_k, 3)

    chunks = retrieve_relevant_chunks(
        query=question,
        document_ids=request.document_ids,
        top_k=top_k,
    )

    # Filter chunks: cosine distance <= 0.68 represents true semantic relevance.
    # Distances above 0.70 indicate the notes do not have content on this topic.
    RELEVANCE_THRESHOLD = 0.68
    relevant_chunks = [c for c in chunks if c.get("distance", 1.0) <= RELEVANCE_THRESHOLD]

    # Seamless Fallback to LLM if notes do not have the required topic or are irrelevant
    if not relevant_chunks:
        logger.info(f"No relevant chunks found for '{question[:40]}' (best distance: {chunks[0]['distance'] if chunks else 'None'}). Falling back to direct LLM generation.")
        prompt = build_direct_chat_prompt(
            question=question,
            student_level=request.student_level or "Class 12",
            target_marks=request.target_marks,
        )
        try:
            answer = generate_answer(prompt=prompt, max_tokens=token_budget, temperature=0.3)
            fallback_answer = f"> 💡 *Note: Topic not found in selected notes. Generated using EduMate AI tutor knowledge.*\n\n{answer}"
            return ChatResponse(answer=fallback_answer, sources=[])
        except Exception as e:
            logger.error(f"Error in fallback generation: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Inference error while generating fallback response: {str(e)}"
            )

    # Use only relevant chunks (discarding high-distance noise)
    chunks = relevant_chunks

    sources = [
        SourceChunk(
            source_number=idx + 1,
            document_name=chunk.get("document_name", "Unknown"),
            page_number=chunk.get("page_number", 1),
            chunk_text=chunk.get("text", "")
        )
        for idx, chunk in enumerate(chunks)
    ]

    prompt = build_rag_prompt(
        question=question,
        retrieved_chunks=chunks,
        student_level=request.student_level or "Class 12",
        target_marks=request.target_marks,
    )

    rag_token_budget = calculate_token_budget(request.target_marks, question, default_tokens=384)

    try:
        answer = generate_answer(prompt=prompt, max_tokens=rag_token_budget, temperature=0.2)
    except Exception as e:
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error while generating tutor response: {str(e)}"
        )

    return ChatResponse(answer=answer, sources=sources)


@router.post("/chat/stream")
def chat_with_tutor_stream(request: ChatRequest):
    """Streams student answers token-by-token in real time.
    
    Supports both Direct Text-to-Text mode and Grounded RAG mode with dynamic exam mark scaling.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    token_budget = calculate_token_budget(request.target_marks, question, default_tokens=350)
    logger.info(f"[STREAM] target_marks={request.target_marks}, token_budget={token_budget}, direct_mode={request.direct_mode}, question='{question[:60]}...'")

    # Fast Direct Text-to-Text Mode (No RAG retrieval)
    if request.direct_mode:
        prompt = build_direct_chat_prompt(
            question=question,
            student_level=request.student_level or "Class 12",
            target_marks=request.target_marks,
        )
        logger.info(f"[STREAM-DIRECT] Prompt length={len(prompt)} chars, first 200: {prompt[:200]}")
        response_headers = dict(STREAM_HEADERS)
        response_headers["X-Sources-JSON"] = "[]"

        def direct_stream():
            try:
                for token in generate_answer_stream(prompt=prompt, max_tokens=token_budget, temperature=0.3):
                    yield token
            except Exception as e:
                logger.error(f"Error in direct_stream: {e}", exc_info=True)
                yield f"\n\n**Generation Error**: {str(e)}"

        return StreamingResponse(
            direct_stream(),
            media_type="text/plain; charset=utf-8",
            headers=response_headers,
        )

    # Grounded RAG Mode
    effective_marks = get_effective_marks(request.target_marks, question)
    # Use 2-3 focused chunks to keep CPU prompt prefill under 4-5s
    top_k = min(request.top_k, 3)

    chunks = retrieve_relevant_chunks(
        query=question,
        document_ids=request.document_ids,
        top_k=top_k,
    )

    # Filter chunks: cosine distance <= 0.68 represents true semantic relevance.
    # Distances above 0.70 indicate the notes do not have content on this topic.
    RELEVANCE_THRESHOLD = 0.68
    relevant_chunks = [c for c in chunks if c.get("distance", 1.0) <= RELEVANCE_THRESHOLD]

    # Seamless Fallback to LLM if notes do not have the required topic or are irrelevant
    if not relevant_chunks:
        logger.info(f"[STREAM] No relevant chunks found for '{question[:40]}' (best dist: {chunks[0]['distance'] if chunks else 'None'}). Falling back to direct LLM generation.")
        prompt = build_direct_chat_prompt(
            question=question,
            student_level=request.student_level or "Class 12",
            target_marks=request.target_marks,
        )
        response_headers = dict(STREAM_HEADERS)
        response_headers["X-Sources-JSON"] = "[]"
        response_headers["X-Fallback-Mode"] = "true"

        def fallback_stream():
            yield "> 💡 *Note: Topic not found in selected notes. Generated using EduMate AI tutor knowledge.*\n\n"
            try:
                for token in generate_answer_stream(prompt=prompt, max_tokens=token_budget, temperature=0.3):
                    yield token
            except Exception as e:
                logger.error(f"Error in fallback_stream: {e}", exc_info=True)
                yield f"\n\n**Generation Error**: {str(e)}"

        return StreamingResponse(
            fallback_stream(),
            media_type="text/plain; charset=utf-8",
            headers=response_headers,
        )

    # Use only relevant chunks (discarding high-distance noise)
    chunks = relevant_chunks

    sources_data = [
        {
            "source_number": idx + 1,
            "document_name": chunk.get("document_name", "Unknown"),
            "page_number": chunk.get("page_number", 1),
            "chunk_text": chunk.get("text", "")
        }
        for idx, chunk in enumerate(chunks)
    ]

    prompt = build_rag_prompt(
        question=question,
        retrieved_chunks=chunks,
        student_level=request.student_level or "Class 12",
        target_marks=request.target_marks,
    )

    rag_token_budget = calculate_token_budget(request.target_marks, question, default_tokens=384)

    response_headers = dict(STREAM_HEADERS)
    response_headers["X-Sources-JSON"] = json.dumps(sources_data)

    def token_stream():
        try:
            for token in generate_answer_stream(prompt=prompt, max_tokens=rag_token_budget, temperature=0.2):
                yield token
        except Exception as e:
            logger.error(f"Error in token_stream: {e}", exc_info=True)
            yield f"\n\n**Generation Error**: {str(e)}"

    return StreamingResponse(
        token_stream(),
        media_type="text/plain; charset=utf-8",
        headers=response_headers,
    )
