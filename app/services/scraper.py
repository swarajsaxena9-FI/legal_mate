import asyncio
import logging
import re
import httpx
from app.config import JINA_API_KEY

logger = logging.getLogger(__name__)

_JINA_BASE = "https://r.jina.ai/"
_CONCURRENCY = 3
_TIMEOUT = 30.0
_MIN_CHARS = 500

_IK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://indiankanoon.org/",
}

_ERROR_SIGNALS = ["just a moment", "captcha", "403: forbidden", "access denied", "enable javascript"]


def _is_error_page(text: str) -> bool:
    low = text.lower()
    return any(signal in low for signal in _ERROR_SIGNALS)


def _extract_court_name(html: str) -> str:
    match = re.search(r'<div[^>]*class="[^"]*docsource[^"]*"[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()
    return ""


def _extract_ik_text(html: str) -> str:
    """Extract judgement text from Indian Kanoon HTML."""
    # Remove script/style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Extract text from judgement div if present
    match = re.search(r'<div[^>]*id=["\']judgments?["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if match:
        html = match.group(1)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def _scrape_indiankanoon(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
) -> dict | None:
    async with sem:
        try:
            resp = await client.get(url, headers=_IK_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            text = _extract_ik_text(resp.text)
            if len(text) >= _MIN_CHARS and not _is_error_page(text):
                court = _extract_court_name(resp.text)
                logger.info(f"IK direct scrape: {url} -> {len(text)} chars | court: {court}")
                return {"url": url, "text": text, "court": court}
            logger.warning(f"IK scrape too short or error page: {url} ({len(text)} chars)")
            return None
        except Exception as e:
            logger.warning(f"IK scrape failed for {url}: {e}")
            return None


async def _scrape_jina(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
) -> dict | None:
    headers = {"Accept": "text/plain"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    async with sem:
        try:
            resp = await client.get(
                _JINA_BASE + url,
                headers=headers,
                timeout=_TIMEOUT,
                follow_redirects=True,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            if len(text) >= _MIN_CHARS and not _is_error_page(text):
                logger.info(f"Jina scrape: {url} -> {len(text)} chars")
                return {"url": url, "text": text}
            logger.warning(f"Jina returned error/short page for {url}")
            return None
        except Exception as e:
            logger.warning(f"Jina scrape failed for {url}: {e}")
            return None


async def scrape_urls(urls: list[str]) -> list[dict]:
    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient() as client:
        tasks = []
        for url in urls:
            if "indiankanoon.org" in url:
                tasks.append(_scrape_indiankanoon(client, sem, url))
            else:
                tasks.append(_scrape_jina(client, sem, url))
        results = await asyncio.gather(*tasks)

    docs = [r for r in results if r is not None]
    logger.info(f"Successfully scraped {len(docs)}/{len(urls)} URLs")
    return docs
