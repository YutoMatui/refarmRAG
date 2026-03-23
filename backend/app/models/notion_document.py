from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.db.database import Base


class NotionDocument(Base):
    __tablename__ = "notion_documents"

    id = Column(Integer, primary_key=True, index=True)
    page_url = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM))
