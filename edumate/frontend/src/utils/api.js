// API client for EduMate backend
const isDev = typeof window !== 'undefined' && (window.location.port === '3000' || window.location.port === '5173');
const API_BASE = isDev ? 'http://127.0.0.1:8000' : '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchDocuments(studentId) {
  const url = studentId
    ? `${API_BASE}/documents?student_id=${encodeURIComponent(studentId)}`
    : `${API_BASE}/documents`;
  const res = await fetch(url);
  return res.json();
}

export async function uploadDocument(file, studentId, subject, chapter) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('student_id', studentId || 'student_1');
  formData.append('subject', subject || 'General');
  formData.append('chapter', chapter || 'General');

  const res = await fetch(`${API_BASE}/upload-document`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function chatStream(question, options = {}) {
  const body = {
    question,
    student_level: options.studentLevel || 'Class 12',
    document_ids: options.documentIds || null,
    top_k: options.topK || 4,
    direct_mode: options.directMode || false,
    target_marks: options.targetMarks || null,
  };

  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Chat request failed');
  }

  // Extract custom headers
  const sourcesJson = res.headers.get('X-Sources-JSON');
  const fallbackMode = res.headers.get('X-Fallback-Mode') === 'true';

  let sources = [];
  if (sourcesJson) {
    try { sources = JSON.parse(sourcesJson); } catch {}
  }

  return { body: res.body, sources, fallbackMode };
}

export async function generateQuiz(params) {
  const res = await fetch(`${API_BASE}/generate-quiz`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_ids: params.documentIds,
      topic: params.topic || 'General',
      difficulty: params.difficulty || 'medium',
      number_of_questions: params.numberOfQuestions || 5,
      question_types: params.questionTypes || ['mcq', 'short_answer'],
      student_id: params.studentId || 'student_1',
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Quiz generation failed');
  }
  return res.json();
}

export async function submitAnswer(params) {
  const res = await fetch(`${API_BASE}/submit-answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: params.questionId,
      student_answer: params.studentAnswer,
      student_id: params.studentId || 'student_1',
      time_taken_seconds: params.timeTaken || 0,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Submission failed');
  }
  return res.json();
}

export async function fetchProgress(studentId) {
  const res = await fetch(`${API_BASE}/progress/${encodeURIComponent(studentId)}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to fetch progress');
  }
  return res.json();
}

