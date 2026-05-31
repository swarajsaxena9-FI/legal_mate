import sys, os, json, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.extractor import extract_legal_query

SAMPLE = open(os.path.join(os.path.dirname(__file__), "sample_case.txt")).read()

def test_extract_legal_query_text():
    result = extract_legal_query(raw_text=SAMPLE)
    print("\nExtracted JSON:\n", json.dumps(result, indent=2))
    assert isinstance(result, dict), "Result must be a dict"
    for key in ("case_summary", "case_type", "statutes", "keywords", "search_queries"):
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["search_queries"], list), "search_queries must be a list"
    assert len(result["search_queries"]) == 3, f"Expected 3 search_queries, got {len(result['search_queries'])}"
    assert isinstance(result["statutes"], list)
    assert isinstance(result["keywords"], list)
    print("TEST GATE 2: PASS")
