import os
import json
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="EduMate - Offline AI Study Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API endpoint URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# App title and styling
st.title("🎓 EduMate - Offline AI Study Tutor")
st.markdown("Your local, privacy-preserving study partner grounded strictly in your uploaded textbooks and notes.")

# Custom CSS for long academic essay readability
st.markdown("""
<style>
    /* Academic Answer Sheet styling */
    .stMarkdown h3 {
        color: #1e88e5;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 6px;
        margin-top: 18px;
        font-weight: 700;
    }
    .stMarkdown h2 {
        color: #0d47a1;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .stMarkdown ul {
        line-height: 1.7;
    }
    .stMarkdown blockquote {
        border-left: 4px solid #1e88e5;
        background-color: rgba(30, 136, 229, 0.05);
        padding: 8px 16px;
        border-radius: 4px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR: Student Profile & Document Ingestion
# -------------------------------------------------------------
with st.sidebar:
    st.header("👤 Student Profile")
    student_id = st.text_input("Student ID", value="student_1")
    student_grade = st.selectbox(
        "Academic Level",
        ["Class 10", "Class 11", "Class 12", "Undergraduate", "General"],
        index=2
    )

    st.markdown("---")
    st.header("📂 Upload Study Material")
    uploaded_file = st.file_uploader("Upload PDF Notes or Chapters", type=["pdf"])
    subject = st.text_input("Subject", value="Physics")
    chapter = st.text_input("Chapter / Unit", value="Current Electricity")

    if st.button("🚀 Upload & Index PDF", use_container_width=True):
        if uploaded_file is None:
            st.error("Please select a PDF file first.")
        else:
            with st.spinner("Extracting text, chunking, and embedding locally..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    data = {
                        "student_id": student_id,
                        "subject": subject,
                        "chapter": chapter,
                    }
                    res = requests.post(f"{API_URL}/upload-document", files=files, data=data)
                    if res.status_code == 201:
                        doc_info = res.json()
                        st.success(f"Indexed '{doc_info['document_name']}' successfully! ({doc_info['number_of_pages']} pages, {doc_info['number_of_chunks']} chunks)")
                    else:
                        st.error(f"Upload failed: {res.json().get('detail', res.text)}")
                except Exception as e:
                    st.error(f"Could not connect to EduMate API at {API_URL}. Is the backend running? ({e})")

    st.markdown("---")
    st.header("📚 Indexed Documents")
    try:
        docs_res = requests.get(f"{API_URL}/documents?student_id={student_id}")
        if docs_res.status_code == 200:
            doc_list = docs_res.json()
            if doc_list:
                for doc in doc_list:
                    st.write(f"• **ID {doc['document_id']}**: `{doc['document_name']}` ({doc.get('subject')} - {doc.get('chapter')})")
            else:
                st.caption("No documents uploaded yet.")
        else:
            st.caption("Unable to load documents.")
    except Exception:
        st.caption("Backend offline. Please start FastAPI.")


# -------------------------------------------------------------
# MAIN VIEW TABS
# -------------------------------------------------------------
tab_chat, tab_quiz, tab_progress = st.tabs(["📖 Study & Ask Tutor", "📝 Practice Quiz", "📊 Topic Mastery"])

# =============================================================
# TAB 1: STUDY & ASK TUTOR (Optimized for 16-Mark Academic Essays)
# =============================================================
with tab_chat:
    st.subheader("📖 Academic Study & Exam Tutor")
    st.caption("Ask any question or concept. EduMate scales the answer from a quick 2-mark definition to a full 16-mark university-level academic breakdown.")

    # Initialize session state for persistent answers
    if "current_answer_data" not in st.session_state:
        st.session_state["current_answer_data"] = None

    # Tutor Mode Toggle
    tutor_mode = st.radio(
        "Tutor Mode:",
        [
            "⚡ Fast Direct AI Tutor (Text-to-Text — Instant direct reasoning)",
            "📚 Grounded Study Notes (RAG — Grounded in uploaded PDFs with page citations)"
        ],
        index=0,
        horizontal=True
    )
    is_direct_mode = "Fast Direct" in tutor_mode

    # Retrieve available document IDs for filtering
    doc_options = {}
    try:
        d_res = requests.get(f"{API_URL}/documents")
        if d_res.status_code == 200:
            for d in d_res.json():
                doc_options[f"[{d['document_id']}] {d['document_name']} ({d.get('chapter')})"] = d['document_id']
    except Exception:
        pass

    if is_direct_mode:
        st.caption("💡 **Fast Direct Mode**: Answers any concept or exam question using Gemma's built-in reasoning.")
        doc_ids_to_send = None
        top_k = 1
    else:
        st.caption("📚 **Grounded RAG Mode**: Matches against your uploaded notes. If the topic is missing from your notes, EduMate automatically generates the full explanation using built-in AI tutor knowledge.")
        col_filter1, col_filter2 = st.columns([3, 1])
        with col_filter1:
            selected_doc_labels = st.multiselect(
                "Filter by Documents (Leave empty to search all uploaded materials)",
                options=list(doc_options.keys())
            )
        with col_filter2:
            top_k = st.slider("Sources to retrieve", min_value=1, max_value=6, value=3)

        doc_ids_to_send = [doc_options[lbl] for lbl in selected_doc_labels] if selected_doc_labels else None

    # Exam Mark Weightage Selector
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        marks_options = [
            "Auto / General (Balanced explanation — default)",
            "2 Marks (Very Short — Definition & 2 points, ~50 words)",
            "5 Marks (Short Answer — Principle, points & example, ~180 words)",
            "10 Marks (Detailed Long Answer — Multi-section breakdown, ~350 words)",
            "12 Marks (University Essay — Exhaustive step-by-step & mechanism, ~450 words)",
            "16 Marks (Complete Academic Breakdown — 8 sections, derivations & applications, ~550 words)",
        ]
        marks_selection = st.selectbox(
            "🎯 Exam Mark Weightage (Length & Depth):",
            marks_options,
            index=0,
            help="Select mark weightage or write 'for 16 marks' in your question. EduMate automatically formats the response to Indian university exam marking schemes."
        )
    with col_m2:
        if is_direct_mode:
            st.metric("Mode", "⚡ Fast Direct AI")
        else:
            st.metric("Mode", "📚 Grounded RAG")

    target_marks = None
    if "2 Marks" in marks_selection:
        target_marks = 2
    elif "5 Marks" in marks_selection:
        target_marks = 5
    elif "10 Marks" in marks_selection:
        target_marks = 10
    elif "12 Marks" in marks_selection:
        target_marks = 12
    elif "16 Marks" in marks_selection:
        target_marks = 16

    # Quick Suggestion Chips for Students
    st.markdown("**Quick Prompts:**")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    preset_q = None
    if q_col1.button("⚡ Newton's Laws (16 Marks)", use_container_width=True):
        preset_q = "Explain Newton's Laws of Motion in detail with derivations and practical applications for 16 marks"
    if q_col2.button("⚡ AC Generator (12 Marks)", use_container_width=True):
        preset_q = "Explain the working principle and construction of an AC Generator for 12 marks"
    if q_col3.button("⚡ Ohm's Law (5 Marks)", use_container_width=True):
        preset_q = "State and derive Ohm's law with microscopic form and limitations for 5 marks"
    if q_col4.button("⚡ Drift Velocity (2 Marks)", use_container_width=True):
        preset_q = "Define drift velocity and state its formula and SI units for 2 marks"

    default_question_text = preset_q if preset_q else ""

    user_question = st.text_area(
        "Your Question:",
        value=default_question_text,
        placeholder="e.g. Explain the principle, working and mathematical derivation of an AC Generator (or specify 'for 16 marks')",
        height=90
    )

    ask_col1, ask_col2 = st.columns([1, 5])
    with ask_col1:
        ask_submitted = st.button("💡 Ask EduMate", type="primary", use_container_width=True)
    with ask_col2:
        if st.session_state.get("current_answer_data"):
            if st.button("🔄 Clear Current Answer", use_container_width=False):
                st.session_state["current_answer_data"] = None
                st.rerun()

    # Generation Execution
    if ask_submitted:
        if not user_question.strip():
            st.warning("Please enter a question.")
        else:
            payload = {
                "question": user_question,
                "student_level": student_grade,
                "document_ids": doc_ids_to_send,
                "top_k": top_k,
                "direct_mode": is_direct_mode,
                "target_marks": target_marks
            }

            mark_label = f"{target_marks}-Mark" if target_marks else "General"
            
            # Dedicated Live Exam Progress Container
            progress_card = st.container()
            with progress_card:
                st.info(f"⏳ **Writing {mark_label} Academic Answer...** Starting stream (~5 tok/s on CPU)...")
                status_box = st.empty()
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                m_metric1 = metrics_col1.empty()
                m_metric2 = metrics_col2.empty()
                m_metric3 = metrics_col3.empty()

            response_canvas = st.empty()
            full_response = ""
            token_count = 0
            sources_holder = []
            is_fallback = False

            try:
                with requests.post(
                    f"{API_URL}/chat/stream",
                    json=payload,
                    stream=True,
                    timeout=(120, 600)
                ) as res:
                    if res.status_code == 200:
                        raw_sources = res.headers.get("X-Sources-JSON")
                        is_fallback = res.headers.get("X-Fallback-Mode") == "true"
                        if raw_sources:
                            try:
                                sources_holder.extend(json.loads(raw_sources))
                            except Exception:
                                pass

                        for chunk in res.iter_content(chunk_size=1, decode_unicode=True):
                            if chunk:
                                token_count += 1
                                full_response += chunk

                                # Live metrics update every 10 tokens
                                if token_count % 10 == 0 or token_count == 1:
                                    word_count = len(full_response.split())
                                    status_box.markdown(f"✍️ **Streaming tokens in real time...** (`{token_count}` tokens computed)")
                                    m_metric1.metric("Tokens", token_count)
                                    m_metric2.metric("Word Count", word_count)
                                    m_metric3.metric("Exam Target", f"{mark_label}")

                                # Real-time canvas render with blinking cursor
                                response_canvas.markdown(full_response + " ▌")

                        # Generation Complete
                        progress_card.empty()
                        response_canvas.empty()

                        # Store in session state for persistent reading & download
                        st.session_state["current_answer_data"] = {
                            "question": user_question,
                            "target_marks": target_marks,
                            "mark_label": mark_label,
                            "response": full_response,
                            "sources": sources_holder,
                            "is_fallback": is_fallback,
                            "token_count": token_count,
                            "word_count": len(full_response.split()),
                        }
                    else:
                        st.error(f"Backend error: {res.text}")
            except requests.exceptions.Timeout:
                st.error("Request timed out. The model was still computing on CPU. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to EduMate backend at {API_URL}. Is the server running?")

    # Persistent Academic Essay Reading Canvas
    if st.session_state.get("current_answer_data"):
        data = st.session_state["current_answer_data"]

        st.markdown("---")
        st.markdown("## 📜 Academic Answer Sheet")

        # Top Metadata Banner
        banner_c1, banner_c2, banner_c3, banner_c4 = st.columns([2, 1, 1, 1])
        with banner_c1:
            st.markdown(f"**Question:** *{data['question']}*")
        with banner_c2:
            st.metric("Exam Weightage", f"🎯 {data['mark_label']}")
        with banner_c3:
            st.metric("Total Words", f"📝 {data['word_count']}")
        with banner_c4:
            est_mins = max(1, round(data['word_count'] / 180))
            st.metric("Est. Read Time", f"⏱️ ~{est_mins} min")

        # Fallback Alert if topic wasn't in uploaded notes
        if data.get("is_fallback") or not data.get("sources"):
            if not is_direct_mode:
                st.info("💡 **AI Knowledge Synthesis:** This topic was not found in your uploaded PDF notes. EduMate automatically generated the full explanation using built-in AI tutor knowledge.")

        # Download / Action Toolbar
        action_c1, action_c2 = st.columns([1, 4])
        with action_c1:
            st.download_button(
                label="📥 Download Notes (.md)",
                data=f"# {data['question']}\n\n**Exam Weightage:** {data['mark_label']}\n**Word Count:** {data['word_count']}\n\n---\n\n{data['response']}",
                file_name=f"edumate_{data['mark_label'].lower()}_notes.md",
                mime="text/markdown",
                use_container_width=True
            )

        # Full Formatted Academic Reading Canvas
        with st.container(border=True):
            st.markdown(data["response"])

        # Collapsible Source Citations Accordion
        if data.get("sources"):
            with st.expander(f"📑 Verified Source Citations ({len(data['sources'])} chunks retrieved from your notes)", expanded=False):
                for src in data["sources"]:
                    st.markdown(f"**Source [{src['source_number']}] — `{src['document_name']}` (Page {src['page_number']})**")
                    st.caption(src["chunk_text"])
                    st.markdown("---")


# =============================================================
# TAB 2: PRACTICE QUIZ
# =============================================================
with tab_quiz:
    st.subheader("Generate a Grounded Practice Quiz")
    st.caption("Quizzes are created strictly from the facts, formulas, and definitions in your notes.")
    st.info("💡 **Speed Tip:** Keep questions at 2 or 3 for fast ~10–15s generation on CPU. Generating 5+ questions takes longer.")

    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        quiz_topic = st.text_input("Quiz Topic / Chapter", value=chapter or "Physics")
    with col_q2:
        quiz_difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
    with col_q3:
        num_questions = st.number_input("Number of Questions", min_value=1, max_value=6, value=2)

    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        selected_quiz_docs = st.multiselect(
            "Select Source Documents for Quiz",
            options=list(doc_options.keys()),
            default=list(doc_options.keys())[:1] if doc_options else []
        )
    with col_t2:
        question_types = st.multiselect("Question Types", ["mcq", "short_answer"], default=["mcq", "short_answer"])

    if st.button("🎲 Generate Quiz"):
        if not selected_quiz_docs and doc_options:
            st.warning("Please select at least one document.")
        elif not question_types:
            st.warning("Please select at least one question type.")
        else:
            quiz_doc_ids = [doc_options[lbl] for lbl in selected_quiz_docs] if selected_quiz_docs else []
            with st.spinner("Reading notes and formulating questions with Gemma..."):
                try:
                    payload = {
                        "document_ids": quiz_doc_ids,
                        "topic": quiz_topic,
                        "difficulty": quiz_difficulty,
                        "number_of_questions": num_questions,
                        "question_types": question_types,
                        "student_id": student_id,
                    }
                    q_res = requests.post(f"{API_URL}/generate-quiz", json=payload)
                    if q_res.status_code == 200:
                        st.session_state["current_quiz"] = q_res.json()
                        st.success(f"Quiz generated with {len(st.session_state['current_quiz']['questions'])} questions!")
                    else:
                        st.error(f"Failed to generate quiz: {q_res.json().get('detail', q_res.text)}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # Display active quiz
    if "current_quiz" in st.session_state and st.session_state["current_quiz"]:
        quiz = st.session_state["current_quiz"]
        st.markdown(f"### 📋 Quiz: {quiz['topic']} ({quiz['difficulty'].title()})")

        with st.form("quiz_submission_form"):
            user_answers = {}
            for idx, q in enumerate(quiz["questions"], 1):
                st.markdown(f"**Q{idx}. {q['question_text']}**")
                q_id = q["question_id"]
                q_type = q["question_type"]

                if q_type == "mcq" and q.get("options"):
                    user_answers[q_id] = st.radio(
                        f"Select answer for Q{idx}:",
                        options=q["options"],
                        key=f"mcq_{q_id}",
                        label_visibility="collapsed"
                    )
                else:
                    user_answers[q_id] = st.text_input(
                        f"Write your answer for Q{idx}:",
                        key=f"text_{q_id}",
                        placeholder="Type concise answer here..."
                    )
                st.write("")

            submitted = st.form_submit_button("Submit All Answers & Get Feedback", type="primary")

        if submitted:
            st.markdown("### 📝 Results & Detailed Feedback")
            total_score = 0.0
            max_possible = len(quiz["questions"])

            for q in quiz["questions"]:
                q_id = q["question_id"]
                ans = user_answers.get(q_id, "")
                if not ans:
                    st.warning(f"Q: '{q['question_text']}' was left blank.")
                    continue

                with st.spinner(f"Evaluating answer for Question #{q_id}..."):
                    try:
                        sub_payload = {
                            "question_id": q_id,
                            "student_answer": ans,
                            "student_id": student_id,
                            "time_taken_seconds": 10.0
                        }
                        sub_res = requests.post(f"{API_URL}/submit-answer", json=sub_payload)
                        if sub_res.status_code == 200:
                            result = sub_res.json()
                            total_score += result["score"]
                            card_color = "🟢" if result["is_correct"] else "🔴"
                            st.markdown(f"#### {card_color} {q['question_text']}")
                            st.write(f"**Your answer:** {ans}")
                            st.write(f"**Feedback:** {result['feedback']}")
                            st.info(f"💡 Revision Recommendation: {result['suggested_revision_topic']}")
                    except Exception as e:
                        st.error(f"Error submitting answer: {e}")

            st.metric("Total Score", f"{total_score:.1f} / {max_possible}")


# =============================================================
# TAB 3: TOPIC MASTERY & PROGRESS
# =============================================================
with tab_progress:
    st.subheader("Your Topic-Wise Mastery & Revision Tracker")
    st.caption("Stored locally in SQLite. Mastery is automatically computed as: (Correct Attempts / Total Attempts) * 100.")

    if st.button("🔄 Refresh Progress Data"):
        st.rerun()

    try:
        prog_res = requests.get(f"{API_URL}/progress/{student_id}")
        if prog_res.status_code == 200:
            prog = prog_res.json()

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Overall Mastery", f"{prog['overall_mastery']}%")
            with col_m2:
                st.metric("Quizzes Completed", prog["total_quizzes_taken"])
            with col_m3:
                st.metric("Total Questions Attempted", prog["total_questions_attempted"])

            # Recommended revision alerts
            recs = prog.get("recommended_revision_topics", [])
            if recs:
                st.warning(f"⚠️ **Recommended Topics for Revision:** {', '.join(set(recs))}")
            else:
                st.success("🎉 Excellent! All tested topics are currently in the 'Strong' mastery tier (≥ 80%).")

            # Chart of topic mastery
            topics_data = prog.get("topics", [])
            if topics_data:
                df = pd.DataFrame(topics_data)
                
                # Color mapping
                color_map = {
                    "Strong": "#2ecc71",
                    "Needs revision": "#f39c12",
                    "Weak topic": "#e74c3c"
                }
                df["Color"] = df["status"].map(color_map)

                fig = px.bar(
                    df,
                    x="topic",
                    y="mastery_percentage",
                    color="status",
                    color_discrete_map=color_map,
                    title="Topic Mastery Percentage (%)",
                    labels={"mastery_percentage": "Mastery %", "topic": "Topic", "status": "Classification"},
                    range_y=[0, 100],
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📋 Topic Breakdown Table")
                st.dataframe(
                    df[["topic", "mastery_percentage", "correct_attempts", "total_attempts", "status"]].rename(
                        columns={
                            "topic": "Topic",
                            "mastery_percentage": "Mastery (%)",
                            "correct_attempts": "Correct",
                            "total_attempts": "Total Attempts",
                            "status": "Level"
                        }
                    ),
                    use_container_width=True
                )
            else:
                st.info("No quiz attempts recorded yet. Take a practice quiz in the 'Practice Quiz' tab to start tracking mastery!")
        else:
            st.error("Could not fetch student progress data.")
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")

