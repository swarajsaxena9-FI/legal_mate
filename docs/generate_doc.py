"""Generate Legal Mate architecture PDF document."""
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(30, 90, 160)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "Legal Mate - Architecture & Tech Stack Document", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f"Page {self.page_no()} | Legal Mate POC - Confidential", align="C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(230, 240, 255)
        self.set_text_color(20, 60, 130)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 80, 160)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def code_block(self, text):
        self.set_font("Courier", "", 8)
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(200, 200, 200)
        self.multi_cell(0, 4.5, text, fill=True, border=1)
        self.set_font("Helvetica", "", 9)
        self.ln(2)

    def table_row(self, cols, widths, header=False):
        if header:
            self.set_font("Helvetica", "B", 8)
            self.set_fill_color(60, 100, 180)
            self.set_text_color(255, 255, 255)
        else:
            self.set_font("Helvetica", "", 8)
            self.set_fill_color(248, 250, 255)
            self.set_text_color(0, 0, 0)
        for col, w in zip(cols, widths):
            self.cell(w, 6, str(col), border=1, fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def note(self, text):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, f"Note: {text}")
        self.set_text_color(0, 0, 0)
        self.ln(1)


def build():
    pdf = PDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # ── COVER ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 130)
    pdf.ln(10)
    pdf.cell(0, 12, "Legal Mate", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "AI Legal Case Similarity Search", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Architecture, Tech Stack & Future Scope", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "POC Documentation | Prepared for internal review", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # ── 1. WHAT IS LEGAL MATE ────────────────────────────────────────────────
    pdf.chapter_title("1. What is Legal Mate?")
    pdf.body(
        "Legal Mate is an AI-powered semantic search engine for Indian court judgements. "
        "A lawyer uploads a case draft (PDF or plain text), and the system automatically:\n"
        "  1. Understands the legal issues in the case\n"
        "  2. Searches live Indian legal databases (Indian Kanoon, LiveLaw, Bar & Bench, SCI)\n"
        "  3. Finds the most semantically similar past judgements\n"
        "  4. Returns structured citations with relevance scores, legal reasoning, and source links\n\n"
        "Simple analogy: Think of it as a 'Google for your case' -- but instead of returning "
        "web pages, it returns similar court judgements with AI-generated similarity explanations."
    )

    # ── 2. SYSTEM ARCHITECTURE ───────────────────────────────────────────────
    pdf.chapter_title("2. System Architecture")
    pdf.body("Two-tier deployment: FastAPI backend (Render) + Streamlit frontend (Streamlit Cloud)")
    pdf.code_block(
        "USER (Browser)\n"
        "     |\n"
        "     | Upload PDF / Paste text\n"
        "     v\n"
        "STREAMLIT FRONTEND  (legalmate.streamlit.app)\n"
        "     |\n"
        "     | POST /search\n"
        "     v\n"
        "FASTAPI BACKEND  (legal-search-api.onrender.com)\n"
        "  |\n"
        "  |-- Step 1: EXTRACTOR  -> Gemini reads case, extracts statutes + queries\n"
        "  |-- Step 2: SEARCHER   -> Serper searches 4 legal sites in parallel\n"
        "  |-- Step 3: SCRAPER    -> Fetches full case text from URLs\n"
        "  |-- Step 4: CHUNKER    -> Splits docs into 512-char chunks\n"
        "  |-- Step 5: EMBEDDER   -> Converts chunks to 768-dim vectors\n"
        "  |-- Step 6: FAISS      -> Finds top-20 most similar chunks\n"
        "  |-- Step 7: VALIDATOR  -> Gemini rates legal similarity, returns citations\n"
        "     |\n"
        "     v\n"
        "JSON response -> Streamlit renders cards with similarity scores"
    )

    # ── 3. HOW SIMILAR CASES ARE RETRIEVED ──────────────────────────────────
    pdf.chapter_title("3. How Similar Cases Are Retrieved (7-Step Pipeline)")

    steps = [
        ("Step 1: EXTRACT", "gemini-2.5-flash",
         "Case text/PDF -> JSON with case_type, statutes, keywords, 3 search queries.\n"
         "Analogy: A trained lawyer reads your case and writes a research brief."),
        ("Step 2: SEARCH", "Serper.dev (Google Search API)",
         "3 search queries run on 4 sites in parallel:\n"
         "  - site:indiankanoon.org (main legal database)\n"
         "  - site:livelaw.in (recent HC/SC judgements)\n"
         "  - site:barandbench.com (legal news + judgements)\n"
         "  - site:sci.gov.in (Supreme Court official)\n"
         "Returns: up to 10 unique case URLs + titles + snippets"),
        ("Step 3: SCRAPE", "Direct HTTP + Serper snippets",
         "Fetches full case text from each URL.\n"
         "Fallback: Uses Google snippets when direct access is blocked (datacenter IPs)."),
        ("Step 4: CHUNK", "LangChain RecursiveCharacterTextSplitter",
         "Splits long judgements (50,000+ chars) into 512-char chunks with 64-char overlap.\n"
         "Analogy: Breaking a book into readable paragraphs. Max 20 chunks (free-tier quota)."),
        ("Step 5: EMBED", "gemini-embedding-001",
         "Converts all text chunks + user query into 768-dimensional float vectors.\n"
         "Analogy: Translating text into a language of numbers where similar meaning = similar numbers.\n"
         "Batched: All chunks in ONE API call (respects 100 req/min free-tier limit)."),
        ("Step 6: VECTOR SEARCH", "FAISS IndexFlatIP",
         "Cosine similarity search: query vector vs all chunk vectors.\n"
         "Returns top-20 most similar chunks in milliseconds.\n"
         "Analogy: GPS finding nearest locations -- but for legal meaning, not geography."),
        ("Step 7: VALIDATE", "gemini-2.5-flash",
         "LLM reads user case + top chunks, rates genuine legal similarity (0.0-1.0).\n"
         "Returns: case_name, citation, relevance_score, key_overlap, reasoning, source.\n"
         "Thinking disabled (thinking_budget=0) for speed -- saves 10-15s per call."),
    ]

    for title, tool, desc in steps:
        pdf.section_title(title + f"  [{tool}]")
        pdf.body(desc)

    # ── 4. TECH STACK ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("4. Tech Stack -- Current vs Alternatives vs Enterprise")

    headers = ["Component", "Current (POC)", "Why Chosen", "Enterprise Alternative"]
    widths  = [35, 38, 52, 55]
    pdf.table_row(headers, widths, header=True)

    rows = [
        ["LLM", "gemini-2.5-flash", "Free tier, PDF native, JSON mode", "GPT-4o / Claude 3.5 Sonnet"],
        ["Embeddings", "gemini-embedding-001", "Same API key, 768-dim, batched", "text-embedding-3-large (OpenAI)"],
        ["Vector DB", "FAISS (in-memory)", "No DB needed, fast, ephemeral", "Pinecone / Qdrant / pgvector"],
        ["Search", "Serper.dev", "2500 free/month, works on cloud", "IK API + SCC Online + Manupatra"],
        ["Scraper", "Direct HTTP + snippets", "Free, no setup needed", "Playwright + Firecrawl"],
        ["Chunker", "LangChain text splitter", "Battle-tested, easy config", "Semantic chunker"],
        ["Backend", "FastAPI + Uvicorn", "Async, auto-docs, fast", "FastAPI + Kubernetes"],
        ["Frontend", "Streamlit", "POC speed, 1-file UI", "React + Next.js"],
        ["Backend Host", "Render (free)", "GitHub auto-deploy, 0 cost", "AWS ECS / GCP Cloud Run"],
        ["Frontend Host", "Streamlit Cloud", "Free, shareable URL", "Vercel / AWS CloudFront"],
        ["Cache", "None", "POC, not needed yet", "Redis (embeddings + responses)"],
        ["Database", "None", "In-memory, ephemeral", "PostgreSQL (users, history)"],
        ["Auth", "None", "POC only", "OAuth2 + JWT + RBAC"],
    ]

    fill = True
    for row in rows:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, widths)
        fill = not fill

    # ── 5. SOURCES ───────────────────────────────────────────────────────────
    pdf.ln(4)
    pdf.chapter_title("5. Document Sources")

    pdf.body(
        "All 4 sources are searched simultaneously (parallel Serper queries), not sequentially. "
        "Results are merged and deduplicated before processing."
    )

    src_headers = ["Source", "URL", "What it covers", "Status"]
    src_widths  = [40, 55, 65, 20]
    pdf.table_row(src_headers, src_widths, header=True)

    sources = [
        ["Indian Kanoon", "indiankanoon.org", "SC, all HCs, Tribunals, 10cr+ cases", "Active"],
        ["LiveLaw", "livelaw.in", "Recent HC/SC judgements + legal news", "Active"],
        ["Bar & Bench", "barandbench.com", "HC/SC judgements + legal analysis", "Active"],
        ["Supreme Court", "sci.gov.in", "Official SC judgements", "Active"],
        ["SCC Online", "scconline.com", "Premium, best quality", "Future"],
        ["Manupatra", "manupatra.com", "Premium, comprehensive", "Future"],
        ["JUDIS", "judis.nic.in", "SC archive", "Future"],
    ]

    fill = True
    for row in sources:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, src_widths)
        fill = not fill

    # ── 6. PIPELINE TIMINGS ──────────────────────────────────────────────────
    pdf.ln(4)
    pdf.chapter_title("6. Pipeline Timings (Free Tier)")

    t_headers = ["Stage", "Time", "Bottleneck?", "How to Improve"]
    t_widths  = [40, 20, 25, 95]
    pdf.table_row(t_headers, t_widths, header=True)

    timings = [
        ["Extract (LLM)", "~2-3s", "No", "Already optimized (thinking disabled)"],
        ["Search (Serper)", "~1-2s", "No", "Parallel queries, fast"],
        ["Scrape (10 URLs)", "~4-6s", "Sometimes", "Increase concurrency (semaphore=5)"],
        ["Chunk + Embed", "~4-5s", "Yes (quota)", "Paid tier = no waiting; Redis cache"],
        ["FAISS search", "<0.1s", "No", "Already near-instant"],
        ["Validate (LLM)", "~3-5s", "Sometimes", "Stream response to show partial results"],
        ["TOTAL", "~15-20s", "--", "Target: <10s on paid tier with caching"],
    ]

    fill = True
    for row in timings:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, t_widths)
        fill = not fill

    # ── 7. KNOWN LIMITATIONS ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("7. Known Limitations (Free Tier)")

    lim_headers = ["Limitation", "Detail", "Workaround / Fix"]
    lim_widths  = [45, 70, 65]
    pdf.table_row(lim_headers, lim_widths, header=True)

    limits = [
        ["Embedding quota", "100 req/min free tier", "20-chunk cap; 62s retry; paid tier"],
        ["Render cold start", "40s first request after 15min idle", "Retry once; upgrade to paid"],
        ["Chunk cap (20)", "Less context for FAISS", "Paid Gemini = increase to 100+"],
        ["Serper 2500/month", "High usage may exhaust", "IK API as backup"],
        ["No auth/login", "Anyone with URL can use", "Add Google OAuth2"],
        ["No history", "Each search is independent", "PostgreSQL + user sessions"],
        ["LLM hallucination", "Case names may be inaccurate", "Add citation verification step"],
    ]

    fill = True
    for row in limits:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, lim_widths)
        fill = not fill

    # ── 8. FUTURE SCOPE & ENTERPRISE ROADMAP ─────────────────────────────────
    pdf.ln(4)
    pdf.chapter_title("8. Future Scope & Enterprise Roadmap")

    pdf.section_title("8.1 Open Source / Offline LLMs (Ollama Support)")
    pdf.body(
        "Current system uses Gemini (cloud API). For law firms with confidentiality requirements, "
        "client data should never leave the firm's servers. Solution: Ollama.\n\n"
        "Ollama is a tool that runs LLMs locally on any laptop or server -- completely free, "
        "completely offline. No API key, no data sent to Google/OpenAI."
    )
    pdf.code_block(
        "# Current (Gemini - cloud)\n"
        "client = genai.Client(api_key='AIza...')\n"
        "resp = client.models.generate_content(model='gemini-2.5-flash', ...)\n\n"
        "# Future (Ollama - local, free, offline)\n"
        "# pip install ollama\n"
        "import ollama\n"
        "resp = ollama.chat(model='llama3.2', messages=[{...}])\n\n"
        "# Recommended models for Ollama:\n"
        "# LLM:        llama3.2 / mistral / phi-4\n"
        "# Embeddings: nomic-embed-text / mxbai-embed-large"
    )

    pdf.table_row(["Feature", "Gemini (Cloud)", "Ollama (Local)"], [50, 65, 65], header=True)
    ollama_rows = [
        ["Cost", "Pay per request (~Rs 0.01/search)", "Free forever"],
        ["Privacy", "Data sent to Google servers", "100% local, no data leak"],
        ["Internet", "Required", "Not required after setup"],
        ["Speed", "Fast (Google infrastructure)", "Depends on your hardware"],
        ["Best for", "POC, startups, small teams", "Law firms, hospitals, courts"],
        ["Setup", "API key only", "GPU/good CPU server needed"],
    ]
    fill = True
    for row in ollama_rows:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, [50, 65, 65])
        fill = not fill

    pdf.ln(4)
    pdf.section_title("8.2 Enterprise Scale Architecture")
    pdf.code_block(
        "POC (Now)               MVP (3 months)          Enterprise (6+ months)\n"
        "--------------------    --------------------    -----------------------\n"
        "Streamlit UI         -> React + TypeScript   -> White-label product\n"
        "Single Render server -> Docker + CI/CD       -> Kubernetes auto-scale\n"
        "Gemini only          -> Multi-model support  -> Ollama option\n"
        "No DB                -> PostgreSQL           -> Multi-tenant DB\n"
        "No auth              -> Google OAuth2        -> SSO + RBAC\n"
        "No cache             -> Redis cache          -> Full caching layer\n"
        "IK + 3 sources       -> 10+ sources          -> SCC Online + Manupatra\n"
        "FAISS (memory)       -> Pinecone/Qdrant      -> Custom vector index\n"
        "Manual key mgmt      -> Secret Manager       -> HSM / Vault"
    )

    pdf.section_title("8.3 Additional Features for Enterprise")
    features = [
        "Multi-language support -- Hindi, Marathi, Tamil case documents",
        "Case timeline analysis -- see how law evolved over time on a statute",
        "Judge-specific search -- find all judgements by a specific judge",
        "Citation network -- which cases cite each other (graph visualization)",
        "Bulk case processing -- upload 100 cases at once, process overnight",
        "API access -- integrate into existing legal practice management software",
        "Mobile app -- React Native app for lawyers on the go",
        "Offline mode -- download case embeddings, search without internet",
        "Audit trail -- log every search for compliance and billing",
        "Custom fine-tuning -- fine-tune LLM on Indian legal corpus for better accuracy",
    ]
    for f in features:
        pdf.body(f"  - {f}")

    # ── 9. QUICK REFERENCE ────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("9. Quick Reference")

    pdf.section_title("Live URLs")
    pdf.body(
        "Frontend (Streamlit): https://legalmate-5yuktet3xgfjf2xcbc8y5l.streamlit.app\n"
        "Backend (Render):     https://legal-search-api-y9ca.onrender.com\n"
        "GitHub Repository:    https://github.com/swarajsaxena9-FI/legal_mate\n"
        "Health Check:         https://legal-search-api-y9ca.onrender.com/health"
    )

    pdf.section_title("Environment Variables Required")
    env_headers = ["Variable", "Required", "Where to Get"]
    env_widths  = [55, 25, 100]
    pdf.table_row(env_headers, env_widths, header=True)
    envs = [
        ["GEMINI_API_KEY", "Yes", "https://aistudio.google.com/apikey"],
        ["SERPER_API_KEY", "Yes (on cloud)", "https://serper.dev"],
        ["GOOGLE_CSE_API_KEY", "Optional", "Google Cloud Console"],
        ["GOOGLE_CSE_ID", "Optional", "https://programmablesearchengine.google.com"],
        ["JINA_API_KEY", "Optional", "https://jina.ai/reader"],
    ]
    fill = True
    for row in envs:
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.table_row(row, env_widths)
        fill = not fill

    pdf.ln(4)
    pdf.section_title("Local Setup Commands")
    pdf.code_block(
        "git clone https://github.com/swarajsaxena9-FI/legal_mate.git\n"
        "cd legal_mate\n"
        "python -m venv .venv\n"
        ".venv\\Scripts\\activate          # Windows\n"
        "pip install -r requirements.txt\n"
        "cp .env.example .env            # Fill in your API keys\n\n"
        "# Terminal 1 - Backend\n"
        "uvicorn app.main:app --reload --port 8000\n\n"
        "# Terminal 2 - Frontend\n"
        "streamlit run streamlit_app.py"
    )

    out_path = os.path.join(os.path.dirname(__file__), "LegalMate_Architecture.pdf")
    pdf.output(out_path)
    print(f"PDF saved: {out_path}")
    return out_path


if __name__ == "__main__":
    build()
