import asyncio
import logging
import re
import httpx
from app.config import JINA_API_KEY

logger = logging.getLogger(__name__)

_JINA_BASE = "https://r.jina.ai/"
_CONCURRENCY = 3
_TIMEOUT = 30.0
_MIN_CHARS = 200

_IK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://indiankanoon.org/",
}

_ERROR_SIGNALS = ["just a moment", "captcha", "403: forbidden", "access denied", "enable javascript"]


def _is_error_page(text: str) -> bool:
    return any(s in text.lower() for s in _ERROR_SIGNALS)


def _extract_court_name(html: str) -> str:
    match = re.search(r'<div[^>]*class="[^"]*docsource[^"]*"[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()
    return ""


def _extract_ik_text(html: str) -> str:
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    match = re.search(r'<div[^>]*id=["\']judgments?["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if match:
        html = match.group(1)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def _try_direct(client: httpx.AsyncClient, url: str) -> str | None:
    """Try direct HTTP scrape — works on residential IPs."""
    try:
        resp = await client.get(url, headers=_IK_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        text = _extract_ik_text(resp.text)
        if len(text) >= _MIN_CHARS and not _is_error_page(text):
            return text
    except Exception:
        pass
    return None


async def _scrape_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    item: dict,
) -> dict | None:
    url = item["url"]
    title = item.get("title", "")
    snippet = item.get("snippet", "")

    async with sem:
        # 1. Try direct HTTP (works locally)
        if "indiankanoon.org" in url:
            text = await _try_direct(client, url)
            if text:
                logger.info(f"Direct scrape: {url} -> {len(text)} chars")
                return {"url": url, "text": text, "court": _extract_court_name("")}

        # 2. Use snippet as fallback (always available from Serper, no HTTP needed)
        if snippet and len(snippet) >= 50:
            combined = f"{title}\n\n{snippet}" if title else snippet
            logger.info(f"Using Serper snippet: {url} -> {len(combined)} chars")
            return {"url": url, "text": combined, "court": ""}

        logger.warning(f"No content available for {url}")
        return None


async def scrape_urls(items: list[dict] | list[str]) -> list[dict]:
    # Accept both old list[str] format and new list[dict] format
    if items and isinstance(items[0], str):
        items = [{"url": u, "title": "", "snippet": ""} for u in items]

    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient() as client:
        tasks = [_scrape_one(client, sem, item) for item in items]
        results = await asyncio.gather(*tasks)

    docs = [r for r in results if r is not None]
    logger.info(f"Scraped {len(docs)}/{len(items)} items")
    return docs
