"""
EPM Intelligent Support Assistant
---------------------------------
An AI support tool for Oracle EPM / EPBCS / PBCS professionals, built entirely on
free tools:
  • Streamlit  (UI, free to deploy on Streamlit Community Cloud)
  • Groq API + LLaMA 3.3 70B  (free tier, no credit card)
  • Local RAG over your own error notebooks & reference materials (free, runs locally)

Run locally:   streamlit run app.py
"""

import os

import streamlit as st

import prompts
import rag
import llm
import history
from log_analyzer import analyze_log

st.set_page_config(page_title="EPM Intelligent Support Assistant",
                   page_icon="🛠️", layout="wide")

# ------- light styling -------
st.markdown("""
<style>
  .stApp { font-size: 0.95rem; }
  .kb-pill { display:inline-block; padding:2px 10px; border-radius:12px;
             font-size:0.78rem; font-weight:600; }
  .kb-on  { background:#10381f; color:#7CFFB0; }
  .kb-off { background:#3a2a10; color:#FFD27C; }
  .src    { font-size:0.78rem; color:#888; }
  div[data-testid="stExpander"] details { border-radius:8px; }
</style>
""", unsafe_allow_html=True)

st.title("🛠️ EPM Intelligent Support Assistant")
st.caption("Root-cause diagnosis, FDMEE log analysis, and EPM Q&A — grounded in your own notes.")

