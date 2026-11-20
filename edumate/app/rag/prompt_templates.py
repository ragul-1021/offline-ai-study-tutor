import re
from typing import List, Dict, Any, Optional

RAG_SYSTEM_PROMPT_TEMPLATE = """You are EduMate, an expert offline AI study tutor.

Answer the student's question clearly, thoroughly, and helpfully.

RULES:
1. Prioritize and cite facts from the RETRIEVED STUDY MATERIAL using [1], [2], etc., whenever available.
2. CRITICAL FALLBACK INSTRUCTION: If the retrieved material does NOT contain the topic, or is only partially relevant, DO NOT refuse to answer and DO NOT say you lack information. Instead, seamlessly generate the full, accurate academic explanation using your internal AI tutor knowledge so the student receives a complete, helpful answer.
3. Explain clearly for a {student_level} student using crisp bullet points, logical steps, and practical examples.
4. If formulas or derivations apply, present them clearly with all symbols and SI units.

OUTPUT FORMAT:
### Answer
[Clear, comprehensive explanation integrating retrieved material and academic knowledge, with citations like [1], [2] where applicable]

### Key Points
- [Key point 1]
- [Key point 2]

### Sources
[1] {document_name}, Page {page_number} (or "Built-in AI Tutor Knowledge" if beyond notes)"""


