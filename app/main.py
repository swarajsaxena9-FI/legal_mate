import time
import asyncio
import logging
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


@app.get("/")
async def root():
    return {
        "service": "Legal Case Similarity Search API",
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "search": "POST /search  (form: text or file)"
        }
    }


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

    # Read file bytes early so we can pass to extractor
    file_bytes, mime = None, None
    if file:
        file_bytes = await file.read()
        mime = file.content_type or "application/pdf"

    # Stage 1: Extract (runs in thread so it doesn't block event loop)
    t = time.time()
    try:
        loop = asyncio.get_event_loop()
        if file_bytes:
            extracted = await loop.run_in_executor(
                None, lambda: extract_legal_query(file_bytes=file_bytes, mime_type=mime)
            )
        else:
            extracted = await loop.run_in_executor(
                None, lambda: extract_legal_query(raw_text=text)
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
    timings["extract"] = round(time.time() - t, 2)

    # Stage 2: Search — returns list of {url, title, snippet}
    t = time.time()
    try:
        search_results = await search_legal_urls(extracted.get("search_queries", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    timings["search"] = round(time.time() - t, 2)

    if not search_results:
        return SearchResponse(
            extracted=extracted,
            results=[],
            meta=SearchMeta(n_urls=0, n_docs_scraped=0, n_chunks=0, timings=timings),
        )

    # Stage 3: Scrape (uses snippet fallback when direct scraping blocked)
    t = time.time()
    try:
        docs = await scrape_urls(search_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e}")
    timings["scrape"] = round(time.time() - t, 2)

    if not docs:
        return SearchResponse(
            extracted=extracted,
            results=[],
            meta=SearchMeta(n_urls=len(search_results), n_docs_scraped=0, n_chunks=0, timings=timings),
        )

    # Stage 4: Chunk
    chunks = chunk_documents(docs)
    timings["chunk"] = round(time.time() - t, 2)

    # Stage 5: Embed chunks + query (in executor to not block)
    t = time.time()
    try:
        loop = asyncio.get_event_loop()
        chunk_texts = [c["text"] for c in chunks]
        query_text = extracted.get("case_summary", text or "")

        chunk_vecs, query_vec = await asyncio.gather(
            loop.run_in_executor(None, lambda: embed_texts(chunk_texts, "RETRIEVAL_DOCUMENT")),
            loop.run_in_executor(None, lambda: embed_texts([query_text], "RETRIEVAL_QUERY")),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
    timings["embed"] = round(time.time() - t, 2)

    # Stage 6: FAISS
    t = time.time()
    top_chunks = top_k_matches(query_vec, chunk_vecs, chunks)
    timings["vector_search"] = round(time.time() - t, 2)

    # Stage 7: Validate
    t = time.time()
    try:
        loop = asyncio.get_event_loop()
        case_summary = extracted.get("case_summary", text or "")
        citations_raw = await loop.run_in_executor(
            None, lambda: validate_matches(case_summary, top_chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")
    timings["validate"] = round(time.time() - t, 2)
    timings["total"] = round(time.time() - total_start, 2)

    citations = [Citation(**c) for c in citations_raw]

    return SearchResponse(
        extracted=extracted,
        results=citations,
        meta=SearchMeta(
            n_urls=len(search_results),
            n_docs_scraped=len(docs),
            n_chunks=len(chunks),
            timings=timings,
        ),
    )
