from __future__ import annotations

import logging
from typing import TypedDict
import httpx

try:
    from ..config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS
except (ImportError, ValueError):
    from config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class MarkdownCandidate(TypedDict):
    url: str
    title: str
    format: str
    source: str


def search_github_markdown(
    query: str,
    max_results: int = 5,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[MarkdownCandidate]:
    """Search GitHub public repositories for README and documentation in Markdown (.md)."""
    endpoint = "https://api.github.com/search/repositories"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }

    candidates: list[MarkdownCandidate] = []

    try:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(max_results * 2, 20),
        }
        response = httpx.get(endpoint, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            logger.warning("GitHub API returned status %d for query '%s'", response.status_code, query)
            return candidates

        data = response.json()
        items = data.get("items", [])

        for item in items:
            full_name = item.get("full_name")
            default_branch = item.get("default_branch", "main")
            description = item.get("description") or full_name

            raw_url = f"https://raw.githubusercontent.com/{full_name}/{default_branch}/README.md"
            candidates.append(
                {
                    "url": raw_url,
                    "title": f"GitHub - {full_name}: {description}",
                    "format": "md",
                    "source": "github",
                }
            )

            if len(candidates) >= max_results:
                break

    except Exception as e:
        logger.error("GitHub search error for '%s': %s", query, e)

    return candidates
