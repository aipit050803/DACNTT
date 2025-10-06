from pydantic import BaseModel, Field
from typing import List, Optional

class UploadResp(BaseModel):
    doc_id: str

class DocMeta(BaseModel):
    id: str
    title: str
    status: str = "processing"  # processing | done | failed

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

class ChatMessageReq(BaseModel):
    session_id: str
    question: str

class ChatMessageResp(BaseModel):
    answer: str
    citations: List[dict] = []  # [{"page": 3, "heading": "..."}]
