from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, history
from app.core.config import settings
from app.db.database import Base, engine
import app.models  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Refarm AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(history.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
