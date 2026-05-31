import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

BASE_URL = "http://127.0.0.1:8000"
SAMPLE = open(os.path.join(os.path.dirname(__file__), "sample_case.txt")).read()


def test_health():
    resp = httpx.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_search_text(timeout=300):
    resp = httpx.post(
        f"{BASE_URL}/search",
        data={"text": SAMPLE},
        timeout=timeout,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert "extracted" in body
    assert "results" in body
    assert "meta" in body
    assert len(body["results"]) >= 1, "Expected at least 1 citation result"
    for r in body["results"]:
        for key in ("case_name", "citation", "relevance_score", "key_overlap", "reasoning", "source_url"):
            assert key in r, f"Missing key in result: {key}"
        assert 0.0 <= r["relevance_score"] <= 1.0
    print(f"\nPipeline: {body['meta']['timings']['total']}s | {len(body['results'])} citations")
    print("TEST GATE 8 (pytest): PASS")
