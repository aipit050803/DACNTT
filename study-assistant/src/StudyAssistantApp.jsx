import React, { useMemo, useRef, useState } from 'react';
import * as api from './lib/api.js'; // dùng import trực tiếp

const TABS = ['Summary', 'Flashcards', 'Quiz', 'Chat'];
const cx = (...xs) => xs.filter(Boolean).join(' ');

export default function StudyAssistantApp() {
  const [docs, setDocs] = useState([]);
  const [activeDocId, setActiveDocId] = useState(null);
  const [activeTab, setActiveTab] = useState('Summary');

  const [summary, setSummary] = useState({ overall: '', sections: [] });
  const [flashcards, setFlashcards] = useState([]);
  const [quizzes, setQuizzes] = useState([]);

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSessionId, setChatSessionId] = useState(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const activeDoc = useMemo(
    () => docs.find(d => d.id === activeDocId) || null,
    [docs, activeDocId]
  );

  const fileRef = useRef(null);

  async function handleUpload(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const f = files[0];

    const tempId = `local-${Date.now()}`;
    setDocs(prev => [{ id: tempId, name: f.name, size: f.size, status: 'processing' }, ...prev]);
    setActiveDocId(tempId);
    setError(null);
    setBusy(true);

    try {
      // Upload thực
      const up = await api.uploadDocument(f);
      const docId = up.doc_id || up.id;
      setDocs(prev => prev.map(d => d.id === tempId ? { ...d, id: docId } : d));
      setActiveDocId(docId);

      await api.waitForProcessed(docId);

      const [sum, cards, qs] = await Promise.all([
        api.getSummary(docId),
        api.getFlashcards(docId),
        api.getQuizzes(docId),
      ]);
      setSummary(sum);
      setFlashcards(cards);
      setQuizzes(qs);

      // tạo session chat thật
      const sess = await api.createChatSession(docId);
      setChatSessionId(sess.session_id);

      setDocs(prev => prev.map(d => d.id === docId ? { ...d, status: 'done' } : d));
    } catch (e) {
      console.error('Upload/Process error:', e);
      setDocs(prev => prev.map(d => d.id === tempId ? { ...d, status: 'failed' } : d));
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleAsk() {
    const q = chatInput.trim();
    if (!q) return;

    setChatMessages(prev => [...prev, { role: 'user', content: q }]);
    setChatInput('');
    setError(null);

    try {
      setBusy(true);

      // nếu chưa có session thì tạo ngay (đảm bảo không rơi vào "demo")
      if (!chatSessionId) {
        const sess = await api.createChatSession(activeDocId);
        setChatSessionId(sess.session_id);
      }

      const resp = await api.sendChatMessage(chatSessionId, q);
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: resp.answer, citations: resp.citations || [] },
      ]);
    } catch (e) {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Lỗi: ${e.message || e}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Sidebar */}
      <aside className="col-span-12 lg:col-span-3">
        <UploadCard onUpload={handleUpload} fileRef={fileRef} busy={busy} />
        <DocList docs={docs} activeId={activeDocId} onSelect={setActiveDocId} />
      </aside>

      {/* Main */}
      <section className="col-span-12 lg:col-span-9 rounded-2xl border bg-white shadow-sm">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div>
            <div className="text-sm text-gray-500">Tài liệu</div>
            <div className="text-lg font-semibold">{activeDoc?.name || '(Chưa chọn)'}</div>
          </div>
          <div className="flex gap-1">
            {TABS.map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={cx(
                  'rounded-xl px-3 py-1.5 text-sm border',
                  activeTab === t ? 'border-black' : 'border-gray-200 hover:bg-gray-50'
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4">
          {error && <div className="mb-2 text-red-600 text-sm">{String(error)}</div>}
          {!activeDoc && <EmptyState />}

          {activeDoc && activeTab === 'Summary' && <SummaryView busy={busy} summary={summary} />}
          {activeDoc && activeTab === 'Flashcards' && <FlashcardsView cards={flashcards} />}
          {activeDoc && activeTab === 'Quiz' && <QuizView quizzes={quizzes} />}
          {activeDoc && activeTab === 'Chat' && (
            <ChatView
              messages={chatMessages}
              input={chatInput}
              setInput={setChatInput}
              onAsk={handleAsk}
              busy={busy}
            />
          )}
        </div>
      </section>
    </div>
  );
}

/* ---------- Sub-components ---------- */

function UploadCard({ onUpload, fileRef, busy }) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <h3 className="font-semibold mb-2">Tải tài liệu (PDF/Word)</h3>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); onUpload(e.dataTransfer.files); }}
        className={cx('mt-2 flex h-28 cursor-pointer items-center justify-center rounded-xl border border-dashed text-sm', dragOver ? 'bg-gray-50' : 'bg-white')}
        onClick={() => fileRef.current?.click()}
      >
        <div className="text-center">
          <div className="font-medium">Kéo thả file vào đây</div>
          <div className="text-gray-500">Hoặc bấm để chọn file</div>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.doc,.docx"
        className="hidden"
        onChange={(e) => onUpload(e.target.files)}
      />

      <div className="mt-3 text-xs text-gray-500">Kích thước ≤ 25MB. Dữ liệu sẽ được xử lý an toàn.</div>
      {busy && <div className="mt-3 text-xs text-blue-600">Đang xử lý…</div>}
    </div>
  );
}

