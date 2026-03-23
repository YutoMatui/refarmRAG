from sqlalchemy.dialects.postgresql import insert

from app.db.database import SessionLocal
from app.models.notion_document import NotionDocument
from app.services.llm import embed_document
from app.services.notion import fetch_notion_documents


def upsert_documents():
    db = SessionLocal()
    try:
        documents = fetch_notion_documents()
        for doc in documents:
            embedding = embed_document(doc["content"])
            stmt = insert(NotionDocument).values(
                page_url=doc["url"],
                title=doc["title"],
                content=doc["content"],
                embedding=embedding,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["page_url"],
                set_={
                    "title": doc["title"],
                    "content": doc["content"],
                    "embedding": embedding,
                },
            )
            db.execute(stmt)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    upsert_documents()
