import streamlit as st
import httpx

try:
    BACKEND_URL = st.secrets["BACKEND_URL"].rstrip("/")
except Exception:
    BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Legal Case Similarity Search",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ AI Legal Case Similarity Search")
st.caption("Upload a case draft or paste text — find similar Indian court judgements instantly.")

# ── Input ──────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])
with col1:
    uploaded_file = st.file_uploader("Upload case PDF", type=["pdf"])
with col2:
    case_text = st.text_area(
        "Or paste case text",
        height=200,
        placeholder="Paste your case facts, FIR details, or draft complaint here...",
    )

search_btn = st.button("🔍 Find Similar Cases", type="primary", use_container_width=True)

# ── Search ─────────────────────────────────────────────────────────────────────
if search_btn:
    if not uploaded_file and not case_text.strip():
        st.error("Please upload a PDF or paste case text before searching.")
        st.stop()

    with st.spinner("Searching Indian legal databases... (15-30 seconds)"):
        try:
            if uploaded_file:
                files = {"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
                resp = httpx.post(f"{BACKEND_URL}/search", files=files, timeout=180.0)
            else:
                resp = httpx.post(f"{BACKEND_URL}/search", data={"text": case_text}, timeout=180.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            st.error("Request timed out. Backend may be cold-starting (Render free tier). Please retry in 30 seconds.")
            st.stop()
        except Exception as e:
            st.error(f"Error contacting backend: {e}")
            st.stop()

    st.session_state["results"] = data.get("results", [])
    st.session_state["extracted"] = data.get("extracted", {})
    st.session_state["meta"] = data.get("meta", {})

# ── Display ────────────────────────────────────────────────────────────────────
if "results" in st.session_state and st.session_state["results"] is not None:
    extracted = st.session_state["extracted"]
    all_results = st.session_state["results"]
    meta = st.session_state["meta"]

    # Case summary
    with st.expander("📋 Extracted Case Analysis", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Case Type:** `{extracted.get('case_type', 'N/A')}`")
            st.markdown(f"**Summary:** {extracted.get('case_summary', '')}")
        with c2:
            statutes = extracted.get("statutes", [])
            if statutes:
                st.markdown("**Statutes:** " + " · ".join(f"`{s}`" for s in statutes))
            keywords = extracted.get("keywords", [])
            if keywords:
                st.markdown("**Keywords:** " + " · ".join(f"`{k}`" for k in keywords))

    timings = meta.get("timings", {})
    st.caption(
        f"Searched {meta.get('n_urls', 0)} URLs · "
        f"Scraped {meta.get('n_docs_scraped', 0)} docs · "
        f"{meta.get('n_chunks', 0)} chunks · "
        f"⏱ {timings.get('total', '?')}s total"
    )

    st.divider()

    if not all_results:
        st.warning("No similar cases found. Try adding more specific legal details.")
        st.stop()

    # ── Filter & Sort Controls ──────────────────────────────────────────────────
    st.subheader("🎛️ Filter & Sort Results")

    ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])

    with ctrl1:
        min_score = st.slider(
            "Minimum Similarity %",
            min_value=0,
            max_value=100,
            value=30,
            step=5,
            help="Only show cases with similarity at or above this threshold",
        )

    with ctrl2:
        sort_order = st.selectbox(
            "Sort by Similarity",
            options=["Highest First", "Lowest First"],
        )

    with ctrl3:
        max_display = st.selectbox(
            "Show top N results",
            options=[5, 10, 15, 20, "All"],
            index=0,
        )

    # Apply filter
    filtered = [r for r in all_results if r.get("relevance_score", 0) * 100 >= min_score]

    # Apply sort
    reverse = sort_order == "Highest First"
    filtered = sorted(filtered, key=lambda x: x.get("relevance_score", 0), reverse=reverse)

    # Apply limit
    if max_display != "All":
        filtered = filtered[:int(max_display)]

    # Stats bar
    total_count = len(all_results)
    filtered_count = len(filtered)
    score_range = ""
    if filtered:
        hi = max(r["relevance_score"] for r in filtered) * 100
        lo = min(r["relevance_score"] for r in filtered) * 100
        score_range = f" · Range: {lo:.0f}%–{hi:.0f}%"

    st.info(
        f"Showing **{filtered_count}** of **{total_count}** cases "
        f"(≥ {min_score}% similarity){score_range}"
    )

    st.divider()

    if not filtered:
        st.warning(f"No cases match the {min_score}% similarity threshold. Try lowering it.")
        st.stop()

    # ── Result Cards ────────────────────────────────────────────────────────────
    for i, r in enumerate(filtered):
        score = r.get("relevance_score", 0)
        score_pct = score * 100
        case_name = r.get("case_name") or "Unknown Case"
        citation = r.get("citation")
        reasoning = r.get("reasoning", "")
        overlaps = r.get("key_overlap", [])
        source_url = r.get("source_url", "")

        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(f"### {i+1}. {case_name}")
            if citation:
                st.markdown(f"**Citation:** `{citation}`")
        with col_b:
            color = "🟢" if score_pct >= 70 else "🟡" if score_pct >= 40 else "🔴"
            st.metric(label="Similarity", value=f"{color} {score_pct:.0f}%")
            st.progress(score)

        if overlaps:
            st.markdown("**Legal Overlap:** " + "  ".join(f"`{o}`" for o in overlaps))
        if reasoning:
            st.info(f"💡 {reasoning}")
        if source_url:
            st.markdown(f"[🔗 View Source Judgement]({source_url})")

        st.divider()
