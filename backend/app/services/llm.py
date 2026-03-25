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
        "あなたは『りふぁーむ』の新入生オンボーディングを支援する優秀なAIアシスタントです。\n"
        "ユーザーからの質問に対し、以下の【ルール】に厳格に従って回答してください。\n\n"
        "【ルール】\n"
        "1. 厳格な情報源の制限: 回答は必ず <context> タグ内に提供されたNotionの情報のみに基づいて作成してください。"
        "事前知識や推測、一般的な事実は絶対に混ぜないでください。\n"
        "2. 不明な場合の対応: <context> の情報だけでは質問に答えられない場合や、確証が持てない場合は、"
        "決して推測で答えを作らず「提供されたNotionのデータには、その情報が見当たりませんでした」と正直に答えてください。\n"
        "3. 最新情報の優先: <context> 内に類似した情報が複数ある場合や、内容が矛盾している場合は、"
        "記載されている「更新日（または日付）」が最も新しいものを正として回答してください。\n"
        "4. 履歴の扱い: <history> は会話の文脈（指示語の解決）のためにのみ使用し、事実の根拠は必ず <context> から取得してください。\n"
        "5. 情報源の明記: 回答の**各文末**に、根拠となる <context> のIDを角括弧で付与してください（例: [1]）。\n"
        "6. 参考一覧: 回答の最後に、使用したIDの一覧を「参考:」として箇条書きで示してください（形式: [ID] タイトル - URL）。\n\n"
        "<context>\n{context}\n</context>\n\n"
        "<history>\n{history_text}\n</history>\n\n"
        "質問: {question}\n\n"
        "回答は日本語で、箇条書きなどを使い分かりやすく簡潔にまとめてください。"
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
