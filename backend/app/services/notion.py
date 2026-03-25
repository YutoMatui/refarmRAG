import logging
import time
from collections import deque
from typing import Deque, Dict, List, Set, Tuple

import httpx
from notion_client import Client
from notion_client.errors import APIErrorCode, APIResponseError, RequestTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


def _extract_plain_text(rich_text) -> str:
    return "".join([item.get("plain_text", "") for item in rich_text or []])


def _retry_notion_call(func, *args, **kwargs):
    max_retries = settings.NOTION_SYNC_MAX_RETRIES
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except APIResponseError as exc:
            is_rate_limited = exc.status == 429 or exc.code == APIErrorCode.RateLimited
            is_retryable = is_rate_limited or exc.status >= 500
            if not is_retryable or attempt >= max_retries:
                raise
            retry_after = exc.headers.get("Retry-After") or exc.headers.get(
                "retry-after"
            )
            if retry_after:
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    wait_seconds = min(2**attempt, 60)
            else:
                wait_seconds = min(2**attempt, 60)
            logger.warning(
                "Notion API error %s (attempt %d/%d). Retrying in %.1fs...",
                exc.status,
                attempt + 1,
                max_retries,
                wait_seconds,
            )
            time.sleep(wait_seconds)
            attempt += 1
        except (RequestTimeoutError, httpx.HTTPError):
            if attempt >= max_retries:
                raise
            wait_seconds = min(2**attempt, 60)
            logger.warning(
                "Notion request failed (attempt %d/%d). Retrying in %.1fs...",
                attempt + 1,
                max_retries,
                wait_seconds,
            )
            time.sleep(wait_seconds)
            attempt += 1


def _call_with_delay(func, *args, **kwargs):
    result = _retry_notion_call(func, *args, **kwargs)
    if settings.NOTION_SYNC_DELAY_SECONDS > 0:
        time.sleep(settings.NOTION_SYNC_DELAY_SECONDS)
    return result


def _list_block_children(
    notion: Client, block_id: str, max_blocks: int | None = None
) -> List[Dict]:
    blocks: List[Dict] = []
    cursor = None
    while True:
        if cursor:
            response = _call_with_delay(
                notion.blocks.children.list, block_id=block_id, start_cursor=cursor
            )
        else:
            response = _call_with_delay(notion.blocks.children.list, block_id=block_id)
        results = response.get("results", [])
        if max_blocks is not None:
            remaining = max_blocks - len(blocks)
            if remaining <= 0:
                break
            blocks.extend(results[:remaining])
        else:
            blocks.extend(results)
        if not response.get("has_more"):
            break
        if max_blocks is not None and len(blocks) >= max_blocks:
            break
        cursor = response.get("next_cursor")
    return blocks


def _list_database_pages(notion: Client, database_id: str) -> List[Dict]:
    pages: List[Dict] = []
    cursor = None
    while True:
        if cursor:
            response = _call_with_delay(
                notion.databases.query, database_id=database_id, start_cursor=cursor
            )
        else:
            response = _call_with_delay(notion.databases.query, database_id=database_id)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def _get_page_title(page: Dict) -> str:
    for value in page.get("properties", {}).values():
        if value.get("type") == "title":
            title = _extract_plain_text(value.get("title"))
            if title:
                return title
    return "Untitled"


def _collect_block_text(
    notion: Client, block: Dict, budget: Dict[str, int] | None
) -> Tuple[List[str], List[str], List[str]]:
    text_parts: List[str] = []
    child_page_ids: List[str] = []
    child_database_ids: List[str] = []

    if budget is not None:
        if budget["remaining"] <= 0:
            return text_parts, child_page_ids, child_database_ids
        budget["remaining"] -= 1

    block_type = block.get("type")
    block_value = block.get(block_type, {})
    rich_text = block_value.get("rich_text")
    if rich_text:
        text = _extract_plain_text(rich_text)
        if text:
            text_parts.append(text)

    if block_type == "child_page":
        block_id = block.get("id")
        if block_id:
            child_page_ids.append(block_id)
    elif block_type == "child_database":
        block_id = block.get("id")
        if block_id:
            child_database_ids.append(block_id)

    if block.get("has_children"):
        remaining = budget["remaining"] if budget is not None else None
        for child in _list_block_children(notion, block["id"], max_blocks=remaining):
            child_text, child_pages, child_dbs = _collect_block_text(
                notion, child, budget
            )
            text_parts.extend(child_text)
            child_page_ids.extend(child_pages)
            child_database_ids.extend(child_dbs)

    return text_parts, child_page_ids, child_database_ids


def fetch_notion_documents(max_pages: int = 0) -> List[Dict[str, str]]:
    notion = Client(auth=settings.NOTION_API_KEY)
    queue: Deque[str] = deque([settings.NOTION_ROOT_PAGE_ID])
    visited_pages: Set[str] = set()
    documents: List[Dict[str, str]] = []
    max_pages_limit = max_pages if max_pages > 0 else None
    max_blocks_per_page = settings.NOTION_SYNC_MAX_BLOCKS_PER_PAGE or None

    while queue:
        if max_pages_limit is not None and len(documents) >= max_pages_limit:
            break

        page_id = queue.popleft()
        if page_id in visited_pages:
            continue
        visited_pages.add(page_id)

        page = _call_with_delay(notion.pages.retrieve, page_id=page_id)
        title = _get_page_title(page)
        url = page.get("url")
        last_edited_time = page.get("last_edited_time")

        content_parts: List[str] = []
        child_page_ids: List[str] = []
        child_database_ids: List[str] = []
        budget = (
            {"remaining": max_blocks_per_page} if max_blocks_per_page else None
        )

        for block in _list_block_children(
            notion, page_id, max_blocks=max_blocks_per_page
        ):
            block_text, block_pages, block_dbs = _collect_block_text(
                notion, block, budget
            )
            content_parts.extend(block_text)
            child_page_ids.extend(block_pages)
            child_database_ids.extend(block_dbs)

        for child_page_id in child_page_ids:
            if child_page_id not in visited_pages:
                queue.append(child_page_id)

        for child_database_id in child_database_ids:
            for db_page in _list_database_pages(notion, child_database_id):
                db_page_id = db_page.get("id")
                if db_page_id and db_page_id not in visited_pages:
                    queue.append(db_page_id)

        documents.append(
            {
                "page_id": page_id,
                "title": title or "Untitled",
                "url": url,
                "content": "\n".join([part for part in content_parts if part]),
                "last_edited_time": last_edited_time,
            }
        )
        logger.info("Fetched page: %s", title or "Untitled")

    logger.info("Total pages collected: %d", len(documents))
    return documents
