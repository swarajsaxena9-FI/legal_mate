# ⚖️ AI Legal Case Similarity Search — POC

A semantic search engine for Indian court judgements. Upload a case draft (PDF or text) → system extracts legal issues → searches live Indian legal databases → finds semantically similar past judgements → returns structured citations with relevance scores.

---

## Architecture

```
User Input (PDF / Text)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Render)                    │
│                                                                 │
│  1. EXTRACTOR  ──── gemini-2.5-flash (JSON mode, no thinking)  │
│     └─ case_summary, case_type, statutes, keywords,            │
│        search_queries[3]                                        │
│                                                                 │
│  2. SEARCHER   ──── Indian Kanoon (direct HTML scrape)          │
│     └─ Queries SC + Delhi HC + Bombay HC + Allahabad HC +       │
│        Madras HC + Calcutta HC + Karnataka HC in parallel       │
│     └─ Returns up to 10 deduplicated case URLs                  │
│                                                                 │
│  3. SCRAPER    ──── Direct HTTP + Jina Reader fallback          │
│     └─ Indian Kanoon: direct httpx scrape (bypasses CAPTCHA)   │
│     └─ Other URLs: Jina AI Reader (r.jina.ai)                  │
│     └─ Concurrent (semaphore = 3), 30s timeout per URL         │
│                                                                 │
│  4. CHUNKER    ──── RecursiveCharacterTextSplitter              │
│     └─ chunk_size=512, overlap=64, capped at 20 chunks          │
│        (free-tier embedding quota: 100 req/min)                 │
│                                                                 │
│  5. EMBEDDER   ──── gemini-embedding-001 (batched)              │
│     └─ output_dimensionality=768, task_type=RETRIEVAL_DOCUMENT │
│     └─ Batch size=100, retry on 429 (62s backoff)              │
│                                                                 │
│  6. VECTOR STORE ── FAISS IndexFlatIP (cosine similarity)       │
│     └─ Ephemeral per-request, L2 normalized, top-k=5           │
│                                                                 │
│  7. VALIDATOR  ──── gemini-2.5-flash (JSON mode, no thinking)  │
│     └─ Rates genuine legal similarity 0.0–1.0                  │
│     └─ Returns: case_name, citation, relevance_score,          │
│        key_overlap, reasoning, source_url                       │
│                                                                 │
│  POST /search  ──── Returns SearchResponse (citations + meta)  │
│  GET  /health  ──── {"status": "ok"}                           │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│               Streamlit Frontend (Streamlit Cloud)              │
│                                                                 │
│  • PDF uploader + text area input                              │
│  • Similarity % slider (0–100%, default 30%)                   │
│  • Sort: Highest First / Lowest First                          │
│  • Top-N selector: 5 / 10 / 15 / 20 / All                     │
│  • Result cards: case name, citation, score bar,               │
│    legal overlap tags, reasoning, source link                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Backend | FastAPI + Uvicorn | async |
| LLM | `gemini-2.5-flash` via `google-genai` | thinking disabled for speed |
| Embeddings | `gemini-embedding-001` | batched, dim=768 |
| Search | Indian Kanoon direct scrape | SC + 7 High Courts |
| Scraper | Direct httpx + Jina AI Reader | IK direct, others via Jina |
| Vector Search | `faiss-cpu` + NumPy | in-memory `IndexFlatIP`, ephemeral |
| Chunking | `langchain-text-splitters` | chunk=512, overlap=64 |
| UI | Streamlit | |
| Backend Host | Render (free tier) | cold start ~40s after 15min idle |
| Frontend Host | Streamlit Community Cloud | |

---

## Pipeline Timings (approximate, free tier)

| Stage | Time |
|---|---|
| Extract (LLM) | ~2–3s |
| Search (7 courts parallel) | ~3–4s |
| Scrape (10 URLs concurrent) | ~5–6s |
| Embed (20 chunks batch) | ~4–5s |
| FAISS search | < 0.1s |
| Validate (LLM) | ~3–5s |
| **Total** | **~18–25s** |

---

## Known Limitations (Free Tier)

| Limitation | Detail | Workaround |
|---|---|---|
| Gemini embedding: 100 req/min | Each search uses ~21 req | Wait 60s between searches |
| Render cold start | First request after 15min idle takes ~40s | Retry once |
| Chunk cap at 20 | Limits context for FAISS | Upgrade to paid Gemini tier |
| Indian Kanoon only | No SCC Online / Manupatra | Acceptable for POC |
| No auth / no DB | In-memory, ephemeral | By design for POC |

---

## Local Setup

```bash
# Clone and install
git clone <repo-url>
cd legal-search-poc
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

# Configure secrets
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY

# Run backend
uvicorn app.main:app --reload --port 8000

# Run UI (separate terminal)
streamlit run streamlit_app.py
```

## Environment Variables

| Variable | Required | Where to get |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | https://aistudio.google.com/apikey |
| `GOOGLE_CSE_API_KEY` | Optional | Google Cloud Console (requires billing) |
| `GOOGLE_CSE_ID` | Optional | https://programmablesearchengine.google.com |
| `JINA_API_KEY` | Optional | https://jina.ai/reader (1M free tokens) |

---

## Project Structure

```
legal-search-poc/
├── app/
│   ├── main.py              # FastAPI app, /search + /health endpoints
│   ├── config.py            # env vars + constants
│   ├── models.py            # Pydantic schemas
│   └── services/
│       ├── gemini_client.py # shared client + retry-on-429
│       ├── extractor.py     # PDF/text → legal query (LLM #1)
│       ├── searcher.py      # Indian Kanoon multi-court search
│       ├── scraper.py       # direct HTTP + Jina fallback
│       ├── chunker.py       # RecursiveCharacterTextSplitter
│       ├── embedder.py      # gemini-embedding-001 batched
│       ├── vector_store.py  # FAISS cosine similarity
│       └── validator.py     # top-k → citations (LLM #2)
├── streamlit_app.py         # Streamlit UI
├── tests/
│   ├── sample_case.txt      # Section 138 NI Act test case
│   ├── test_extractor.py
│   ├── test_searcher.py
│   ├── test_scraper.py
│   └── test_pipeline.py
├── requirements.txt         # backend deps
├── requirements-streamlit.txt
├── render.yaml              # Render Blueprint
├── .env.example
└── .gitignore
```

---

## Deployment

### Backend → Render
```bash
# render.yaml is already configured
# Push to GitHub, then:
# render.com → New → Blueprint → select repo → add env vars → Deploy
```

### Frontend → Streamlit Cloud
```
share.streamlit.io → New app → select repo
Main file: streamlit_app.py
Requirements: requirements-streamlit.txt
Secrets: BACKEND_URL = "https://your-render-url.onrender.com"
```
