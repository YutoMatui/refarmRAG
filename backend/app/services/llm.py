from typing import List

from google import genai
from google.genai import types

from app.core.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate_answer(question: str, context: str, history: List[dict]) -> str:
    client = _get_client()

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

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )
    return response.text or "回答が生成できませんでした。"


def embed_text(text: str) -> List[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=settings.EMBEDDING_DIM,
        ),
    )
    if not result.embeddings:
        raise ValueError("Embedding failed")
    return list(result.embeddings[0].values)


def embed_document(text: str) -> List[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=settings.EMBEDDING_DIM,
        ),
    )
    if not result.embeddings:
        raise ValueError("Embedding failed")
    return list(result.embeddings[0].values)
