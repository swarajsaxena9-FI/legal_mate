import asyncio
import logging
import re
import httpx
from duckduckgo_search import DDGS
from app.config import MAX_URLS

logger = logging.getLogger(__name__)

_IK_SEARCH = "https://indiankanoon.org/search/"
_IK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_SOURCES = {
    "indiankanoon.org": "Indian Kanoon",
    "livelaw.in":       "LiveLaw",
    "barandbench.com":  "Bar & Bench",
    "sci.gov.in":       "Supreme Court of India",
    "judis.nic.in":     "JUDIS",
}

_CASE_URL_RE = re.compile(
    r"(indiankanoon\.org/doc/\d+"
    r"|livelaw\.in/(top-stories|high-court|supreme-court|news-updates|law-firms)/"
    r"|barandbench\.com/(news|stories)/"
    r"|sci\.gov\.in/supremecourt/"
    r"|judis\.nic\.in/)"
)


def _is_case_url(url: str) -> bool:
    return bool(_CASE_URL_RE.search(url))


def _detect_source(url: str) -> str:
    for domain, name in _SOURCES.items():
        if domain in url:
            return name
    return "Web"


def _ddg_search_sync(query: str, max_results: int = 5) -> list[dict]:
    """Synchronous DDG search — called via asyncio.to_thread."""
    try:
        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                url = item.get("href", "")
                if _is_case_url(url):
                    results.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "source": _detect_source(url),
                    })
        site_hint = query[query.rfind("site:"):query.rfind("site:") + 30] if "site:" in query else query[:40]
        logger.info(f"DDG [{site_hint}]: {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"DDG search failed for '{query[:60]}': {e}")
        return []


async def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    return await asyncio.to_thread(_ddg_search_sync, query, max_results)


async def _ik_direct_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Fallback: direct IK HTML scrape if DDG returns nothing."""
    try:
        resp = await client.get(
            _IK_SEARCH,
            params={"formInput": query, "pagenum": 0},
            headers=_IK_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        matches = re.findall(r'href="(/doc/\d+/)"', resp.text)
        results = [
            {"url": f"https://indiankanoon.org{m}", "title": "", "snippet": "", "source": "Indian Kanoon"}
            for m in dict.fromkeys(matches)
        ]
        logger.info(f"IK direct fallback: {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"IK direct search failed: {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[dict]:
    """Returns list of {url, title, snippet, source} dicts."""
    seen: set[str] = set()
    results: list[dict] = []
    primary = queries[0]

    # Parallel DDG search across all sources — free, no API key needed
    tasks = [
        _ddg_search(f"{primary} site:indiankanoon.org", max_results=5),
        _ddg_search(f"{queries[-1]} site:indiankanoon.org", max_results=4),
        _ddg_search(f"{primary} site:livelaw.in", max_results=3),
        _ddg_search(f"{primary} site:barandbench.com", max_results=2),
        _ddg_search(f"{primary} site:sci.gov.in", max_results=2),
    ]
    all_batches = await asyncio.gather(*tasks)

    for batch in all_batches:
        for item in batch:
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)

    # Fallback to IK direct scrape if DDG returned nothing
    if not results:
        logger.warning("DDG returned 0 results — falling back to IK direct search")
        async with httpx.AsyncClient() as client:
            fallback_batches = await asyncio.gather(
                *[_ik_direct_search(client, q) for q in queries]
            )
        for batch in fallback_batches:
            for item in batch:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    results.append(item)

    final = results[:MAX_URLS]
    source_counts = {}
    for r in final:
        s = r.get("source", "Web")
        source_counts[s] = source_counts.get(s, 0) + 1
    logger.info(f"Total: {len(final)} URLs — sources: {source_counts}")
    return final
