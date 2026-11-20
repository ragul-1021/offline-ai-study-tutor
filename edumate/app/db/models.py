from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    student_id: str = Field(..., description="Unique student identifier")
    name: str = Field("Student", description="Student's full name")
    class_or_grade: str = Field("General", description="Class or Grade level (e.g., Class 10, Class 12)")


class DocumentResponse(BaseModel):
    document_id: int
    document_name: str
    number_of_pages: int
    number_of_chunks: int
    subject: Optional[str] = "General"
    chapter: Optional[str] = "General"


class SourceChunk(BaseModel):
    source_number: int
    document_name: str
    page_number: int
    chunk_text: str


class ChatRequest(BaseModel):
    question: str = Field(..., description="Student's study question")
    student_level: str = Field("Class 12", description="Academic level of the student")
    document_ids: Optional[List[int]] = Field(default=None, description="Optional list of document IDs to query")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of source chunks to retrieve")
    direct_mode: bool = Field(default=False, description="Direct text-to-text mode without document retrieval")
    target_marks: Optional[int] = Field(default=None, description="Optional exam marks target (e.g., 2, 5, 10, 12, 16). If None, general balanced answer is generated.")


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


class QuizGenerateRequest(BaseModel):
    document_ids: List[int] = Field(..., description="Document IDs to base the quiz upon")
    topic: str = Field("General", description="Topic or chapter for the quiz")
    difficulty: str = Field("medium", description="Difficulty level: easy, medium, hard")
    number_of_questions: int = Field(5, ge=1, le=15, description="Number of questions to generate")
    question_types: List[str] = Field(default_factory=lambda: ["mcq", "short_answer"], description="Allowed question types")
    student_id: str = Field("student_1", description="Student requesting the quiz")


class QuizQuestionItem(BaseModel):
    question_id: int
    question_text: str
    question_type: str  # "mcq" or "short_answer"
    options: Optional[List[str]] = None
    explanation: Optional[str] = None


class QuizResponse(BaseModel):
    quiz_id: int
    topic: str
    difficulty: str
    questions: List[QuizQuestionItem]


class SubmitAnswerRequest(BaseModel):
    question_id: int
    student_answer: str
    student_id: str = Field("student_1", description="Student ID")
    time_taken_seconds: Optional[float] = 0.0


class SubmitAnswerResponse(BaseModel):
    question_id: int
    is_correct: bool
    score: float
    feedback: str
    suggested_revision_topic: str


class TopicProgress(BaseModel):
    topic: str
    total_attempts: int
    correct_attempts: int
    mastery_percentage: float
    status: str  # "Strong", "Needs revision", "Weak topic"


class ProgressResponse(BaseModel):
    student_id: str
    overall_mastery: float
    total_quizzes_taken: int
    total_questions_attempted: int
    topics: List[TopicProgress]
    recommended_revision_topics: List[str]

