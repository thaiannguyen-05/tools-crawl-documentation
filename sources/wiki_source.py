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
    """Search Vietnamese Wikipedia and fetch structured plain-text content (.txt) with pagination and batching."""
    search_endpoint = "https://vi.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
    }

    candidates: list[WikiCandidate] = []
    offset = 0

    while len(candidates) < max_results:
        fetch_limit = min(50, max_results - len(candidates))
        try:
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "utf8": 1,
                "srlimit": fetch_limit,
                "sroffset": offset,
            }
            res = httpx.get(search_endpoint, params=search_params, headers=headers, timeout=timeout)
            if res.status_code != 200:
                break

            items = res.json().get("query", {}).get("search", [])
            if not items:
                break

            # Batch extract plain-text content (up to 20 pageids per request for high speed)
            page_id_map = {str(item["pageid"]): item.get("title", "") for item in items if item.get("pageid")}
            page_ids = list(page_id_map.keys())

            for i in range(0, len(page_ids), 20):
                batch_ids = page_ids[i : i + 20]
                extract_params = {
                    "action": "query",
                    "prop": "extracts",
                    "explaintext": 1,
                    "pageids": "|".join(batch_ids),
                    "format": "json",
                    "utf8": 1,
                }
                try:
                    res_content = httpx.get(search_endpoint, params=extract_params, headers=headers, timeout=timeout)
                    if res_content.status_code == 200:
                        pages = res_content.json().get("query", {}).get("pages", {})
                        for pid, pdata in pages.items():
                            text_content = pdata.get("extract", "")
                            if len(text_content.strip()) > 120:
                                candidates.append(
                                    {
                                        "url": f"https://vi.wikipedia.org/?curid={pid}",
                                        "title": page_id_map.get(pid, pdata.get("title", f"wiki_{pid}")),
                                        "format": "txt",
                                        "source": "wikipedia_vi",
                                        "direct_content": text_content,
                                    }
                                )
                                if len(candidates) >= max_results:
                                    break
                except Exception as e:
                    logger.debug("Wikipedia batch extract error: %s", e)

                if len(candidates) >= max_results:
                    break

            offset += len(items)
            if len(items) < fetch_limit:
                break

        except Exception as e:
            logger.error("Wikipedia search failed for '%s': %s", query, e)
            break

    return candidates
