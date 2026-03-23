from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.notion_document import NotionDocument
from app.services.llm import embed_text


def retrieve_context(db: Session, query: str, top_k: int = 5) -> Tuple[str, List[dict]]:
    embedding = embed_text(query)
    documents = (
        db.query(NotionDocument)
        .order_by(NotionDocument.embedding.cosine_distance(embedding))
        .limit(top_k)
        .all()
    )

    context_parts = []
    references = []
    for doc in documents:
        context_parts.append(f"# {doc.title}\n{doc.content}")
        references.append({"title": doc.title, "url": doc.page_url})

    return "\n\n".join(context_parts), references
