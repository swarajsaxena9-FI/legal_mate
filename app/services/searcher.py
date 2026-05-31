import asyncio
import logging
import re
import httpx
from app.config import MAX_URLS

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def _search_indiankanoon(client: httpx.AsyncClient, query: str) -> list[str]:
    try:
        resp = await client.get(
            "https://indiankanoon.org/search/",
            params={"formInput": query, "pagenum": 0},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        urls = list(dict.fromkeys(f"https://indiankanoon.org{m}" for m in matches))
        logger.info(f"IndianKanoon: {len(urls)} results for '{query[:50]}'")
        return urls
    except Exception as e:
        logger.warning(f"IndianKanoon search failed: {e}")
        return []


async def _search_livelaw(client: httpx.AsyncClient, query: str) -> list[str]:
    try:
        resp = await client.get(
            "https://www.livelaw.in/search",
            params={"q": query},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(
            r'href="(https://www\.livelaw\.in/(?:top-stories|high-court|supreme-court|news-updates)/[^"]+)"',
            resp.text,
        )
        urls = list(dict.fromkeys(matches))[:5]
        logger.info(f"LiveLaw: {len(urls)} results for '{query[:50]}'")
        return urls
    except Exception as e:
        logger.warning(f"LiveLaw search failed: {e}")
        return []


async def _search_sci(client: httpx.AsyncClient, query: str) -> list[str]:
    """Supreme Court of India judgements via Indian Kanoon filtered to SC."""
    try:
        resp = await client.get(
            "https://indiankanoon.org/search/",
            params={"formInput": f"{query} court:supremecourt", "pagenum": 0},
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        urls = list(dict.fromkeys(f"https://indiankanoon.org{m}" for m in matches))[:3]
        logger.info(f"SCI (via IK): {len(urls)} results for '{query[:50]}'")
        return urls
    except Exception as e:
        logger.warning(f"SCI search failed: {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []

    async with httpx.AsyncClient() as client:
        # Run all sources in parallel for the first query (most specific)
        primary = queries[0]
        ik_task = _search_indiankanoon(client, primary)
        ll_task = _search_livelaw(client, primary)
        sc_task = _search_sci(client, queries[-1])  # last query often most statute-specific

        ik_results, ll_results, sc_results = await asyncio.gather(ik_task, ll_task, sc_task)

        # Interleave: IK first, then SC, then LiveLaw for diversity
        for batch in [ik_results, sc_results, ll_results]:
            for url in batch:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

        # If still under MAX_URLS, run remaining queries on IK
        if len(urls) < MAX_URLS and len(queries) > 1:
            extra_tasks = [_search_indiankanoon(client, q) for q in queries[1:]]
            extra_results = await asyncio.gather(*extra_tasks)
            for batch in extra_results:
                for url in batch:
                    if url not in seen:
                        seen.add(url)
                        urls.append(url)

    final = urls[:MAX_URLS]
    logger.info(f"Total: {len(final)} unique URLs from all sources")
    return final