def _secret(key, default=""):
    """Read a Streamlit secret safely. st.secrets raises if no secrets.toml
    exists at all, so we swallow that and fall back to the default."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# Push optional Supabase secrets into env so history.py can pick the cloud backend.
for _k in ("SUPABASE_URL", "SUPABASE_KEY"):
    _v = _secret(_k, "")
    if _v:
        os.environ[_k] = _v


# ---------------- sidebar: key + knowledge base ----------------
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input(
        "Groq API key", type="password",
        value=_secret("GROQ_API_KEY", ""),
        help="Free key from console.groq.com/keys",
    )
    model = st.selectbox("Model",
                         [llm.MODEL, llm.FALLBACK_MODEL],
                         help="70B = best quality. 8B = faster / higher free-tier limits.")

    st.divider()
    st.subheader("Knowledge base")
    st.write("Drop `.txt .md .pdf .docx .csv .xlsx` files into the "
             "`knowledge_base/` folder, then rebuild.")
    if st.button("🔄 Build / refresh index", use_container_width=True):
        with st.spinner("Embedding your reference materials..."):
            n_chunks, n_files = rag.build_index(force=True)
        st.session_state["kb"] = (n_chunks, n_files)

    if "kb" not in st.session_state:
        try:
            st.session_state["kb"] = rag.build_index(force=False)
        except Exception as e:
            st.session_state["kb"] = (0, 0)
            st.warning(f"Index not ready: {e}")

    n_chunks, n_files = st.session_state.get("kb", (0, 0))
    if n_chunks:
        st.markdown(f"<span class='kb-pill kb-on'>● {n_files} files · "
                    f"{n_chunks} chunks indexed</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='kb-pill kb-off'>● no reference material yet "
                    "(works without it)</span>", unsafe_allow_html=True)


def _run(system_prompt, user_content, retrieval_query, mode, use_kb=True):
    """Shared run path: optionally retrieve KB context, stream the answer, save it."""
    if not api_key:
        st.error("Add your Groq API key in the sidebar first.")
        return
    context, hits = ("", [])
    if use_kb and n_chunks:
        context, hits = rag.context_block(retrieval_query, k=4)

    try:
        client = llm.get_client(api_key)
    except Exception as e:
        st.error(str(e)); return

    placeholder = st.empty()
    acc = ""
    try:
        for delta in llm.stream_answer(client, system_prompt, user_content,
                                       context=context, model=model):
            acc += delta
            placeholder.markdown(acc)
    except Exception as e:
        st.error(f"Groq request failed: {e}")
        return

    if hits:
        with st.expander(f"📎 Used {len(hits)} snippet(s) from your knowledge base"):
            for h in hits:
                st.markdown(f"<span class='src'>{h['source']} · relevance {h['score']}</span>",
                            unsafe_allow_html=True)
                st.text(h["text"][:600])

    # persist the interaction
    history.save(mode, user_content, acc, [h["source"] for h in hits])
    st.caption("✓ saved to History")


tab1, tab2, tab3, tab4 = st.tabs(
    ["🔍 Diagnose error", "📋 Analyze log file", "💬 Ask EPM question", "🕘 History"])

# ---- Mode 1: paste an error ----
with tab1:
    st.subheader("Paste a Process Details error")
    err = st.text_area("Error text", height=180,
                        placeholder="e.g. Error: No periods were identified for loading data into the application...")
    if st.button("Diagnose", type="primary", key="b1"):
        if err.strip():
            _run(prompts.ERROR_DIAGNOSIS, err, retrieval_query=err, mode="Diagnose error")
        else:
            st.info("Paste an error first.")

# ---- Mode 2: upload a log ----
with tab2:
    st.subheader("Upload an FDMEE / Data Management / ODI / Process Details log")
    up = st.file_uploader("Log file", type=["txt", "log", "out", "csv"])
    pasted = st.text_area("…or paste log text", height=140, key="logpaste")
    if st.button("Analyze log", type="primary", key="b2"):
        raw = ""
        if up is not None:
            raw = up.read().decode("utf-8", errors="ignore")
        elif pasted.strip():
            raw = pasted
        if not raw.strip():
            st.info("Upload or paste a log first.")
        else:
            summary_dict, summary_text = analyze_log(raw)
            with st.expander("🔎 Local parse (sent to the model instead of the raw log)"):
                st.text(summary_text)
            _run(prompts.LOG_ANALYSIS, summary_text,
                 retrieval_query=summary_text[:500], mode="Log analysis")

# ---- Mode 3: free Q&A ----
with tab3:
    st.subheader("Ask anything Oracle EPM")
    q = st.text_area("Your question", height=120,
                     placeholder="e.g. How do I create an auto-incrementing requisition number in Workforce using a sub var?")
    use_kb = st.checkbox("Use my knowledge base", value=True)
    if st.button("Answer", type="primary", key="b3"):
        if q.strip():
            _run(prompts.GENERAL_QA, q, retrieval_query=q, mode="EPM Q&A", use_kb=use_kb)
        else:
            st.info("Type a question first.")

# ---- History ----
with tab4:
    recs = history.load()
    top = st.columns([3, 1, 1])
    top[0].subheader(f"Saved interactions ({len(recs)})")
    top[0].caption(f"Storage: {history.backend_name()}")
    if recs:
        top[1].download_button("⬇ Export .md", data=history.export_markdown(),
                               file_name="epm_support_history.md", use_container_width=True)
        if top[2].button("🗑 Clear all", use_container_width=True):
            history.clear()
            st.rerun()

    if not recs:
        st.info("No history yet. Run a diagnosis or question and it'll be saved here.")
    else:
        for r in recs:
            snippet = r["input"].strip().replace("\n", " ")[:70]
            with st.expander(f"**{r['time']}** · {r['mode']} — {snippet}…"):
                st.markdown("**Input**")
                st.text(r["input"][:1500])
                st.markdown("**Answer**")
                st.markdown(r["answer"])
                if r.get("sources"):
                    st.caption("Sources: " + ", ".join(r["sources"]))
                if st.button("➕ Add this resolution to knowledge base",
                             key=f"kb_{r['ts']}"):
                    path = history.save_to_kb(r)
                    rag.build_index(force=True)
                    st.session_state["kb"] = rag.build_index(force=False)
                    st.success(f"Added to KB as {os.path.basename(path)} and re-indexed.")

st.divider()
st.caption("Free stack: Streamlit · Groq (LLaMA 3.3 70B) · local sentence-transformers RAG. "
           "Logs are parsed locally; only a compact summary is sent to the API.")
