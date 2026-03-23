from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReferenceOut(BaseModel):
    title: str
    url: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    references: List[ReferenceOut]
    created_at: datetime

    class Config:
        from_attributes = True