function DocList({ docs, activeId, onSelect }) {
  return (
    <div className="mt-4 rounded-2xl border bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold">Tài liệu của bạn</h3>
        <span className="text-xs text-gray-500">{docs.length} mục</span>
      </div>
      <div className="space-y-2 max-h-[360px] overflow-auto pr-1">
        {docs.length === 0 && <div className="text-sm text-gray-500">Chưa có tài liệu. Hãy upload ở trên.</div>}
        {docs.map(d => (
          <button
            key={d.id}
            onClick={() => onSelect(d.id)}
            className={cx('w-full rounded-xl border px-3 py-2 text-left hover:bg-gray-50', activeId === d.id ? 'border-black' : 'border-gray-200')}
          >
            <div className="flex items-center justify-between">
              <div className="font-medium truncate">{d.name}</div>
              <span className={cx(
                'rounded-full px-2 py-0.5 text-xs',
                d.status === 'done' ? 'bg-green-100 text-green-700'
                  : d.status === 'failed' ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700'
              )}>
                {d.status}
              </span>
            </div>
            <div className="text-xs text-gray-500">{d.size ? `${Math.ceil(d.size/1024)} KB` : ''}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="h-12 w-12 rounded-2xl bg-black text-white flex items-center justify-center mb-3">AI</div>
      <h3 className="text-lg font-semibold">Chưa có tài liệu nào được chọn</h3>
      <p className="mt-1 text-sm text-gray-600">Hãy tải tài liệu và chọn để bắt đầu tóm tắt, luyện flashcard, làm quiz hoặc hỏi đáp.</p>
    </div>
  );
}

function SummaryView({ busy, summary }) {
  return (
    <div>
      <h4 className="font-semibold mb-2">Tóm tắt tổng quan</h4>
      <p className="text-[15px] leading-7 bg-gray-50 rounded-xl p-4 border whitespace-pre-wrap">
        {summary.overall || (busy ? 'Đang sinh tóm tắt…' : '(Chưa có dữ liệu)')}
      </p>
    </div>
  );
}

function FlashcardsView({ cards }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  if (!cards || cards.length === 0) return <div className="text-sm text-gray-500">(Chưa có flashcard)</div>;

  const card = cards[index];
  const next = () => { setFlipped(false); setIndex((index + 1) % cards.length); };
  const prev = () => { setFlipped(false); setIndex((index - 1 + cards.length) % cards.length); };

  return (
    <div>
      <div className="mb-2 text-sm text-gray-500">{index + 1}/{cards.length}</div>
      <div
        className={cx('rounded-2xl border p-6 text-center min-h-[160px] flex items-center justify-center cursor-pointer select-none', 'transition-transform duration-300')}
        onClick={() => setFlipped(!flipped)}
        title="Bấm để lật thẻ"
      >
        {!flipped ? (
          <div>
            <div className="text-xs uppercase tracking-wide text-gray-500">Câu hỏi</div>
            <div className="mt-2 text-lg font-semibold">{card.q}</div>
          </div>
        ) : (
          <div>
            <div className="text-xs uppercase tracking-wide text-gray-500">Đáp án</div>
            <div className="mt-2 text-lg font-semibold text-green-700">{card.a}</div>
          </div>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button onClick={prev} className="rounded-xl border px-3 py-1.5 text-sm hover:bg-gray-50">Trước</button>
        <div className="text-xs text-gray-600">Tags: {(card.tags || []).join(', ') || '—'}</div>
        <button onClick={next} className="rounded-xl border px-3 py-1.5 text-sm hover:bg-gray-50">Tiếp</button>
      </div>
    </div>
  );
}

function QuizView({ quizzes }) {
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);
  if (!quizzes || quizzes.length === 0) return <div className="text-sm text-gray-500">(Chưa có câu hỏi)</div>;

  const q = quizzes[idx];
  const submit = () => {
    if (selected == null) return;
    if (q.opts[selected] === q.answer) setScore(s => s + 1);
    if (idx + 1 < quizzes.length) { setIdx(idx + 1); setSelected(null); } else { setDone(true); }
  };
  const reset = () => { setIdx(0); setSelected(null); setScore(0); setDone(false); };

  return (
    <div>
      {!done ? (
        <div>
          <div className="mb-2 text-sm text-gray-500">Câu {idx + 1}/{quizzes.length} • Độ khó: <span className="font-medium">{q.difficulty || 'Med'}</span></div>
          <div className="rounded-2xl border p-4">
            <div className="font-semibold mb-2">{q.q}</div>
            <div className="space-y-2">
              {q.opts.map((opt, i) => (
                <label key={i} className={cx('flex items-center gap-2 rounded-xl border p-2 cursor-pointer', selected === i ? 'border-black' : 'border-gray-200 hover:bg-gray-50')}>
                  <input type="radio" name="opt" checked={selected === i} onChange={() => setSelected(i)} />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between">
              <button onClick={submit} className="rounded-xl border px-3 py-1.5 text-sm hover:bg-gray-50">Trả lời</button>
              <div className="text-xs text-gray-600">{selected != null ? `Giải thích: ${q.why}` : ''}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-10">
          <div className="text-3xl font-bold">{score}/{quizzes.length}</div>
          <div className="mt-2 text-sm text-gray-600">Điểm số của bạn</div>
          <button onClick={reset} className="mt-4 rounded-xl border px-3 py-1.5 text-sm hover:bg-gray-50">Làm lại</button>
        </div>
      )}
    </div>
  );
}

function ChatView({ messages, input, setInput, onAsk, busy }) {
  return (
    <div className="grid grid-rows-[1fr_auto] h-[480px]">
      <div className="overflow-auto pr-2 space-y-3">
        {messages.length === 0 && (
          <div className="text-sm text-gray-500">
            Hỏi bất cứ điều gì liên quan đến tài liệu. Ví dụ: “Định nghĩa quan trọng là gì?”, “Tóm tắt nội dung chính?”.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cx('rounded-2xl border p-3', m.role === 'user' ? 'bg-gray-50' : 'bg-white')}>
            <div className="text-xs uppercase tracking-wide text-gray-500">{m.role}</div>
            <div className="mt-1 text-sm whitespace-pre-wrap">{m.content}</div>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-2 text-xs text-gray-500">
                Nguồn:{' '}
                {m.citations.map((c, j) => {
                  const label =
                    c.page != null || c.heading
                      ? `Trang ${c.page ?? '—'} – ${c.heading ?? '—'}`
                      : (c.idx != null ? `Đoạn #${c.idx}` : '—');
                  return (j ? ', ' : '') + `[${label}]`;
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={2}
            placeholder="Nhập câu hỏi…"
            className="flex-1 rounded-2xl border p-3 text-sm focus:outline-none focus:ring-2 focus:ring-black"
          />
          <button
            onClick={onAsk}
            disabled={busy}
            className={cx('rounded-2xl border px-4 py-2 text-sm', busy ? 'opacity-60' : 'hover:bg-gray-50')}
          >
            Gửi
          </button>
        </div>
        <div className="mt-1 text-xs text-gray-500">Câu trả lời dựa trên các đoạn ngữ cảnh từ tài liệu của bạn.</div>
      </div>
    </div>
  );
}
