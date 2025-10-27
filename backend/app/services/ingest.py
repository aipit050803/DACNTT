# app/services/ingest.py
from typing import List, Tuple
from pypdf import PdfReader
from docx import Document
import re

def _pdf_to_text(path: str) -> Tuple[str, List[int]]:
    reader = PdfReader(path)
    pages = []
    page_map = []
    cursor = 0
    for p in reader.pages:
        t = p.extract_text() or ""
        pages.append(t)
        page_map.append(cursor)
        cursor += len(t)
    return "\n\n".join(pages), page_map

def _docx_to_text(path: str) -> str:
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text(path: str) -> str:
    p = path.lower()
    if p.endswith(".pdf"):
        text, _ = _pdf_to_text(path)
        return text
    if p.endswith(".docx"):
        return _docx_to_text(path)
    raise ValueError("Unsupported file type")

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def chunk_text(text: str, max_chars: int = 4000, overlap: int = 600) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        j = min(i + max_chars, len(text))
        chunk = text[i:j]
        chunks.append(chunk)
        if j == len(text):
            break
        i = j - overlap
    return chunks