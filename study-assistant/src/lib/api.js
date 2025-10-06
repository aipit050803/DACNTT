// src/lib/api.js
// Gọi backend FastAPI
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

/** Upload file -> { doc_id } */
export async function uploadDocument(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}/documents`, { method: 'POST', body: fd });
  if (!res.ok) throw new Error(`Upload failed ${res.status}`);
  return res.json();
}

/** GET /documents/{id} cho tới khi status=done/failed */
export async function waitForProcessed(docId, timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const r = await fetch(`${API_BASE}/documents/${docId}`);
    if (!r.ok) throw new Error(`poll failed ${r.status}`);
    const meta = await r.json();
    if (meta.status === 'done') return meta;
    if (meta.status === 'failed') throw new Error('process failed');
    await new Promise(r => setTimeout(r, 800));
  }
  throw new Error('timeout waiting document processed');
}

export async function getSummary(docId) {
  const r = await fetch(`${API_BASE}/documents/${docId}/summary`);
  if (!r.ok) throw new Error(`summary ${r.status}`);
  return r.json();
}

export async function getFlashcards(docId) {
  const r = await fetch(`${API_BASE}/documents/${docId}/flashcards`);
  if (!r.ok) throw new Error(`flashcards ${r.status}`);
  return r.json();
}

export async function getQuizzes(docId) {
  const r = await fetch(`${API_BASE}/documents/${docId}/quizzes`);
  if (!r.ok) throw new Error(`quizzes ${r.status}`);
  return r.json();
}

/** Tạo session chat (hiện backend chưa dùng, nhưng để tương thích tương lai) */
export async function createChatSession(docId) {
  const url = docId ? `${API_BASE}/chat/session?doc_id=${encodeURIComponent(docId)}` : `${API_BASE}/chat/session`;
  const r = await fetch(url, { method: 'POST' });
  if (!r.ok) throw new Error(`session ${r.status}`);
  return r.json(); // { session_id }
}

/** Gửi câu hỏi */
export async function sendChatMessage(sessionId, question) {
  const r = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // gửi cả "question" và "q" để khớp mọi schema
    body: JSON.stringify({ question, q: question, session_id: sessionId || null })
  });
  if (!r.ok) throw new Error(`chat ${r.status}`);
  return r.json();
}

