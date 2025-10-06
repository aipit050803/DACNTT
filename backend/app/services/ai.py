# app/services/ai.py
import os
import json
import requests

from dotenv import load_dotenv
load_dotenv()

USE_OLLAMA = os.getenv("USE_OLLAMA", "0") == "1"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct")

def _ollama_generate(prompt: str, temperature: float = 0.2, max_tokens: int | None = None) -> str:
    """
    Gọi Ollama /api/generate. Trả về toàn bộ text.
    Ném exception nếu request lỗi để caller biết mà handle.
    """
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
    # key "response" chứa text đã sinh (khi stream=false)
    return data.get("response", "").strip()

# ---------- PUBLIC APIS used by main.py ----------

def summarize_overall(text: str) -> str:
    if not USE_OLLAMA:
        return "BẢN TÓM TẮT (DEMO): Nội dung chính của tài liệu…"

    # Giới hạn ~10–12k ký tự để tránh quá context
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


def generate_flashcards(text: str, n: int = 10) -> list[dict]:
    """Sinh flashcards (q/a)."""
    if not USE_OLLAMA:
        # fallback demo
        return [{"q": "Định nghĩa Machine Learning?", "a": "Lĩnh vực cho phép mô hình cải thiện từ dữ liệu.", "tags": ["khái niệm"]}]
    prompt = (
        f"Hãy tạo {n} thẻ hỏi-đáp (flashcards) bằng tiếng Việt từ nội dung sau.\n"
        "Mỗi thẻ dạng JSON {\"q\": \"câu hỏi\", \"a\": \"đáp án ngắn\"}. "
        "Chỉ in ra một mảng JSON hợp lệ, không giải thích thêm.\n\n"
        f"--- TÀI LIỆU ---\n{text}\n\n---\nMẢNG JSON:"
    )
    try:
        raw = _ollama_generate(prompt, temperature=0.3)
        data = json.loads(raw)
        # Chuẩn hoá về list[dict{q,a}]
        out = []
        for item in data:
            q = item.get("q") or item.get("question")
            a = item.get("a") or item.get("answer")
            if q and a:
                out.append({"q": q, "a": a, "tags": item.get("tags", [])})
        return out[:n] if out else []
    except Exception as e:
        print(f"[AI] generate_flashcards failed: {e}")
        return []

def generate_quiz(text: str, n: int = 10) -> list[dict]:
    """Sinh câu hỏi trắc nghiệm có đáp án và giải thích."""
    if not USE_OLLAMA:
        # demo
        return [{
            "q": "Mục tiêu chính của học máy là gì?",
            "opts": ["Tăng số tham số", "Giảm dữ liệu", "Cải thiện dự đoán từ kinh nghiệm", "Không cần dữ liệu"],
            "answer": "Cải thiện dự đoán từ kinh nghiệm",
            "why": "ML học từ dữ liệu để dự đoán tốt hơn",
            "difficulty": "Easy"
        }]
    prompt = (
        f"Hãy tạo {n} câu hỏi trắc nghiệm tiếng Việt từ nội dung sau.\n"
        "Mỗi phần tử JSON có dạng {\"q\":..., \"opts\":[...4 đáp án...], \"answer\":..., \"why\":..., \"difficulty\":\"Easy/Med/Hard\"}.\n"
        "Chỉ in ra MẢNG JSON hợp lệ.\n\n"
        f"--- TÀI LIỆU ---\n{text}\n\n---\nMẢNG JSON:"
    )
    try:
        raw = _ollama_generate(prompt, temperature=0.3)
        data = json.loads(raw)
        out = []
        for item in data:
            q = item.get("q") or item.get("question")
            opts = item.get("opts") or item.get("options")
            ans = item.get("answer") or item.get("correct")
            why = item.get("why") or item.get("explain")
            if q and isinstance(opts, list) and ans:
                out.append({
                    "q": q, "opts": opts, "answer": ans,
                    "why": why or "", "difficulty": (item.get("difficulty") or "Med")
                })
        return out[:n] if out else []
    except Exception as e:
        print(f"[AI] generate_quiz failed: {e}")
        return []

def answer_with_context(question: str, contexts: list[str]) -> str:
    """
    Trả lời dựa trên các đoạn context đã truy hồi (RAG).
    """
    if not USE_OLLAMA:
        return "Đây là câu trả lời demo dựa trên các đoạn văn bản liên quan."

    # Ghép context cho prompt
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
