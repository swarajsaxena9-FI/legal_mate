import sys, os, asyncio, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.scraper import scrape_urls

URLS = [
    "https://indiankanoon.org/doc/100995424/",
    "https://indiankanoon.org/doc/4753698/",
    "https://indiankanoon.org/doc/97452657/",
]

def test_scrape_urls():
    docs = asyncio.run(scrape_urls(URLS))
    print(f"\nScraped {len(docs)}/{len(URLS)} URLs successfully")
    assert len(docs) >= 1, f"Expected at least 1 successful scrape, got 0"
    for doc in docs:
        assert "url" in doc and "text" in doc
        assert len(doc["text"]) > 200, f"Text too short: {len(doc['text'])} chars"
    first = docs[0]
    print(f"URL: {first['url']}")
    print(f"First 300 chars:\n{first['text'][:300]}")
    print("TEST GATE 4: PASS")
