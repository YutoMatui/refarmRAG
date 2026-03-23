from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.history import MessageOut, SessionOut
from app.services.llm import generate_answer
from app.services.rag import retrieve_context

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == payload.session_id, ChatSession.user_id == user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        title = payload.question[:20]
        session = ChatSession(user_id=user.id, title=title or "新しい相談")
        db.add(session)
        db.commit()
        db.refresh(session)

    user_message = Message(
        session_id=session.id,
        role="user",
        content=payload.question,
        references=[],
    )
    db.add(user_message)
    db.commit()

    context, references = retrieve_context(db, payload.question)

    history_messages = (
        db.query(Message)
        .filter(Message.session_id == session.id)
        .order_by(Message.created_at.desc())
        .limit(6)
        .all()
    )
    history_payload = [
        {"role": message.role, "content": message.content}
        for message in reversed(history_messages)
    ]

    answer = generate_answer(payload.question, context, history_payload)

    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=answer,
        references=references,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        session=SessionOut.model_validate(session),
        message=MessageOut.model_validate(assistant_message),
        references=references,
    )
