import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, history
from app.core.config import settings
from app.db.database import Base, engine
import app.models  # noqa: F401

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Refarm AI Assistant")

allowed_origins = [
    origin.strip()
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- グローバル例外ハンドラー ---
# 未処理の例外が発生しても、CORSミドルウェアが正しくヘッダーを付与できるよう
# JSONResponse を返す（500 が生の例外のまま伝搬すると CORS ヘッダーが欠落する）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(history.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