def extract_marks_from_question(question: str) -> Optional[int]:
    """Detects if the user explicitly requested marks in their question text (e.g. '12 marks', '5-mark', 'for 2 marks')."""
    match = re.search(r'\b(2|3|4|5|6|7|8|10|12|14|15|16|20)\s*(?:-|\s)?(?:marks?|mk|mks)\b', question, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            pass
    return None


def get_effective_marks(target_marks: Optional[int], question: str) -> Optional[int]:
    """Returns explicit target_marks if provided, otherwise checks if question contains marks text."""
    if target_marks and target_marks > 0:
        return target_marks
    return extract_marks_from_question(question)


def get_mark_guidelines(marks: Optional[int]) -> str:
    """Returns specific exam formatting instructions based on mark weightage."""
    if not marks:
        return ""
    if marks <= 2:
        return (
            f"\n\nEXAM SPECIFICATION ({marks} MARKS - VERY SHORT ANSWER):\n"
            f"- Target Length: Approx 40-60 words.\n"
            f"- Structure: 1-sentence precise definition, followed by 2 concise bullet points or formula with units.\n"
            f"- Be direct and concise without introductory preamble."
        )
    elif marks <= 5:
        return (
            f"\n\nEXAM SPECIFICATION ({marks} MARKS - SHORT ANSWER):\n"
            f"- Target Length: Approx 150-200 words.\n"
            f"- Structure:\n"
            f"  1. Definition & Core Concept\n"
            f"  2. Working Principle or Key Mechanism\n"
            f"  3. 3-4 Key Characteristics, Steps, or Points\n"
            f"  4. Mathematical Formula / Brief Real-world Example"
        )
    elif marks <= 12:
        return (
            f"\n\nEXAM SPECIFICATION ({marks} MARKS - STRUCTURED EXAM ANSWER):\n"
            f"- Target Length: Approx 280-350 words of high-density, bullet-pointed content.\n"
            f"- Structure with clear headings:\n"
            f"  ### 1. Introduction & Formal Definition\n"
            f"  ### 2. Core Scientific/Technical Principle\n"
            f"  ### 3. Detailed Mechanism & Working (Bullet points)\n"
            f"  ### 4. Mathematical Formula / Circuit / Diagram Description & Parameters\n"
            f"  ### 5. Types / Classification / Key Characteristics\n"
            f"  ### 6. Real-World Applications & Practical Examples\n"
            f"  ### 7. Advantages & Limitations\n"
            f"  ### 8. Summary / Key Takeaways\n"
            f"- Use crisp bullet points and formulas to maximize clarity and avoid verbose narrative filler."
        )
    else:  # 15, 16+ marks
        return (
            f"\n\nEXAM SPECIFICATION ({marks} MARKS - COMPREHENSIVE ESSAY):\n"
            f"- Target Length: Approx 350-420 words of high-density structured academic content.\n"
            f"- Thoroughly cover theory, formulas, step-by-step mechanism, and applications using bullet points under clear headers."
        )


def build_rag_prompt(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    student_level: str = "Class 12",
    target_marks: Optional[int] = None,
) -> str:
    """Builds the strict RAG prompt adapting structure according to target exam marks."""
    effective_marks = get_effective_marks(target_marks, question)
    mark_guidelines = get_mark_guidelines(effective_marks)

    base_instructions = (
        f"You are EduMate, an expert academic AI study tutor.\n\n"
        f"Answer the student's question clearly, thoroughly, and helpfully for a {student_level} student.\n\n"
        f"RULES:\n"
        f"1. Prioritize and cite facts from the RETRIEVED STUDY MATERIAL using [1], [2], etc., whenever available.\n"
        f"2. CRITICAL FALLBACK INSTRUCTION: If the retrieved material has limited or partial details on this topic, "
        f"DO NOT refuse to answer, DO NOT say you lack information, and DO NOT output incomplete sentences. "
        f"Instead, seamlessly integrate whatever details the notes provide and complete the full, rigorous academic explanation "
        f"using your internal AI tutor knowledge so the student receives an exhaustive, complete answer.\n"
        f"3. Explain clearly using crisp bullet points, logical steps, formulas with SI units, and practical examples.\n"
    )

    if effective_marks and effective_marks >= 10:
        format_instructions = (
            f"\nCRITICAL EXAM REQUIREMENT ({effective_marks} MARKS):\n"
            f"You MUST write an EXHAUSTIVE, DETAILED answer of 450-650 words.\n"
            f"DO NOT write a short answer. DO NOT summarize briefly.\n"
            f"Use ALL these ### headings:\n"
            f"### 1. Introduction & Formal Definition\n"
            f"### 2. Core Scientific/Technical Principle\n"
            f"### 3. Detailed Mechanism & Working\n"
            f"### 4. Mathematical Formula & Parameters\n"
            f"### 5. Types / Classification / Key Characteristics\n"
            f"### 6. Real-World Applications & Practical Examples\n"
            f"### 7. Advantages & Limitations\n"
            f"### 8. Summary / Key Takeaways\n"
            f"{mark_guidelines}"
        )
    elif effective_marks:
        format_instructions = (
            f"\nMARK-BASED EXAM REQUIREMENT ({effective_marks} MARKS):\n"
            f"{mark_guidelines}\n"
            f"Organize the verified facts from the retrieved material and your academic knowledge into the required depth for {effective_marks} marks."
        )
    else:
        format_instructions = (
            "\nOUTPUT FORMAT:\n"
            "### Answer\n"
            "Clear, comprehensive explanation integrating retrieved material and academic knowledge, with citations like [1], [2] where applicable.\n\n"
            "### Key Points\n"
            "- Key point 1\n"
            "- Key point 2"
        )

    chunks_text_list = []
    for idx, chunk in enumerate(retrieved_chunks, 1):
        doc_name = chunk.get("document_name", "Unknown Document")
        page_num = chunk.get("page_number", 1)
        text = chunk.get("text", "").strip()
        if len(text) > 350:
            text = text[:350] + "..."
        chunks_text_list.append(f"[{idx}] Source: {doc_name}, Page: {page_num}\n{text}")

    sources_formatted = "\n\n".join(chunks_text_list)

    full_prompt = (
        f"{base_instructions}"
        f"{format_instructions}\n\n"
        f"RETRIEVED STUDY MATERIAL:\n"
        f"{sources_formatted}\n\n"
        f"STUDENT QUESTION:\n"
        f"{question}"
    )
    return full_prompt


def build_direct_chat_prompt(
    question: str,
    student_level: str = "Class 12",
    target_marks: Optional[int] = None,
) -> str:
    """Builds a fast, direct text-to-text prompt scaling depth according to exam marks."""
    effective_marks = get_effective_marks(target_marks, question)

    if not effective_marks:
        # Default general mode — no marks requested
        return f"""You are EduMate, an expert, patient AI study tutor.
Explain this concept clearly and step-by-step for a {student_level} student.
Use simple language, bold key terms, and give one concrete real-life example.
Keep your explanation focused, helpful, and balanced (around 200-250 words).

STUDENT QUESTION:
{question}

TUTOR EXPLANATION:"""

    if effective_marks <= 2:
        return f"""You are EduMate, an AI tutor writing a {effective_marks}-MARK exam answer for a {student_level} student.

IMPORTANT: This is a {effective_marks}-mark answer. Keep it VERY SHORT — around 40-60 words only.
Structure: One precise definition sentence, then 2 concise bullet points or a formula with units.
Do NOT write long explanations. Be direct.

QUESTION ({effective_marks} marks):
{question}

ANSWER ({effective_marks} marks, ~50 words):"""

    elif effective_marks <= 5:
        return f"""You are EduMate, an AI tutor writing a {effective_marks}-MARK exam answer for a {student_level} student.

IMPORTANT: This is a {effective_marks}-mark answer. Write approximately 150-200 words.
Structure your answer with:
1. Definition & Core Concept
2. Working Principle or Key Mechanism
3. 3-4 Key Points or Characteristics
4. Formula (if applicable) and one real-world example

QUESTION ({effective_marks} marks):
{question}

ANSWER ({effective_marks} marks, ~180 words):"""

    elif effective_marks <= 12:
        return f"""You are EduMate, an expert AI tutor writing a {effective_marks}-MARK structured exam answer for a {student_level} student.

CRITICAL INSTRUCTION: Write a high-density, well-structured {effective_marks}-mark exam answer.
Use bullet points and clear, direct explanations under each heading to maximize clarity and avoid unnecessary filler (approx 280-350 words total).

Cover ALL of these 8 sections using ### headings:

### 1. Introduction & Formal Definition
(Clear, formal definition)

### 2. Core Scientific/Technical Principle
(Core physics/scientific principle)

### 3. Detailed Mechanism & Working
(Step-by-step bullet points of how it works)

### 4. Mathematical Formula & Parameters
(Formulas, symbols, SI units)

### 5. Types / Classification / Key Characteristics
(Key types or characteristics in bullet points)

### 6. Real-World Applications & Practical Examples
(3-4 practical use cases)

### 7. Advantages & Limitations
(Pros and cons)

### 8. Summary & Key Takeaways
(Key revision points)

QUESTION ({effective_marks} marks):
{question}

STRUCTURED {effective_marks}-MARK ANSWER (cover all 8 sections crisply with bullet points):"""

    else:  # 15, 16+ marks
        return f"""You are EduMate, an expert AI tutor writing an in-depth {effective_marks}-MARK structured academic answer for a {student_level} student.

CRITICAL INSTRUCTION: Provide a comprehensive, high-density structured answer using bullet points, derivations, and concise explanations under each heading (approx 350-420 words total).

Structure with these headings:
### 1. Introduction & Formal Definition
### 2. Theoretical Background & Principle
### 3. Detailed Mechanism & Step-by-Step Working
### 4. Mathematical Derivation & Formulas
### 5. Types / Classification
### 6. Practical Applications & Examples
### 7. Advantages, Limitations & Comparisons
### 8. Summary & Key Takeaways

QUESTION ({effective_marks} marks):
{question}

STRUCTURED {effective_marks}-MARK ANSWER (cover all sections with high information density):"""


def build_quiz_generation_prompt(
    topic: str,
    difficulty: str,
    number_of_questions: int,
    question_types: List[str],
    retrieved_chunks: List[Dict[str, Any]]
) -> str:
    """Builds a streamlined prompt requesting a practice quiz formatted strictly as JSON."""
    # Keep chunks compact to speed up prompt prefill
    trimmed_chunks = []
    for i, c in enumerate(retrieved_chunks[:3]):
        text_snippet = c.get('text', '').strip()[:450]
        trimmed_chunks.append(f"[{i+1}] {text_snippet}")
    chunks_text = "\n\n".join(trimmed_chunks)

    return f"""You are an exam generator. Create a {number_of_questions}-question quiz on "{topic}" ({difficulty} level) based on this text:
{chunks_text}

Rules:
1. Allowed types: {", ".join(question_types)}.
2. For "mcq", give 4 options in an array, and "correct_answer" as "A", "B", "C", or "D".
3. For "short_answer", set options to null, and give a model answer in "correct_answer".
4. Output valid JSON only, starting with {{ and ending with }}:

{{
  "questions": [
    {{
      "question_text": "Sample question text?",
      "question_type": "mcq",
      "options": ["A) Opt 1", "B) Opt 2", "C) Opt 3", "D) Opt 4"],
      "correct_answer": "A",
      "explanation": "Brief reason"
    }}
  ]
}}"""


def build_short_answer_eval_prompt(
    question_text: str,
    correct_model_answer: str,
    student_answer: str,
    context: str
) -> str:
    """Evaluates a student's short answer against the context and expected answer."""
    return f"""Evaluate this student answer against reference context.

CONTEXT:
{context[:300]}

QUESTION:
{question_text}

REFERENCE:
{correct_model_answer}

STUDENT ANSWER:
{student_answer}

Return valid JSON only:
{{
  "is_correct": true,
  "score": 0.85,
  "feedback": "Constructive feedback under 25 words.",
  "suggested_revision_topic": "Specific topic name"
}}"""
