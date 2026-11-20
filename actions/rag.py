"""Retrieval-augmented answers (RAG) for the chat.

Retrieval: Bloom's own ranking (`rank_events`) picks the events that best match the question,
the visitor's interests and any place they named. Generation: when OPENAI_API_KEY is set, an LLM
writes a short, friendly answer using ONLY those retrieved listings, so it can't invent events.
Without a key (or if the call fails) Bloom falls back to its built-in wording.
"""

from __future__ import annotations

import json
import os
import urllib.request

SYSTEM = (
    "You are Bloom, a warm assistant helping adults 60+ in Salem, Oregon find local events. "
    "Answer the visitor in 2-3 short, plain sentences, in {language}. Use ONLY the event listings provided; "
    "never invent events, dates, prices or places. If none of the listings fit, say so kindly and suggest "
    "browsing the Events tab. Mention at most three events by name with their day. No markdown, no lists."
)


def enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def context_for(events: list[dict]) -> str:
    lines = []
    for e in events[:8]:
        lines.append(" | ".join(str(x) for x in (
            e.get("title"), e.get("date"), e.get("time"), e.get("location"), e.get("cost") or "Free",
            (e.get("description") or "")[:220], f"source: {e.get('source_name') or e.get('source')}",
            f"{e['miles']:.1f} miles away" if e.get("miles") is not None else "",
        ) if x))
    return "\n".join(lines)


def answer(question: str, events: list[dict], lang: str = "en") -> str | None:
    """A grounded answer, or None (no key, no events, or the API is unavailable)."""
    if not enabled() or not events or not question.strip():
        return None
    body = {
        "model": os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini",
        "temperature": 0.2,
        "max_tokens": 180,
        "messages": [
            {"role": "system", "content": SYSTEM.format(language="Spanish" if lang == "es" else "English")},
            {"role": "user", "content": f"Event listings:\n{context_for(events)}\n\nVisitor's question: {question[:500]}"},
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", json.dumps(body).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            text = json.load(response)["choices"][0]["message"]["content"].strip()
        return text[:700] or None
    except Exception as error:  # rate limit, network, bad key: use the built-in wording instead
        print(f"rag: OpenAI unavailable ({type(error).__name__})", flush=True)
        return None
