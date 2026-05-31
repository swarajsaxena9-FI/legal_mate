import time
import logging
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import SearchResponse, Citation, SearchMeta
from app.services.extractor import extract_legal_query
from app.services.searcher import search_legal_urls
from app.services.scraper import scrape_urls
from app.services.chunker import chunk_documents
from app.services.embedder import embed_texts
from app.services.vector_store import top_k_matches
from app.services.validator import validate_matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Legal Case Similarity Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
):
    if not file and not text:
        raise HTTPException(status_code=400, detail="Provide either a file or text input.")

    timings: dict[str, float] = {}
    total_start = time.time()

    # Stage 1: Extract legal query
    t = time.time()
    try:
        if file:
            file_bytes = await file.read()
            mime = file.content_type or "application/pdf"
            extracted = extract_legal_query(file_bytes=file_bytes, mime_type=mime)
        else:
            extracted = extract_legal_query(raw_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
    timings["extract"] = round(time.time() - t, 2)

    # Stage 2: Search for relevant URLs
    t = time.time()
    try:
        urls = await search_legal_urls(extracted.get("search_queries", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    timings["search"] = round(time.time() - t, 2)

    if not urls:
        return SearchResponse(
            extracted=extracted,
            results=[],
            meta=SearchMeta(n_urls=0, n_docs_scraped=0, n_chunks=0, timings=timings),
        )

    # Stage 3: Scrape URLs
    t = time.time()
    try:
        docs = await scrape_urls(urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e}")
    timings["scrape"] = round(time.time() - t, 2)

    if not docs:
        return SearchResponse(
            extracted=extracted,
            results=[],
            meta=SearchMeta(n_urls=len(urls), n_docs_scraped=0, n_chunks=0, timings=timings),
        )

    # Stage 4: Chunk
    t = time.time()
    chunks = chunk_documents(docs)
    timings["chunk"] = round(time.time() - t, 2)

    # Stage 5: Embed chunks + query
    t = time.time()
    try:
        chunk_texts = [c["text"] for c in chunks]
        chunk_vecs = embed_texts(chunk_texts, task_type="RETRIEVAL_DOCUMENT")
        query_text = extracted.get("case_summary", text or "")
        query_vec = embed_texts([query_text], task_type="RETRIEVAL_QUERY")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
    timings["embed"] = round(time.time() - t, 2)

    # Stage 6: FAISS similarity search
    t = time.time()
    top_chunks = top_k_matches(query_vec, chunk_vecs, chunks)
    timings["vector_search"] = round(time.time() - t, 2)

    # Stage 7: LLM validation
    t = time.time()
    try:
        case_summary = extracted.get("case_summary", text or "")
        citations_raw = validate_matches(case_summary, top_chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")
    timings["validate"] = round(time.time() - t, 2)
    timings["total"] = round(time.time() - total_start, 2)

    citations = [Citation(**c) for c in citations_raw]

    return SearchResponse(
        extracted=extracted,
        results=citations,
        meta=SearchMeta(
            n_urls=len(urls),
            n_docs_scraped=len(docs),
            n_chunks=len(chunks),
            timings=timings,
        ),
    )
