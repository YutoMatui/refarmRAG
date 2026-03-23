from typing import List, Dict
from notion_client import Client

from app.core.config import settings


def _extract_plain_text(rich_text) -> str:
    return "".join([item.get("plain_text", "") for item in rich_text or []])


def fetch_notion_documents() -> List[Dict[str, str]]:
    notion = Client(auth=settings.NOTION_API_KEY)
    pages = notion.databases.query(database_id=settings.NOTION_DATABASE_ID)

    documents: List[Dict[str, str]] = []
    for page in pages.get("results", []):
        title_property = next(
            (
                value
                for value in page.get("properties", {}).values()
                if value.get("type") == "title"
            ),
            None,
        )
        title = _extract_plain_text(title_property.get("title") if title_property else [])
        url = page.get("url")

        # Basic fetch of page content. Tables or complex blocks should be expanded later.
        blocks = notion.blocks.children.list(block_id=page["id"]).get("results", [])
        content_parts = []
        for block in blocks:
            block_type = block.get("type")
            block_value = block.get(block_type, {})
            content_parts.append(_extract_plain_text(block_value.get("rich_text")))

        documents.append({
            "title": title or "Untitled",
            "url": url,
            "content": "\n".join([part for part in content_parts if part])
        })

    return documents
