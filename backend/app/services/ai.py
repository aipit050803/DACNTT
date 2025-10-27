# app/services/ai.py
import os, json, requests
from dotenv import load_dotenv
load_dotenv()

USE_OLLAMA = os.getenv("USE_OLLAMA", "0") == "1"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
# Đặt tên model trong .env cho chắc; nếu không có thì dùng llama3.1 (ổn định, phổ biến)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

def _ollama_generate(prompt: str, temperature: float = 0.2, max_tokens: int | None = None) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()

def summarize_overall(text: str) -> str:
    if not USE_OLLAMA:
        return "BẢN TÓM TẮT (DEMO): Nội dung chính của tài liệu…"

    safe_text = text[:12000]
    prompt = (
        "Bạn là trợ lý học tập. Hãy tóm tắt ngắn gọn, mạch lạc (5–8 câu) cho đoạn tài liệu sau bằng tiếng Việt. "
        "Viết rõ ràng, có xuống dòng hợp lý để dễ đọc.\n\n"
        f"--- TÀI LIỆU ---\n{safe_text}\n\n--- YÊU CẦU ---\nTóm tắt:"
    )
    try:
        return _ollama_generate(prompt, temperature=0.2)
    except Exception as e:
        print(f"[AI] summarize_overall failed: {e}")
        return "BẢN TÓM TẮT (DEMO): Không gọi được mô hình, tạm thời hiển thị bản tóm tắt giả lập."

def answer_with_context(question: str, contexts: list[str]) -> str:
    if not USE_OLLAMA:
        return "Đây là câu trả lời demo dựa trên các đoạn văn bản liên quan."

    joined = "\n\n".join([f"[Đoạn #{i+1}]\n{ctx}" for i, ctx in enumerate(contexts)])
    prompt = (
        "Bạn là trợ lý học tập. Chỉ sử dụng THÔNG TIN trong các đoạn ngữ cảnh dưới đây để trả lời ngắn gọn, súc tích bằng tiếng Việt. "
        "Nếu không tìm thấy câu trả lời trong ngữ cảnh, hãy nói rõ là không chắc thay vì bịa.\n\n"
        f"--- NGỮ CẢNH ---\n{joined}\n\n"
        f"--- CÂU HỎI ---\n{question}\n\n"
        "--- TRẢ LỜI ---"
    )
    try:
        return _ollama_generate(prompt, temperature=0.1)
    except Exception as e:
        print(f"[AI] answer_with_context failed: {e}")
        return "Không gọi được mô hình – tạm thời trả lời demo."
