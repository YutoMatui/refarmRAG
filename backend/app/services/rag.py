from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.notion_chunk import NotionChunk
from app.services.llm import embed_text


def retrieve_context(db: Session, query: str, top_k: int = 5) -> Tuple[str, List[dict]]:
    embedding = embed_text(query)
    chunks = (
        db.query(NotionChunk)
        .order_by(NotionChunk.embedding.cosine_distance(embedding))
        .limit(top_k)
        .all()
    )

    context_parts = []
    references = []
    for idx, chunk in enumerate(chunks, 1):
        context_parts.append(f"[{idx}] {chunk.page_title}\n{chunk.content}")
        references.append(
            {
                "id": idx,
                "title": chunk.page_title,
                "url": chunk.page_url,
                "excerpt": chunk.content,
            }
        )

    return "\n\n".join(context_parts), references
