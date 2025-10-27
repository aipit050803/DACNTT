# app/schemas.py
from pydantic import BaseModel
from typing import List, Dict

class UploadResp(BaseModel):
    doc_id: str

class DocMeta(BaseModel):
    id: str
    title: str
    status: str = "processing"  # processing | done | failed
    message: str | None = None

class SummarySection(BaseModel):
    title: str
    content: str

class SummaryResp(BaseModel):
    overall: str
    sections: List[SummarySection] = []

class Flashcard(BaseModel):
    q: str
    a: str
    tags: List[str] = []

class QuizItem(BaseModel):
    q: str
    opts: List[str]
    answer: str
    why: str
    difficulty: str = "Med"

class ChatSessionResp(BaseModel):
    session_id: str

class ChatMessageResp(BaseModel):
    answer: str
    citations: List[Dict] = []

