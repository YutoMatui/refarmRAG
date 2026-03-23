"""Notion -> PostgreSQL full sync with rate-limit handling.

Usage (PowerShell):
    .\\.venv\\Scripts\\python -m batch.sync_notion
    .\\.venv\\Scripts\\python -m batch.sync_notion --delay 0.5 --max-pages 10

Usage (bash / Railway):
    python -m batch.sync_notion
    python -m batch.sync_notion --delay 0.5 --max-pages 10
"""

import argparse
import logging
import sys
import time

from sqlalchemy.dialects.postgresql import insert

from app.db.database import SessionLocal
from app.models.notion_document import NotionDocument
from app.services.llm import embed_document
from app.services.notion import fetch_notion_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def upsert_documents(*, max_pages: int = 0, delay: float = 0.3) -> None:
    logger.info("=== Notion sync started ===")

    # ---- Step 1: Fetch all pages from Notion ----
    logger.info("Step 1/2: Fetching pages from Notion...")
    documents = fetch_notion_documents()
    total = len(documents)
    logger.info("Fetched %d documents from Notion.", total)

    if max_pages > 0:
        documents = documents[:max_pages]
        logger.info("--max-pages=%d: processing first %d documents.", max_pages, len(documents))

    # ---- Step 2: Embed & upsert one by one ----
    logger.info("Step 2/2: Embedding & upserting to DB...")
    db = SessionLocal()
    succeeded = 0
    failed = 0
    skipped = 0
    failed_titles: list[str] = []

    try:
        for i, doc in enumerate(documents, 1):
            title = doc["title"]

            # Skip documents with empty content
            if not doc["content"].strip():
                logger.warning("[%d/%d] SKIP (empty content): %s", i, total, title)
                skipped += 1
                continue

            try:
                embedding = embed_document(doc["content"])

                stmt = insert(NotionDocument).values(
                    page_url=doc["url"],
                    title=title,
                    content=doc["content"],
                    embedding=embedding,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["page_url"],
                    set_={
                        "title": title,
                        "content": doc["content"],
                        "embedding": embedding,
                    },
                )
                db.execute(stmt)
                db.commit()
                succeeded += 1
                logger.info("[%d/%d] OK: %s", i, total, title)
            except Exception as e:
                db.rollback()
                failed += 1
                failed_titles.append(title)
                logger.error("[%d/%d] FAIL: %s -- %s", i, total, title, e)

            # Delay between embedding requests
            if i < len(documents):
                time.sleep(delay)

    finally:
        db.close()

    # ---- Summary ----
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
    args = parser.parse_args()

    upsert_documents(max_pages=args.max_pages, delay=args.delay)


if __name__ == "__main__":
    main()
