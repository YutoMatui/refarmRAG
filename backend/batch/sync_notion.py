"""Notion -> PostgreSQL full sync with diff embedding and rate-limit handling.

Usage (PowerShell):
    .\\.venv\\Scripts\\python -m batch.sync_notion
    .\\.venv\\Scripts\\python -m batch.sync_notion --delay 0.5 --max-pages 10

Usage (bash / Railway):
    python -m batch.sync_notion
    python -m batch.sync_notion --delay 0.5 --max-pages 10
"""

import argparse
import json
import logging
import os
import sys
import time
from hashlib import sha256

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.notion_document import NotionDocument
from app.models.notion_chunk import NotionChunk
from app.services.llm import embed_document
from app.services.notion import fetch_notion_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".notion_sync_checkpoint.json"
)


def _load_checkpoint(path: str, root_page_id: str, resume: bool) -> set[str]:
    if not resume or not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("root_page_id") != root_page_id:
            return set()
        processed = data.get("processed_page_ids") or []
        return set(processed)
    except Exception:
        return set()


def _save_checkpoint(path: str, root_page_id: str, processed: set[str]) -> None:
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    data = {
        "root_page_id": root_page_id,
        "processed_page_ids": sorted(processed),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _hash_content(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _ensure_schema(db) -> None:
    NotionDocument.__table__.create(db.bind, checkfirst=True)
    NotionChunk.__table__.create(db.bind, checkfirst=True)
    inspector = inspect(db.bind)
    columns = {column["name"] for column in inspector.get_columns("notion_documents")}
    if "page_id" not in columns:
        db.execute(text("ALTER TABLE notion_documents ADD COLUMN page_id varchar"))
    if "content_hash" not in columns:
        db.execute(text("ALTER TABLE notion_documents ADD COLUMN content_hash varchar(64)"))
    if "last_edited_time" not in columns:
        db.execute(text("ALTER TABLE notion_documents ADD COLUMN last_edited_time varchar"))

    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_notion_documents_page_id "
            "ON notion_documents (page_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notion_documents_content_hash "
            "ON notion_documents (content_hash)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notion_chunks_page_id "
            "ON notion_chunks (page_id)"
        )
    )
    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_notion_chunks_page_id_index "
            "ON notion_chunks (page_id, chunk_index)"
        )
    )


def _split_into_chunks(text: str) -> list[str]:
    max_chars = max(200, settings.NOTION_CHUNK_SIZE)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        if len(current) + len(paragraph) + 1 <= max_chars:
            current = f"{current}\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        if len(current) <= max_chars:
            chunks.append(current)
        else:
            for i in range(0, len(current), max_chars):
                chunks.append(current[i : i + max_chars])
    if not chunks:
        chunks = [text[:max_chars]]
    return chunks


def _delete_chunks(db, page_id: str | None, page_url: str | None) -> None:
    if page_id:
        db.query(NotionChunk).filter(NotionChunk.page_id == page_id).delete(
            synchronize_session=False
        )
        return
    if page_url:
        db.query(NotionChunk).filter(NotionChunk.page_url == page_url).delete(
            synchronize_session=False
        )


def _upsert_document(db, doc: dict) -> str:
    content = doc.get("content", "")
    content_hash = _hash_content(content)
    page_id = doc.get("page_id")
    page_url = doc.get("url")
    title = doc.get("title") or "Untitled"
    last_edited_time = doc.get("last_edited_time")

    existing = None
    if page_id:
        existing = (
            db.query(NotionDocument)
            .filter(NotionDocument.page_id == page_id)
            .first()
        )
    if existing is None and page_url:
        existing = (
            db.query(NotionDocument)
            .filter(NotionDocument.page_url == page_url)
            .first()
        )

    if existing:
        same_content = existing.content_hash == content_hash and existing.content_hash
        unchanged = (
            same_content
            and existing.title == title
            and existing.page_url == page_url
            and existing.last_edited_time == last_edited_time
        )
        if unchanged:
            return "unchanged"

        if not same_content:
            chunks = _split_into_chunks(content)
            _delete_chunks(db, page_id, page_url)
            for idx, chunk in enumerate(chunks, 1):
                db.add(
                    NotionChunk(
                        page_id=page_id,
                        page_url=page_url,
                        page_title=title,
                        chunk_index=idx,
                        content=chunk,
                        content_hash=_hash_content(chunk),
                        embedding=embed_document(chunk),
                    )
                )

        existing.page_id = page_id
        existing.page_url = page_url
        existing.title = title
        existing.content = content
        existing.content_hash = content_hash
        existing.last_edited_time = last_edited_time
        return "updated"

    chunks = _split_into_chunks(content)
    for idx, chunk in enumerate(chunks, 1):
        db.add(
            NotionChunk(
                page_id=page_id,
                page_url=page_url,
                page_title=title,
                chunk_index=idx,
                content=chunk,
                content_hash=_hash_content(chunk),
                embedding=embed_document(chunk),
            )
        )
    db.add(
        NotionDocument(
            page_id=page_id,
            page_url=page_url,
            title=title,
            content=content,
            content_hash=content_hash,
            last_edited_time=last_edited_time,
        )
    )
    return "inserted"


