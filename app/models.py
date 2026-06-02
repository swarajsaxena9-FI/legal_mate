from pydantic import BaseModel
from typing import Any


class Citation(BaseModel):
    case_name: str | None
    citation: str | None
    relevance_score: float
    key_overlap: list[str]
    reasoning: str
    source_url: str
    source: str = "Indian Kanoon"


class SearchMeta(BaseModel):
    n_urls: int
    n_docs_scraped: int
    n_chunks: int
    timings: dict[str, float]


class SearchResponse(BaseModel):
    extracted: dict[str, Any]
    results: list[Citation]
    meta: SearchMeta
