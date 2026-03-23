import logging
import time
from typing import List, Dict

from notion_client import APIResponseError, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Notion API rate limit: 3 requests/sec => 0.35s between requests is safe
_REQUEST_DELAY = 0.35
_MAX_RETRIES = 3


def _extract_plain_text(rich_text) -> str:
    return "".join([item.get("plain_text", "") for item in rich_text or []])


def _retry_notion_call(func, *args, **kwargs):
    """Notion API call with exponential backoff retry."""
    for attempt in range(_MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except APIResponseError as e:
            if e.status == 429 or e.status >= 500:
                wait = (2 ** attempt) + 1
                logger.warning(
                    "Notion API error %s (attempt %d/%d), retrying in %ds...",
                    e.status, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                raise
    # Final attempt without catching
    return func(*args, **kwargs)


def _fetch_all_pages(notion: Client, database_id: str) -> list:
    """Fetch all pages from a Notion database with pagination."""
    all_pages = []
    has_more = True
    next_cursor = None

    while has_more:
        time.sleep(_REQUEST_DELAY)
        query_kwargs = {"database_id": database_id}
        if next_cursor:
            query_kwargs["start_cursor"] = next_cursor

        response = _retry_notion_call(notion.databases.query, **query_kwargs)
        results = response.get("results", [])
        all_pages.extend(results)
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")
        logger.info("Fetched %d pages so far...", len(all_pages))

    return all_pages


def _fetch_all_blocks(notion: Client, block_id: str) -> list:
    """Fetch all child blocks with pagination."""
    all_blocks = []
    has_more = True
    next_cursor = None

    while has_more:
        time.sleep(_REQUEST_DELAY)
        list_kwargs = {"block_id": block_id}
        if next_cursor:
            list_kwargs["start_cursor"] = next_cursor

        response = _retry_notion_call(
            notion.blocks.children.list, **list_kwargs
        )
        results = response.get("results", [])
        all_blocks.extend(results)
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    return all_blocks


def fetch_notion_documents() -> List[Dict[str, str]]:
    """Fetch all documents from Notion with pagination, retry, and delay."""
    notion = Client(auth=settings.NOTION_API_KEY)
    pages = _fetch_all_pages(notion, settings.NOTION_DATABASE_ID)
    logger.info("Total pages found: %d", len(pages))

    documents: List[Dict[str, str]] = []
    for i, page in enumerate(pages, 1):
        title_property = next(
            (
                value
                for value in page.get("properties", {}).values()
                if value.get("type") == "title"
            ),
            None,
        )
        title = _extract_plain_text(
            title_property.get("title") if title_property else []
        )
        url = page.get("url")

        try:
            blocks = _fetch_all_blocks(notion, page["id"])
        except APIResponseError as e:
            logger.error(
                "[%d/%d] Failed to fetch blocks for '%s': %s",
                i, len(pages), title, e,
            )
            blocks = []

        content_parts = []
        for block in blocks:
            block_type = block.get("type")
            block_value = block.get(block_type, {})
            content_parts.append(_extract_plain_text(block_value.get("rich_text")))

        documents.append({
            "title": title or "Untitled",
            "url": url,
            "content": "\n".join([part for part in content_parts if part]),
        })
        logger.info("[%d/%d] Fetched: %s", i, len(pages), title or "Untitled")

    return documents
