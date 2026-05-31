import asyncio
import logging
import httpx
from app.config import MAX_URLS

logger = logging.getLogger(__name__)

_IK_SEARCH = "https://indiankanoon.org/search/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _parse_ik_links(html: str) -> list[str]:
    import re
    pattern = r'href="(/doc/\d+/)"'
    matches = re.findall(pattern, html)
    base = "https://indiankanoon.org"
    seen = set()
    urls = []
    for m in matches:
        url = base + m
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


async def _search_one(client: httpx.AsyncClient, query: str) -> list[str]:
    try:
        resp = await client.get(
            _IK_SEARCH,
            params={"formInput": query, "pagenum": 0},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return _parse_ik_links(resp.text)
    except Exception as e:
        logger.warning(f"IK search failed for '{query[:60]}': {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []

    async with httpx.AsyncClient() as client:
        tasks = [_search_one(client, q) for q in queries]
        results = await asyncio.gather(*tasks)
        for batch in results:
            for url in batch:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

    final = urls[:MAX_URLS]
    logger.info(f"Found {len(final)} URLs from Indian Kanoon search")
    return final
