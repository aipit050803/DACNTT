from pypdf import PdfReader
from docx import Document
from typing import List, Tuple
import re

def _pdf_to_text(path: str) -> Tuple[str, List[int]]:
    reader = PdfReader(path)
    pages = []
    page_map = []  # starting char index of each page
    cursor = 0
    for i, p in enumerate(reader.pages):
        t = p.extract_text() or ""
        pages.append(t)
        page_map.append(cursor)
        cursor += len(t)
    return "\n\n".join(pages), page_map

def _docx_to_text(path: str) -> str:
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        text, _ = _pdf_to_text(path)
        return text
    elif path.lower().endswith(".docx"):
        return _docx_to_text(path)
    else:
        raise ValueError("Unsupported file type")

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def chunk_text(text: str, max_chars: int = 4000, overlap: int = 600) -> List[str]:
    """Roughly ~900-1000 tokens when max_chars=4000. Adjust as needed."""
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


_HEADING_WORDS = r"(Chương|Chapter|CHUONG|Bài|Bai|Phần|Phan|Mục|Muc|Unit|Section)"
_ROMAN = r"(?:[IVXLCDM]+)"   # I, II, III...
_DECNUM = r"(?:\d+)"
_NUMWORD = rf"(?:{_ROMAN}|{_DECNUM})"

# 1) Dạng có từ khóa: "Chương 2:", "Bài 3 -", "Phần II", "Section 4.1 ..."
KW_RE = re.compile(
    rf"^\s*{_HEADING_WORDS}\s+({_NUMWORD}(?:\.\d+)*)\b[:.\-\s]*(.*)$",
    re.I
)

# 2) Dạng chỉ số: "1. Giới thiệu", "2. Phương pháp", "3 Kết quả"
PURE_NUM_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})*)\s+(.+)$")

def _flush(curr, chapters):
    if curr and curr["content"].strip():
        chapters.append(curr)

def split_into_chapters(text: str) -> list[dict]:
    """
    Trả list[{'title','content'}] bằng cách quét qua từng dòng,
    nhận diện heading theo nhiều dạng Việt/Anh + số, và gộp nội dung theo chương lớn.

    Quy ước:
    - Nếu gặp cấp '1.2' thì vẫn gộp về '1' (coi như chương 1).
    - Nếu không thấy heading nào → trả 1 chương 'Mở đầu'.
    """
    chapters: list[dict] = []
    curr = None

    for raw in text.splitlines():
        line = raw.strip()

        m1 = KW_RE.match(line)
        if m1:
            # Ví dụ: "Bài 3 – Hồi quy", "Phần II: ..."
            num_part = m1.group(2)  # số/chuỗi số
            suffix = m1.group(3).strip() if m1.lastindex and m1.lastindex >= 3 else ""
            # Lấy chương gốc (phần trước dấu '.')
            major = str(num_part).split(".")[0]
            title = f"{m1.group(1).capitalize()} {major}"
            if suffix:
                title += f" – {suffix}"
            _flush(curr, chapters)
            curr = {"title": title, "content": ""}
            continue

        m2 = PURE_NUM_RE.match(line)
        if m2 and (len(m2.group(1).split(".")) in (1, 2)):   # chỉ nhận 1.x làm chương/mục lớn
            major = m2.group(1).split(".")[0]
            suffix = m2.group(2).strip()
            title = f"Chương {major}"
            if suffix:
                title += f" – {suffix}"
            _flush(curr, chapters)
            curr = {"title": title, "content": ""}
            continue

        if curr is None:
            curr = {"title": "Mở đầu", "content": ""}

        curr["content"] += (raw + "\n")

    _flush(curr, chapters)

    # Nếu chỉ có 1 chương 'Mở đầu' và quá ít chữ -> trả rỗng để fallback chunk
    if len(chapters) == 1 and chapters[0]["title"] == "Mở đầu" and len(chapters[0]["content"].strip()) < 200:
        return []

    # Loại bỏ các chương rỗng
    chapters = [c for c in chapters if c["content"].strip()]

    # Gộp các mục lặt vặt nếu phát hiện quá nhiều chương cực ngắn
    MIN_LEN = 120
    merged = []
    buffer = None
    for c in chapters:
        if len(c["content"]) < MIN_LEN:
            if buffer is None:
                buffer = {"title": c["title"], "content": c["content"]}
            else:
                buffer["content"] += "\n" + c["content"]
        else:
            if buffer:
                merged.append(buffer)
                buffer = None
            merged.append(c)
    if buffer:
        merged.append(buffer)

    return merged