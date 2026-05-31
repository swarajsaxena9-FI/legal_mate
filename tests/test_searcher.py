import sys, os, asyncio, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.searcher import search_legal_urls

QUERIES = [
    "Section 138 NI Act cheque bounce Mumbai Metropolitan Magistrate",
    "Dishonour of cheque legally enforceable debt legal notice served",
    "Liability under Section 138 NI Act funds insufficient",
]

def test_search_legal_urls():
    urls = asyncio.run(search_legal_urls(QUERIES))
    print(f"\nFound {len(urls)} URLs:")
    for u in urls:
        print(" ", u)
    assert 1 <= len(urls) <= 7, f"Expected 1-7 URLs, got {len(urls)}"
    for u in urls:
        assert u.startswith("http"), f"Invalid URL: {u}"
    print("TEST GATE 3: PASS")
