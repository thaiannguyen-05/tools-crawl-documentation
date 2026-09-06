from __future__ import annotations

import logging
import urllib.parse
from typing import TypedDict
import httpx
from bs4 import BeautifulSoup

try:
    from ..config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS
except (ImportError, ValueError):
    from config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class SearchCandidate(TypedDict):
    url: str
    title: str
    format: str
    source: str


import time

_ddg_cooldown_until: float = 0.0


def search_ddg_files(
    query: str,
    file_format: str,
    max_results: int = 10,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[SearchCandidate]:
    """Search DuckDuckGo HTML for documents matching query and file format.
    
    file_format can be: 'pdf', 'docx', 'doc', 'txt', 'md'.
    """
    global _ddg_cooldown_until
    if time.time() < _ddg_cooldown_until:
        logger.debug("DDG is in cooldown period (rate-limited), skipping query.")
        return []

    search_query = f"{query} filetype:{file_format}"
    endpoint = "https://html.duckduckgo.com/html/"

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    candidates: list[SearchCandidate] = []
    seen_urls: set[str] = set()

    try:
        data = {"q": search_query, "b": ""}
        response = httpx.post(
            endpoint,
            data=data,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

        if response.status_code in (202, 403, 429):
            _ddg_cooldown_until = time.time() + 45.0
            logger.warning(
                "DDG search rate limited (HTTP %d). Entering 45s cooldown for query '%s'",
                response.status_code,
                search_query,
            )
            return candidates

        if response.status_code != 200:
            logger.warning(
                "DDG search returned HTTP %d for query '%s'",
                response.status_code,
                search_query,
            )
            return candidates

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select(".result")

        for res in results:
            link_tag = res.select_one(".result__title a")
            if not link_tag:
                continue

            raw_href = link_tag.get("href", "")
            if not raw_href or "duckduckgo.com/y.js" in raw_href:
                continue

            # Extract actual destination from uddg parameter if present
            target_url = raw_href
            if "uddg=" in raw_href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                target_url = parsed.get("uddg", [raw_href])[0]

            if not target_url.startswith(("http://", "https://")):
                continue

            if target_url in seen_urls:
                continue
            seen_urls.add(target_url)

            title = link_tag.get_text(strip=True)
            candidates.append(
                {
                    "url": target_url,
                    "title": title,
                    "format": file_format.lower(),
                    "source": "duckduckgo",
                }
            )

            if len(candidates) >= max_results:
                break

    except Exception as e:
        logger.error("DDG search failed for '%s': %s", search_query, e)

    return candidates
