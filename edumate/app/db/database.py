import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from app.config import DB_PATH, logger


@contextmanager
def get_db_connection():
    """Provides a thread-safe connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Initializes SQLite tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                class_or_grade TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 2. Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                subject TEXT,
                chapter TEXT,
                page_count INTEGER,
                chunk_count INTEGER,
                created_at TEXT NOT NULL
            );
        """)

        # 3. Quizzes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                document_ids TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 4. Quiz questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                options_json TEXT,
                correct_answer TEXT,
                explanation TEXT,
                source_metadata_json TEXT,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
            );
        """)

        # 5. Attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                student_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                score REAL NOT NULL,
                feedback TEXT,
                time_taken_seconds REAL,
                attempted_at TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id)
            );
        """)

        # Insert a default student if none exists
        cursor.execute("SELECT COUNT(*) FROM students WHERE student_id = 'student_1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO students (student_id, name, class_or_grade, created_at) VALUES (?, ?, ?, ?)",
                ("student_1", "Alex Hunter", "Class 12", datetime.utcnow().isoformat())
            )

        logger.info(f"Database initialized at {DB_PATH}")


def ensure_student_exists(student_id: str, name: str = "Student", grade: str = "Class 12"):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO students (student_id, name, class_or_grade, created_at) VALUES (?, ?, ?, ?)",
                (student_id, name, grade, datetime.utcnow().isoformat())
            )


def insert_document(student_id: str, file_name: str, subject: str, chapter: str, page_count: int, chunk_count: int) -> int:
    ensure_student_exists(student_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (student_id, file_name, subject, chapter, page_count, chunk_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, file_name, subject, chapter, page_count, chunk_count, datetime.utcnow().isoformat())
        )
        return cursor.lastrowid


def list_documents(student_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if student_id:
            cursor.execute("SELECT * FROM documents WHERE student_id = ? ORDER BY document_id DESC", (student_id,))
        else:
            cursor.execute("SELECT * FROM documents ORDER BY document_id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_document(document_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def insert_quiz(student_id: str, document_ids: List[int], topic: str, difficulty: str) -> int:
    ensure_student_exists(student_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quizzes (student_id, document_ids, topic, difficulty, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, json.dumps(document_ids), topic, difficulty, datetime.utcnow().isoformat())
        )
        return cursor.lastrowid


def insert_quiz_question(
    quiz_id: int,
    question_text: str,
    question_type: str,
    options: Optional[List[str]],
    correct_answer: str,
    explanation: Optional[str] = "",
    source_metadata: Optional[Dict[str, Any]] = None
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_questions (quiz_id, question_text, question_type, options_json, correct_answer, explanation, source_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quiz_id,
                question_text,
                question_type,
                json.dumps(options) if options else None,
                correct_answer,
                explanation or "",
                json.dumps(source_metadata) if source_metadata else None
            )
        )
        return cursor.lastrowid


def get_quiz_with_questions(quiz_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        quiz_row = cursor.fetchone()
        if not quiz_row:
            return None

        quiz = dict(quiz_row)
        cursor.execute("SELECT * FROM quiz_questions WHERE quiz_id = ?", (quiz_id,))
        questions = []
        for q_row in cursor.fetchall():
            q_dict = dict(q_row)
            if q_dict["options_json"]:
                q_dict["options"] = json.loads(q_dict["options_json"])
            else:
                q_dict["options"] = None
            questions.append(q_dict)

        quiz["questions"] = questions
        return quiz


def get_question(question_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quiz_questions WHERE question_id = ?", (question_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("options_json"):
            res["options"] = json.loads(res["options_json"])
        if res.get("source_metadata_json"):
            res["source_metadata"] = json.loads(res["source_metadata_json"])
        return res


def insert_attempt(
    student_id: str,
    question_id: int,
    student_answer: str,
    is_correct: bool,
    score: float,
    feedback: str,
    time_taken_seconds: float = 0.0
) -> int:
    ensure_student_exists(student_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO attempts (student_id, question_id, student_answer, is_correct, score, feedback, time_taken_seconds, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                question_id,
                student_answer,
                1 if is_correct else 0,
                score,
                feedback,
                time_taken_seconds,
                datetime.utcnow().isoformat()
            )
        )
        return cursor.lastrowid


def get_student_progress_data(student_id: str) -> Dict[str, Any]:
    """Calculates student mastery percentage by topic and overall stats."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Query all attempts joined with questions and quizzes to get topics
        cursor.execute("""
            SELECT 
                q.topic,
                COUNT(a.attempt_id) as total_attempts,
                SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) as correct_attempts
            FROM attempts a
            JOIN quiz_questions qq ON a.question_id = qq.question_id
            JOIN quizzes q ON qq.quiz_id = q.quiz_id
            WHERE a.student_id = ?
            GROUP BY q.topic
        """, (student_id,))

        rows = cursor.fetchall()

        topics = []
        recommended_revision = []
        total_attempts_all = 0
        total_correct_all = 0

        for row in rows:
            topic = row["topic"] or "General"
            total = row["total_attempts"]
            correct = row["correct_attempts"] or 0
            mastery = round((correct / total) * 100, 1) if total > 0 else 0.0

            total_attempts_all += total
            total_correct_all += correct

            if mastery >= 80:
                status = "Strong"
            elif mastery >= 50:
                status = "Needs revision"
                recommended_revision.append(topic)
            else:
                status = "Weak topic"
                recommended_revision.append(topic)

            topics.append({
                "topic": topic,
                "total_attempts": total,
                "correct_attempts": correct,
                "mastery_percentage": mastery,
                "status": status
            })

        overall_mastery = round((total_correct_all / total_attempts_all) * 100, 1) if total_attempts_all > 0 else 0.0

        cursor.execute("SELECT COUNT(*) FROM quizzes WHERE student_id = ?", (student_id,))
        total_quizzes = cursor.fetchone()[0]

        return {
            "student_id": student_id,
            "overall_mastery": overall_mastery,
            "total_quizzes_taken": total_quizzes,
            "total_questions_attempted": total_attempts_all,
            "topics": topics,
            "recommended_revision_topics": recommended_revision
        }

