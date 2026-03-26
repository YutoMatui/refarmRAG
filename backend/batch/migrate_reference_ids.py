"""Backfill missing reference IDs in messages.references JSON.

Usage (PowerShell):
    .\\.venv\\Scripts\\python -m batch.migrate_reference_ids
    .\\.venv\\Scripts\\python -m batch.migrate_reference_ids --commit-every 200
"""

import argparse
import logging

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.message import Message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _normalize_references(references):
    if not isinstance(references, list):
        return references, False

    changed = False
    normalized = []
    for idx, ref in enumerate(references, 1):
        if not isinstance(ref, dict):
            normalized.append(ref)
            continue
        if "id" not in ref or ref.get("id") is None:
            new_ref = dict(ref)
            new_ref["id"] = idx
            normalized.append(new_ref)
            changed = True
        else:
            normalized.append(ref)
    return normalized, changed


def backfill_reference_ids(commit_every: int = 200) -> None:
    db = SessionLocal()
    updated = 0
    scanned = 0
    try:
        result = db.execute(select(Message))
        for message in result.scalars():
            scanned += 1
            normalized, changed = _normalize_references(message.references)
            if not changed:
                continue
            message.references = normalized
            updated += 1
            if updated % commit_every == 0:
                db.commit()
                logger.info("Committed %d updates...", updated)
        db.commit()
    finally:
        db.close()

    logger.info("Scan complete. Scanned=%d Updated=%d", scanned, updated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill reference IDs")
    parser.add_argument(
        "--commit-every",
        type=int,
        default=200,
        help="Commit after this many updates (default: 200)",
    )
    args = parser.parse_args()
    backfill_reference_ids(commit_every=max(1, args.commit_every))


if __name__ == "__main__":
    main()
