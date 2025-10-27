# app/main.py
from __future__ import annotations
import os, uuid, traceback
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import (
    UploadResp, DocMeta, SummaryResp, SummarySection,
    Flashcard, QuizItem, ChatSessionResp, ChatMessageResp
)
from app.services.ingest import extract_text, chunk_text
from app.services.vector import upsert_doc, search_similar
from app.services.ai import summarize_overall, answer_with_context

# In-memory (sau thay DB)
DOCS: dict[str, DocMeta] = {}
DOC_TEXT: dict[str, str] = {}

app = FastAPI(title="Study Assistant API", version="0.3")

# CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/documents", response_model=list[DocMeta])
def list_docs():
    return list(DOCS.values())

@app.post("/documents", response_model=UploadResp)
async def upload_document(file: UploadFile = File(...)):
    doc_id = str(uuid.uuid4())
    title = file.filename or "upload.bin"
    DOCS[doc_id] = DocMeta(id=doc_id, title=title, status="processing")

    tmp_dir = os.getenv("TMP_DIR") or os.getenv("TEMP") or "/tmp"
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"{doc_id}-{title}")

        # Lưu file tạm
        blob = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(blob)

        # Trích nội dung
        text = extract_text(tmp_path) or ""
        DOC_TEXT[doc_id] = text

        # Chunk + upsert Vector DB (nếu lỗi vẫn bỏ qua, chỉ cảnh báo)
        try:
            chunks = chunk_text(text)
            upsert_doc(doc_id, chunks)
        except Exception as ve:
            print("WARN upsert_doc failed:", repr(ve))

        DOCS[doc_id].status = "done"
        return UploadResp(doc_id=doc_id)

    except Exception as e:
        print("ERROR upload_document:", repr(e))
        traceback.print_exc()
        DOCS[doc_id].status = "failed"
        DOCS[doc_id].message = str(e)
        # vẫn trả 200 để FE có thể hiện 'failed'
        return UploadResp(doc_id=doc_id)

@app.get("/documents/{doc_id}", response_model=DocMeta)
def get_doc(doc_id: str):
    if doc_id not in DOCS:
        return JSONResponse(status_code=404, content={"message": "not found"})
    return DOCS[doc_id]

@app.get("/documents/{doc_id}/summary", response_model=SummaryResp)
def get_summary(doc_id: str):
    text = DOC_TEXT.get(doc_id, "")
    if not text:
        return JSONResponse(status_code=404, content={"message": "no text"})
    try:
        overall = summarize_overall(text)
    except Exception as e:
        print("WARN summarize_overall:", repr(e))
        overall = "Xin lỗi, hiện chưa tóm tắt được (mô hình local chưa sẵn sàng)."
    return SummaryResp(overall=overall, sections=[])

@app.get("/documents/{doc_id}/flashcards", response_model=list[Flashcard])
def get_flashcards(doc_id: str):
    text = DOC_TEXT.get(doc_id, "")
    if not text:
        return JSONResponse(status_code=404, content={"message": "no text"})
    demo = [
        {"q": "Khái niệm chính của tài liệu?", "a": "Các ý chính và kết luận được trình bày trong phần tóm tắt."},
        {"q": "Ứng dụng quan trọng?", "a": "Một số ví dụ ứng dụng thực tế từ nội dung tài liệu."},
    ]
    return [Flashcard(**i) for i in demo]

@app.get("/documents/{doc_id}/quizzes", response_model=list[QuizItem])
def get_quizzes(doc_id: str):
    text = DOC_TEXT.get(doc_id, "")
    if not text:
        return JSONResponse(status_code=404, content={"message": "no text"})
    sample = [{
        "q": "Mục tiêu của tóm tắt tổng quan là gì?",
        "opts": ["Nêu tất cả chi tiết", "Cô đọng ý chính", "Trình bày công thức đầy đủ", "Sao chép nguyên văn"],
        "answer": "B",
        "why": "Tóm tắt để nắm ý chính nhanh, không lan man."
    }]
    return [QuizItem(**q) for q in sample]

@app.post("/chat/session", response_model=ChatSessionResp)
def create_chat_session(doc_id: str | None = None):
    return ChatSessionResp(session_id=str(uuid.uuid4()))

@app.post("/chat/message", response_model=ChatMessageResp)
def chat_message(req: dict = Body(...)):
    # chấp nhận cả "question" lẫn "q"
    question = (req or {}).get("question") or (req or {}).get("q") or ""
    if not question.strip():
        return JSONResponse(status_code=400, content={"message": "missing question"})

    hits = search_similar(question, k=6)
    contexts = [h["text"] for h in hits]
    try:
        ans = answer_with_context(question, contexts)
    except Exception as e:
        ans = f"Không gọi được mô hình (fallback): {e}"

    cites = []
    for h in hits[:2]:
        meta = h.get("meta", {}) if isinstance(h, dict) else {}
        item = {}
        if "page" in meta: item["page"] = meta["page"]
        if "heading" in meta: item["heading"] = meta["heading"]
        if not item: item["idx"] = meta.get("idx", 0)
        cites.append(item)

    return ChatMessageResp(answer=ans, citations=cites)
