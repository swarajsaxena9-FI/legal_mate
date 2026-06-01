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

_LEGAL_SITES = [
    "site:indiankanoon.org",
    "site:main.sci.gov.in",
    "site:livelaw.in",
    "site:barandbench.com",
]

_CASE_URL_PATTERNS = [
    r"indiankanoon\.org/doc/\d+",
    r"main\.sci\.gov\.in/supremecourt/",
    r"livelaw\.in/(top-stories|high-court|supreme-court|news-updates)/",
    r"barandbench\.com/(news|stories)/",
]


def _is_case_url(url: str) -> bool:
    return any(re.search(p, url) for p in _CASE_URL_PATTERNS)


# ── Serper (primary — works from any IP including Render) ──────────────────────

async def _serper_search(
    client: httpx.AsyncClient,
    query: str,
    num: int = 5,
) -> list[str]:
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = await client.post(
            _SERPER_ENDPOINT,
            json={"q": query, "num": num, "gl": "in", "hl": "en"},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        items = resp.json().get("organic", [])
        urls = [item["link"] for item in items if "link" in item]
        logger.info(f"Serper: {len(urls)} results for '{query[:60]}'")
        return urls
    except Exception as e:
        logger.warning(f"Serper search failed for '{query[:60]}': {e}")
        return []


# ── Indian Kanoon direct (fallback — works locally, blocked on Render) ─────────

async def _ik_direct_search(
    client: httpx.AsyncClient,
    query: str,
    court: str = "",
) -> list[str]:
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
        urls = list(dict.fromkeys(f"https://indiankanoon.org{m}" for m in matches))
        logger.info(f"IK direct ({court or 'general'}): {len(urls)} results")
        return urls
    except Exception as e:
        logger.warning(f"IK direct search failed: {e}")
        return []


# ── Main search function ────────────────────────────────────────────────────────

async def search_legal_urls(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []

    async with httpx.AsyncClient() as client:
        if SERPER_API_KEY:
            # Use Serper with IK site filter + general legal search
            serper_tasks = []
            for q in queries:
                serper_tasks.append(_serper_search(client, f"{q} site:indiankanoon.org", num=5))
            serper_tasks.append(_serper_search(client, f"{queries[0]} Indian court judgment", num=3))

            all_results = await asyncio.gather(*serper_tasks)
            for batch in all_results:
                for url in batch:
                    # Only keep actual case doc URLs, not search/index pages
                    if url not in seen and _is_case_url(url):
                        seen.add(url)
                        urls.append(url)
        else:
            # Fallback: direct IK scraping (local dev)
            courts = ["supremecourt", "delhi", "bombay", "allahabad", "madras"]
            tasks = []
            for i, court in enumerate(courts):
                q = queries[i % len(queries)]
                tasks.append(_ik_direct_search(client, q, court))
            tasks.append(_ik_direct_search(client, queries[-1]))

            all_results = await asyncio.gather(*tasks)
            for batch in all_results:
                for url in batch:
                    if url not in seen and _is_case_url(url):
                        seen.add(url)
                        urls.append(url)

    final = urls[:MAX_URLS]
    logger.info(f"Total: {len(final)} unique URLs found")
    return final
