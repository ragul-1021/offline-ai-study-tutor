from fastapi import APIRouter, HTTPException, status
from app.db.models import ProgressResponse, TopicProgress
from app.db.database import get_student_progress_data

router = APIRouter(tags=["Progress"])


@router.get("/progress/{student_id}", response_model=ProgressResponse)
def get_progress(student_id: str):
    """Returns topic-wise mastery analytics and revision recommendations for a student."""
    if not student_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID cannot be empty."
        )

    progress_data = get_student_progress_data(student_id=student_id)

    topics = [
        TopicProgress(
            topic=t["topic"],
            total_attempts=t["total_attempts"],
            correct_attempts=t["correct_attempts"],
            mastery_percentage=t["mastery_percentage"],
            status=t["status"],
        )
        for t in progress_data["topics"]
    ]

    return ProgressResponse(
        student_id=progress_data["student_id"],
        overall_mastery=progress_data["overall_mastery"],
        total_quizzes_taken=progress_data["total_quizzes_taken"],
        total_questions_attempted=progress_data["total_questions_attempted"],
        topics=topics,
        recommended_revision_topics=progress_data["recommended_revision_topics"],
    )

