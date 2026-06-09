"""
Thin wrapper around the Groq API (free tier, no credit card needed).

Model: llama-3.3-70b-versatile. Free tier limits to be aware of:
  ~30 requests/min and ~6,000 tokens/min on the 70B model. That's why we keep
  prompts tight and analyze logs locally before sending.

Get a free key at https://console.groq.com/keys and put it in
.streamlit/secrets.toml as  GROQ_API_KEY = "gsk_..."  (or set the env var).
"""

import os
from groq import Groq

MODEL = "llama-3.3-70b-versatile"   # free-tier, GPT-4o-class quality
FALLBACK_MODEL = "llama-3.1-8b-instant"  # faster / higher rate limits if you hit caps


def get_client(api_key: str | None = None) -> Groq:
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("No Groq API key found. Add GROQ_API_KEY in secrets or env.")
    return Groq(api_key=key)


def stream_answer(client: Groq, system_prompt: str, user_content: str,
                  context: str = "", model: str = MODEL, temperature: float = 0.2):
    """Yield text chunks as they stream back from Groq."""
    user_msg = user_content
    if context:
        user_msg = f"{context}\n\n---\n\nUSER INPUT:\n{user_content}"

    stream = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=1500,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
