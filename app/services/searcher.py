import asyncio
import logging
import re
import httpx
from app.config import SERPER_API_KEY, MAX_URLS

logger = logging.getLogger(__name__)

_SERPER_ENDPOINT = "https://google.serper.dev/search"
_IK_SEARCH = "https://indiankanoon.org/search/"
_IK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_CASE_URL_RE = re.compile(
    r"(indiankanoon\.org/doc/\d+|main\.sci\.gov\.in/supremecourt/|livelaw\.in/(top-stories|high-court|supreme-court|news-updates)/|barandbench\.com/(news|stories)/)"
)


def _is_case_url(url: str) -> bool:
    return bool(_CASE_URL_RE.search(url))


async def _serper_search(
    client: httpx.AsyncClient,
    query: str,
    num: int = 5,
) -> list[dict]:
    try:
        resp = await client.post(
            _SERPER_ENDPOINT,
            json={"q": query, "num": num, "gl": "in", "hl": "en"},
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        items = resp.json().get("organic", [])
        results = []
        for item in items:
            url = item.get("link", "")
            if _is_case_url(url):
                results.append({
                    "url": url,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                })
        logger.info(f"Serper: {len(results)} case results for '{query[:60]}'")
        return results
    except Exception as e:
        logger.warning(f"Serper search failed: {e}")
        return []


async def _ik_direct_search(
    client: httpx.AsyncClient,
    query: str,
    court: str = "",
) -> list[dict]:
    formInput = f"{query} court:{court}" if court else query
    try:
        resp = await client.get(
            _IK_SEARCH,
            params={"formInput": formInput, "pagenum": 0},
            headers=_IK_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        results = [
            {"url": f"https://indiankanoon.org{m}", "title": "", "snippet": ""}
            for m in dict.fromkeys(matches)
        ]
        logger.info(f"IK direct ({court or 'general'}): {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"IK direct search failed: {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[dict]:
    """Returns list of {url, title, snippet} dicts."""
    seen: set[str] = set()
    results: list[dict] = []

    async with httpx.AsyncClient() as client:
        if SERPER_API_KEY:
            tasks = [_serper_search(client, f"{q} site:indiankanoon.org", num=5) for q in queries]
            tasks.append(_serper_search(client, f"{queries[0]} Indian court judgment", num=3))
            all_batches = await asyncio.gather(*tasks)
        else:
            courts = ["supremecourt", "delhi", "bombay", "allahabad", "madras"]
            tasks = [_ik_direct_search(client, queries[i % len(queries)], c) for i, c in enumerate(courts)]
            tasks.append(_ik_direct_search(client, queries[-1]))
            all_batches = await asyncio.gather(*tasks)

        for batch in all_batches:
            for item in batch:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    results.append(item)

    final = results[:MAX_URLS]
    logger.info(f"Total: {len(final)} unique case URLs")
    return final
