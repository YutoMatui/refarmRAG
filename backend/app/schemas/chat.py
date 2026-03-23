from typing import List, Optional
from pydantic import BaseModel

from app.schemas.history import MessageOut, ReferenceOut, SessionOut


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    question: str


class ChatResponse(BaseModel):
    session: SessionOut
    message: MessageOut
    references: List[ReferenceOut]
