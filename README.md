# 🛠️ EPM Intelligent Support Assistant

An AI support tool for Oracle EPM / EPBCS / PBCS / FDMEE professionals — built
entirely on **free tools**.

| Capability | What it does |
|---|---|
| 🔍 **Diagnose error** | Paste a Process Details error → root cause + ordered fix steps |
| 📋 **Analyze log file** | Upload an FDMEE/ODI/Process Details log → parsed locally, then prioritized issues |
| 💬 **Ask EPM question** | Domain Q&A grounded in *your own* error notebooks |

## Free stack

- **Streamlit** — UI; deploy free on Streamlit Community Cloud
- **Groq API + LLaMA 3.3 70B** (`llama-3.3-70b-versatile`) — free tier, no credit card
- **Local RAG** over your notes — `sentence-transformers` (runs locally, no API cost)

> The Groq free tier caps tokens-per-minute, so log files are **parsed locally** and
> only a compact summary is sent to the model. Your reference materials never leave
> your machine except as small retrieved snippets.

## 1. Get a free Groq key
Sign in at <https://console.groq.com/keys>, create a key (starts with `gsk_`).

## 2. Run locally
```bash
pip install -r requirements.txt
# add your key:
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit it
streamlit run app.py
```
(First run downloads the ~80 MB embedding model once.)

## 3. Add your knowledge base
Drop `.txt .md .pdf .docx .csv .xlsx` files into `knowledge_base/`
(there's a sample `sample_error_notebook.md` to start). Then click
**Build / refresh index** in the sidebar. Answers will cite which snippets they used.

## 4. Deploy free (optional)
1. Push this folder to a **public GitHub repo** (the `.gitignore` keeps your key out).
2. Go to <https://share.streamlit.io> → New app → pick the repo → main file `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
4. Deploy. (On Cloud, bundle your KB files in the repo so they're indexed at startup.)

## Project layout
```
app.py            Streamlit UI (3 modes)
llm.py            Groq client + streaming
rag.py            local embeddings + retrieval over knowledge_base/
log_analyzer.py   FDMEE/ODI/Process Details log parser (no LLM)
prompts.py        EPM domain system prompts
knowledge_base/   <- your error notebooks & reference materials
```

## Notes / tuning
- Hitting rate limits? Switch to `llama-3.1-8b-instant` in the sidebar (higher caps).
- Bad retrieval? Lower `min_score` in `rag.py` or raise `k`.
- Add more log signatures in `log_analyzer.py` → `KNOWN_PATTERNS`.
- This is a support aid; always validate fixes against Oracle docs / your environment.
