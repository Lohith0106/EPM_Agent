"""
Persistent history for the EPM Support Assistant.

Two backends, auto-selected:
  • Supabase (Postgres) — used when SUPABASE_URL and SUPABASE_KEY are set
    (e.g. on Streamlit Community Cloud, where the local disk is wiped on reboot).
  • Local JSONL file (history/history.jsonl) — used otherwise, for local runs.

Nothing leaves your machine on the local backend. On Supabase, rows go to your
own free project. The app pushes the secrets into env vars at startup (see app.py).
"""

import os
import json
import time

HIST_DIR = os.path.join(os.path.dirname(__file__), "history")
HIST_FILE = os.path.join(HIST_DIR, "history.jsonl")
KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")
TABLE = "epm_history"

_client = None
_tried = False


def _supabase():
    """Return a cached Supabase client, or None if not configured/available."""
    global _client, _tried
    if _tried:
        return _client
    _tried = True
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not (url and key):
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
    except Exception:
        _client = None
    return _client


def backend_name():
    return "Supabase (cloud)" if _supabase() else "local file"


# ------------------------------- save -------------------------------

def save(mode, user_input, answer, sources=None):
    if not answer.strip():
        return None
    rec = {
        "ts": time.time(),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "input": user_input,
        "answer": answer,
        "sources": sources or [],
    }
    sb = _supabase()
    if sb:
        try:
            sb.table(TABLE).insert(rec).execute()
            return rec["ts"]
        except Exception:
            pass  # fall through to local on any cloud error
    os.makedirs(HIST_DIR, exist_ok=True)
    with open(HIST_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["ts"]


# ------------------------------- load -------------------------------

def load(limit=None):
    """Return records newest-first."""
    sb = _supabase()
    if sb:
        try:
            q = sb.table(TABLE).select("*").order("ts", desc=True)
            if limit:
                q = q.limit(limit)
            return q.execute().data or []
        except Exception:
            pass
    if not os.path.exists(HIST_FILE):
        return []
    out = []
    with open(HIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    out.reverse()
    return out[:limit] if limit else out


def clear():
    sb = _supabase()
    if sb:
        try:
            sb.table(TABLE).delete().neq("ts", 0).execute()
            return
        except Exception:
            pass
    if os.path.exists(HIST_FILE):
        os.remove(HIST_FILE)


# --------------------------- export / promote ---------------------------

def export_markdown():
    recs = load()
    if not recs:
        return "# EPM Support Assistant — history\n\n_(empty)_\n"
    parts = ["# EPM Support Assistant — history\n"]
    for r in recs:
        parts.append(f"## {r.get('time','')} · {r.get('mode','')}\n")
        parts.append(f"**Input**\n\n```\n{str(r.get('input',''))[:2000]}\n```\n")
        parts.append(f"**Answer**\n\n{r.get('answer','')}\n")
        if r.get("sources"):
            parts.append(f"_Sources: {', '.join(r['sources'])}_\n")
        parts.append("\n---\n")
    return "\n".join(parts)


def save_to_kb(rec):
    """Promote one record into the knowledge base as a markdown file.
    Note: on Streamlit Cloud the KB folder is ephemeral; best used locally."""
    os.makedirs(KB_DIR, exist_ok=True)
    path = os.path.join(KB_DIR, f"resolved_{int(rec['ts'])}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Resolved: {rec.get('mode','')} ({rec.get('time','')})\n\n")
        f.write(f"## Problem / question\n{rec.get('input','')}\n\n")
        f.write(f"## Resolution\n{rec.get('answer','')}\n")
    return path
