# 🌐 Deploy to the web (free) — with persistent history

End result: a public URL like `https://epm-support.streamlit.app`, with history
that survives restarts (stored in a free Supabase database).

Total cost: $0. Two free accounts needed: GitHub and Supabase. ~20 minutes.

---

## PART A — Persistent history (Supabase)

Streamlit Cloud erases its disk on every reboot, so web history needs a database.
Supabase gives you a free Postgres. The app auto-detects it from two secrets and
falls back to a local file when they're absent — so your local runs are unchanged.

1. Go to <https://supabase.com> → **Start your project** → sign in with GitHub.
2. **New project**. Pick any name + a database password (you won't need the
   password again here). Choose the free plan. Wait ~2 min for it to provision.
3. In the left sidebar open **SQL Editor** → **New query**, paste this, click **Run**:
   ```sql
   create table if not exists epm_history (
     ts        double precision,
     time      text,
     mode      text,
     input     text,
     answer    text,
     sources   jsonb
   );
   alter table epm_history disable row level security;
   ```
   (RLS off is fine for a personal, allow-listed app — the key lives only in your
   private Streamlit secrets.)
4. Open **Project Settings → API** and copy two values:
   - **Project URL**  → this is `SUPABASE_URL`
   - **API key** → `anon` `public` key → this is `SUPABASE_KEY`

Keep those two strings handy for Part C, step 4.

---

## PART B — Put the code on GitHub

**Browser-only (no git install):**
1. <https://github.com> → log in → **New repository**.
2. Name `epm-support-assistant`, set **Private**, **Create repository**.
3. **Add file → Upload files**, drag in everything from the inner
   `epm-support-assistant` folder: `app.py, llm.py, rag.py, history.py,
   log_analyzer.py, prompts.py, requirements.txt, README.md, DEPLOY.md`, the
   `.streamlit/` folder (config.toml only), and `knowledge_base/` if you want your
   notes online. **Do NOT upload `secrets.toml`.**
4. **Commit changes.**

*(git CLI alt: `git init && git add . && git commit -m init && git branch -M main
&& git remote add origin <repo-url> && git push -u origin main`. The `.gitignore`
already excludes your key, the local history file, and the embeddings cache.)*

---

## PART C — Deploy on Streamlit Community Cloud

1. <https://share.streamlit.io> → **Sign in with GitHub** → Authorize.
2. **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `your-username/epm-support-assistant`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **Advanced settings → Secrets** and paste (using your real values):
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   SUPABASE_URL = "https://xxxxxxxx.supabase.co"
   SUPABASE_KEY = "your_anon_public_key"
   ```
5. **Deploy.** First build takes a few minutes. You'll get a `*.streamlit.app` URL.

Open the app → **History** tab → it should read **"Storage: Supabase (cloud)."**
That confirms persistence is live. Every diagnosis/question is now saved to your
Supabase table and survives reboots and redeploys.

---

## PART D — Lock it down (recommended)

App → **Settings → Sharing** → enable the **viewer allow-list** and add the emails
allowed to open the app. Without this, anyone with the link can use (and drain)
your Groq free-tier quota.

---

## Decisions / notes

- **Client data:** keep the repo **private**, or simply don't upload
  `knowledge_base/` and keep those notes local-only.
- **Who pays for the API:** keep `GROQ_API_KEY` in secrets = visitors use your
  quota (combine with the allow-list). Omit it = each visitor pastes their own key.
- **Heavy build / out of memory:** swap the repo's `requirements.txt` for the
  contents of `requirements-web.txt` (drops the local RAG stack; keeps Supabase
  history + Diagnose/Log/Q&A).
- **"Add to knowledge base" on web:** writes to the (ephemeral) cloud disk, so it's
  best used on local runs. History is the part that's now permanent on web.
- Update secrets anytime: App → **Settings → Secrets** → edit → it reboots itself.