def upsert_documents(
    *,
    max_pages: int = 0,
    delay: float = 0.3,
    resume: bool = False,
    checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
) -> None:
    logger.info("=== Notion sync started ===")

    logger.info("Step 1/2: Fetching pages from Notion (page-tree)...")
    documents = fetch_notion_documents(max_pages=max_pages)
    total = len(documents)
    logger.info("Fetched %d documents from Notion.", total)

    logger.info("Step 2/2: Embedding & upserting to DB (diff-aware)...")
    db = SessionLocal()
    succeeded = 0
    failed = 0
    skipped = 0
    failed_titles: list[str] = []
    processed = 0
    commit_every = max(1, settings.NOTION_SYNC_COMMIT_EVERY)
    checkpoint_every = max(1, settings.NOTION_SYNC_COMMIT_EVERY)

    try:
        _ensure_schema(db)
        processed_page_ids = _load_checkpoint(
            checkpoint_path,
            settings.NOTION_ROOT_PAGE_ID,
            resume,
        )

        for i, doc in enumerate(documents, 1):
            title = doc.get("title") or "Untitled"
            page_id = doc.get("page_id")

            if resume and page_id in processed_page_ids:
                skipped += 1
                logger.info("[%d/%d] SKIP (checkpointed): %s", i, total, title)
                continue
            content = (doc.get("content") or "").strip()

            if not content:
                logger.warning("[%d/%d] SKIP (empty content): %s", i, total, title)
                skipped += 1
                processed += 1
                if processed % commit_every == 0:
                    db.commit()
                if page_id:
                    processed_page_ids.add(page_id)
                    if processed % checkpoint_every == 0:
                        _save_checkpoint(
                            checkpoint_path,
                            settings.NOTION_ROOT_PAGE_ID,
                            processed_page_ids,
                        )
                continue

            try:
                status = _upsert_document(db, doc)
                processed += 1
                if processed % commit_every == 0:
                    db.commit()
                if page_id:
                    processed_page_ids.add(page_id)
                    if processed % checkpoint_every == 0:
                        _save_checkpoint(
                            checkpoint_path,
                            settings.NOTION_ROOT_PAGE_ID,
                            processed_page_ids,
                        )

                if status == "unchanged":
                    skipped += 1
                    logger.info("[%d/%d] SKIP (unchanged): %s", i, total, title)
                else:
                    succeeded += 1
                    logger.info("[%d/%d] OK: %s", i, total, title)
            except OperationalError:
                db.rollback()
                db.close()
                db = SessionLocal()
                _ensure_schema(db)
                status = _upsert_document(db, doc)
                processed += 1
                db.commit()
                if page_id:
                    processed_page_ids.add(page_id)
                    if processed % checkpoint_every == 0:
                        _save_checkpoint(
                            checkpoint_path,
                            settings.NOTION_ROOT_PAGE_ID,
                            processed_page_ids,
                        )
                if status == "unchanged":
                    skipped += 1
                    logger.info("[%d/%d] SKIP (unchanged): %s", i, total, title)
                else:
                    succeeded += 1
                    logger.info("[%d/%d] OK: %s", i, total, title)
            except Exception as exc:
                db.rollback()
                failed += 1
                failed_titles.append(title)
                logger.error("[%d/%d] FAIL: %s -- %s", i, total, title, exc)

            if i < total and delay > 0:
                time.sleep(delay)

        db.commit()
        _save_checkpoint(
            checkpoint_path,
            settings.NOTION_ROOT_PAGE_ID,
            processed_page_ids,
        )
    finally:
        try:
            db.close()
        except Exception:
            pass

    logger.info("=== Notion sync completed ===")
    logger.info("  Success: %d", succeeded)
    logger.info("  Failed:  %d", failed)
    logger.info("  Skipped: %d", skipped)
    logger.info("  Total:   %d", total)

    if failed_titles:
        logger.warning("Failed pages:")
        for t in failed_titles:
            logger.warning("  - %s", t)

    if failed > 0:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Notion documents to PostgreSQL")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max pages to process (0 = unlimited, default: 0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay in seconds between embedding API calls (default: 0.3)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already processed pages)",
    )
    parser.add_argument(
        "--checkpoint-path",
        type=str,
        default=settings.NOTION_SYNC_CHECKPOINT_PATH or DEFAULT_CHECKPOINT_PATH,
        help="Checkpoint file path",
    )
    args = parser.parse_args()

    upsert_documents(
        max_pages=args.max_pages,
        delay=args.delay,
        resume=args.resume,
        checkpoint_path=args.checkpoint_path,
    )


if __name__ == "__main__":
    main()
