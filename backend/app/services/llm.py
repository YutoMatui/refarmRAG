from typing import List
import google.generativeai as genai

from app.core.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


def generate_answer(question: str, context: str, history: List[dict]) -> str:
    _ensure_configured()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    history_text = "\n".join(
        [f"{item['role'].upper()}: {item['content']}" for item in history]
    )

    prompt = (
        "あなたは『りふぁーむ』のオンボーディング支援AIです。"
        "以下のNotion由来コンテキストを優先し、情報源にない内容は推測せず"
        "『Notionに記載が見当たりませんでした』と伝えてください。\n\n"
        f"<context>\n{context}\n</context>\n\n"
        f"<history>\n{history_text}\n</history>\n\n"
        f"質問: {question}\n"
        "回答は日本語で簡潔にまとめてください。"
    )

    response = model.generate_content(prompt)
    return response.text or "回答が生成できませんでした。"


def embed_text(text: str) -> List[float]:
    _ensure_configured()
    response = genai.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    embedding = response.get("embedding")
    if not embedding:
        raise ValueError("Embedding failed")
    return embedding


def embed_document(text: str) -> List[float]:
    _ensure_configured()
    response = genai.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    embedding = response.get("embedding")
    if not embedding:
        raise ValueError("Embedding failed")
    return embedding
