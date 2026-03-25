from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.db.database import Base


class NotionChunk(Base):
    __tablename__ = "notion_chunks"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, index=True)
    page_url = Column(String, nullable=False)
    page_title = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True)
    embedding = Column(Vector(settings.EMBEDDING_DIM))
