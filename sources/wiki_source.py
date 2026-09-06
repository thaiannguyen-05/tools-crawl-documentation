from __future__ import annotations

import logging
from typing import TypedDict
import httpx

try:
    from ..config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS
except (ImportError, ValueError):
    from config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class WikiCandidate(TypedDict):
    url: str
    title: str
    format: str
    source: str
    direct_content: str | None


def search_wiki_articles(
    query: str,
    max_results: int = 5,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[WikiCandidate]:
    """Search Vietnamese Wikipedia and fetch structured plain-text content (.txt)."""
    search_endpoint = "https://vi.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
    }

    candidates: list[WikiCandidate] = []

    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": max_results,
        }
        res = httpx.get(search_endpoint, params=search_params, headers=headers, timeout=timeout)
        if res.status_code != 200:
            return candidates

        items = res.json().get("query", {}).get("search", [])
        for item in items:
            pageid = item.get("pageid")
            title = item.get("title")
            if not pageid or not title:
                continue

            # Fetch plain-text content (explaintext=1)
            extract_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "pageids": pageid,
                "format": "json",
                "utf8": 1,
            }
            res_content = httpx.get(search_endpoint, params=extract_params, headers=headers, timeout=timeout)
            if res_content.status_code == 200:
                pages = res_content.json().get("query", {}).get("pages", {})
                page_data = pages.get(str(pageid), {})
                text_content = page_data.get("extract", "")
                if len(text_content.strip()) > 100:
                    candidates.append(
                        {
                            "url": f"https://vi.wikipedia.org/?curid={pageid}",
                            "title": title,
                            "format": "txt",
                            "source": "wikipedia_vi",
                            "direct_content": text_content,
                        }
                    )

            if len(candidates) >= max_results:
                break

    except Exception as e:
        logger.error("Wikipedia search failed for '%s': %s", query, e)

    return candidates
