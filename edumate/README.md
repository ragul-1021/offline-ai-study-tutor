# 🎓 EduMate — Offline AI Study Tutor

**EduMate** is a fully local, privacy-first, offline RAG-powered study tutor built around the **Gemma GGUF** model (`gemma-4-E4B_q4_0-it.gguf`). It allows students to upload textbook chapters and lecture notes, ask questions, get grounded answers with exact page citations, generate interactive practice quizzes, and track topic-wise mastery over time.

Everything runs **100% locally on your machine** inside a single unified project directory without external APIs.

---

## 🌟 Key Features

1. **Strict Offline RAG Pipeline**:
   - PDF text extraction with PyMuPDF (`fitz`).
   - Text chunking (~700 characters with 100-character overlap) preserving sentence boundaries.
   - Vector storage in **ChromaDB** using local `all-MiniLM-L6-v2` embeddings.
   - Top-4 semantic search with metadata filters (document ID, subject, chapter).
2. **Grounded Gemma Tutor**:
   - Zero hallucinations: strictly bounded by retrieved context.
   - Formatted citations showing document name and page number (`[1] textbook.pdf, page 42`).
   - Level-appropriate explanations (Class 10, Class 12, College) with formulas, defined symbols, worked examples, and comprehension check questions.
3. **Practice Quiz Engine**:
   - Generates MCQs and short-answer questions strictly from uploaded notes.
   - Immediate programmatic evaluation for MCQs and conceptual evaluation with Gemma for short answers.
4. **Local Mastery Tracker**:
   - SQLite database tracking all student attempts, time taken, and scores.
   - Topic mastery calculation: `(Correct Answers / Total Attempts) * 100`.
   - Real-time classifications: **Strong (80–100%)**, **Needs revision (50–79%)**, and **Weak (0–49%)**.
   - Interactive Plotly visualization and revision recommendations.

---

## 📁 Consolidated Project Structure

```text
edumate/
  ├── app/
  │   ├── main.py                  # FastAPI application entrypoint & health checks
  │   ├── config.py                # Centralized paths and environment configuration
  │   ├── rag/
  │   │   ├── ingest.py            # PDF text extraction, chunking, and Chroma indexing
  │   │   ├── retriever.py         # Semantic search and top-k chunk retrieval
  │   │   └── prompt_templates.py  # Strict system prompts and prompt builders
  │   ├── llm/
  │   │   └── gemma_client.py      # Thread-safe Gemma GGUF client (llama-cpp-python)
  │   ├── api/
  │   │   ├── routes_documents.py  # PDF upload and document management endpoints
  │   │   ├── routes_chat.py       # RAG chat endpoint (/chat)
  │   │   ├── routes_quiz.py       # Quiz generation and evaluation endpoints
  │   │   └── routes_progress.py   # Student topic mastery analytics endpoint
  │   ├── db/
  │   │   ├── database.py          # SQLite schema, tables, and CRUD operations
  │   │   └── models.py            # Pydantic schemas for requests and responses
  │   └── ui/
  │       └── streamlit_app.py     # Interactive Streamlit frontend UI
  ├── models/                      # 5.15 GB Gemma GGUF model files
  │   └── google_gemma-4-E4B-it-qat-q4_0-gguf/
  │       └── gemma-4-E4B_q4_0-it.gguf
  ├── data/
  │   ├── uploads/                 # Saved uploaded PDF files
  │   ├── chroma_db/               # Persistent ChromaDB vector index
  │   └── edumate.db               # SQLite database
  ├── scripts/                     # Standalone scripts (api.py, run_gemma.py)
  ├── tests/
  │   └── test_rag.py              # Automated RAG pipeline verification test
  ├── venv/                        # Local Python virtual environment
  ├── .env                         # Local environment configuration
  ├── requirements.txt             # Python dependencies
  └── README.md                    # System documentation
```

---

## 🚀 Setup & Execution

Everything is run directly from the `edumate` directory:

```powershell
cd d:\Ragul\hugging_AI_model\edumate
```

### 1. Install Dependencies
```powershell
.\venv\Scripts\pip install -r requirements.txt
```

### 2. Start the FastAPI Backend
```powershell
.\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/health`

### 3. Start the Streamlit UI
In a separate terminal window:
```powershell
cd d:\Ragul\hugging_AI_model\edumate
.\venv\Scripts\streamlit run app/ui/streamlit_app.py
```
- Opens in your browser at: `http://localhost:8501`

### 4. Run the RAG Verification Test
```powershell
.\venv\Scripts\python tests/test_rag.py
```
