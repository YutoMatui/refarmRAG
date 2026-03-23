import logging
import time
from typing import List

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

_EMBED_MAX_RETRIES = 5


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _embed_with_retry(
    text: str,
    task_type: str,
) -> List[float]:
    """Call Gemini Embedding API with exponential backoff retry."""
    client = _get_client()
    last_exc: Exception | None = None

    for attempt in range(_EMBED_MAX_RETRIES):
        try:
            result = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.EMBEDDING_DIM,
                ),
            )
            if not result.embeddings:
                raise ValueError("Embedding returned empty result")
            return list(result.embeddings[0].values)
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            is_retryable = any(
                keyword in err_str
                for keyword in ["429", "resource_exhausted", "500", "503", "unavailable", "deadline"]
            )
            if not is_retryable:
                raise
            wait = (2 ** attempt) + 0.5
            logger.warning(
                "Embedding API error (attempt %d/%d): %s — retrying in %.1fs",
                attempt + 1, _EMBED_MAX_RETRIES, e, wait,
            )
            time.sleep(wait)

    raise last_exc  # type: ignore[misc]


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
    return _embed_with_retry(text, task_type="RETRIEVAL_QUERY")


def embed_document(text: str) -> List[float]:
    return _embed_with_retry(text, task_type="RETRIEVAL_DOCUMENT")
