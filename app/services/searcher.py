import asyncio
import logging
import re
import httpx
from app.config import MAX_URLS

logger = logging.getLogger(__name__)

_IK_SEARCH = "https://indiankanoon.org/search/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Court filters — gives diversity across jurisdictions
_COURT_TIERS = [
    "supremecourt",   # Supreme Court of India
    "delhi",          # Delhi High Court
    "bombay",         # Bombay High Court
    "allahabad",      # Allahabad High Court
    "madras",         # Madras High Court
    "calcutta",       # Calcutta High Court
    "karnataka",      # Karnataka High Court
]

_COURT_LABELS = {
    "supremecourt": "Supreme Court of India",
    "delhi": "Delhi High Court",
    "bombay": "Bombay High Court",
    "allahabad": "Allahabad High Court",
    "madras": "Madras High Court",
    "calcutta": "Calcutta High Court",
    "karnataka": "Karnataka High Court",
}


async def _search_court(
    client: httpx.AsyncClient,
    query: str,
    court: str,
    max_results: int = 2,
) -> list[dict]:
    try:
        resp = await client.get(
            _IK_SEARCH,
            params={"formInput": f"{query} court:{court}", "pagenum": 0},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        base = "https://indiankanoon.org"
        urls = list(dict.fromkeys(f"{base}{m}" for m in matches))[:max_results]
        if urls:
            logger.info(f"{_COURT_LABELS[court]}: {len(urls)} result(s)")
        return [{"url": u, "court": _COURT_LABELS[court]} for u in urls]
    except Exception as e:
        logger.warning(f"Search failed for court:{court}: {e}")
        return []


async def _search_general(
    client: httpx.AsyncClient,
    query: str,
    max_results: int = 3,
) -> list[dict]:
    """Broad search without court filter as a catch-all."""
    try:
        resp = await client.get(
            _IK_SEARCH,
            params={"formInput": query, "pagenum": 0},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        base = "https://indiankanoon.org"
        urls = list(dict.fromkeys(f"{base}{m}" for m in matches))[:max_results]
        return [{"url": u, "court": "Indian Kanoon"} for u in urls]
    except Exception as e:
        logger.warning(f"General search failed: {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[str]:
    primary = queries[0] if queries else ""
    seen: set[str] = set()
    results: list[dict] = []

    async with httpx.AsyncClient() as client:
        # 2 results from SC + 2 from each major HC using different queries for diversity
        court_tasks = []
        for i, court in enumerate(_COURT_TIERS):
            q = queries[i % len(queries)]  # rotate queries across courts
            court_tasks.append(_search_court(client, q, court, max_results=2))
        # 3 broad results from last query as catch-all
        general_task = _search_general(client, queries[-1] if len(queries) > 1 else primary, max_results=3)

        all_results = await asyncio.gather(*court_tasks, general_task)

        # SC first, then HCs, then general
        for batch in all_results:
            for item in batch:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    results.append(item)

    final = results[:MAX_URLS]
    courts_found = list(dict.fromkeys(r["court"] for r in final))
    logger.info(f"Found {len(final)} URLs from: {', '.join(courts_found)}")
    return [r["url"] for r in final]
