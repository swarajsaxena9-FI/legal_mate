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

# Source sites searched in parallel
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
                    "source": _detect_source(url),
                })
        logger.info(f"Serper [{query[query.rfind('site:'):]}]: {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"Serper search failed for '{query[:60]}': {e}")
        return []


async def _ik_direct_search(
    client: httpx.AsyncClient,
    query: str,
) -> list[dict]:
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
        logger.info(f"IK direct: {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"IK direct search failed: {e}")
        return []


async def search_legal_urls(queries: list[str]) -> list[dict]:
    """Returns list of {url, title, snippet, source} dicts."""
    seen: set[str] = set()
    results: list[dict] = []
    primary = queries[0]

    async with httpx.AsyncClient() as client:
        if SERPER_API_KEY:
            # Search all sources in parallel using all queries
            tasks = [
                # Indian Kanoon — most queries
                _serper_search(client, f"{primary} site:indiankanoon.org", num=5),
                _serper_search(client, f"{queries[-1]} site:indiankanoon.org", num=4),
                # LiveLaw — good for recent HC/SC judgements
                _serper_search(client, f"{primary} site:livelaw.in", num=3),
                # Bar & Bench
                _serper_search(client, f"{primary} site:barandbench.com", num=2),
                # Supreme Court official
                _serper_search(client, f"{primary} site:sci.gov.in", num=2),
            ]
            all_batches = await asyncio.gather(*tasks)
        else:
            # Local fallback: direct IK scraping
            tasks = [_ik_direct_search(client, q) for q in queries]
            all_batches = await asyncio.gather(*tasks)

        # Merge — IK first, then other sources for diversity
        for batch in all_batches:
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
