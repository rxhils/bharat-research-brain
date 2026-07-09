"""Agent 4 — 5-Slide Scriptwriter.

Turns the selected story into EXACTLY 5 slides:
1 Hook · 2 What happened · 3 Why it happened · 4 Why it matters ·
5 Maven takeaway + disclaimer. Hard limits: title <= 7 words, body <= 18
words, one idea per slide, zero advisory language.
"""
from __future__ import annotations

import re

from . import config, state
from .step02_fact_check import banned_language

_STOP = {"a", "an", "the", "of", "to", "in", "on", "as", "at", "by", "for",
         "with", "amid", "after", "over", "into", "its", "his", "her"}


def _clip_words(text: str, limit: int) -> str:
    words = text.split()
    clipped = words[:limit]
    # never let a clipped line dangle on a stopword/preposition (e.g. "...Fund at a")
    while clipped and clipped[-1].lower().strip(",;:.-") in _STOP:
        clipped.pop()
    return " ".join(clipped).rstrip(",;:-")


def _title_from(headline: str, limit: int = config.TITLE_MAX_WORDS) -> str:
    """Compress a headline to <= limit words by dropping stopwords if needed."""
    clean = re.sub(r"^SIMULATION:\s*", "", headline).strip().rstrip(".")
    words = clean.split()
    if len(words) <= limit:
        return clean
    kept = [w for w in words if w.lower() not in _STOP]
    return _clip_words(" ".join(kept) if len(kept) >= 4 else clean, limit)


def _first_sentence(text: str) -> str:
    m = re.split(r"(?<=[.!?])\s+", text.strip())
    return (m[0] if m else text).strip()


def _clip_sentence(text: str, limit: int) -> str:
    """Clip to <= limit words on a CLAUSE boundary so a line never dangles
    mid-phrase (e.g. '...lowest levels since 30'). Splits only on real clause
    marks (comma+space, semicolon, colon, dash) so numbers like '23,882' and
    '2.1%' stay intact; falls back to word-clip when there is no clause break.
    """
    sent = _first_sentence(text)
    if len(sent.split()) <= limit:
        return sent.rstrip(" ,;:-—–")
    out = ""
    for clause in re.split(r"\s*[—–]\s*|,\s+|;\s+|:\s+", sent):
        clause = clause.strip()
        if not clause:
            continue
        cand = f"{out}, {clause}" if out else clause
        if len(cand.split()) > limit:
            break
        out = cand
    return (out or _clip_words(sent, limit)).rstrip(" ,;:-—–")


def _sanitize(text: str) -> str:
    """Strip advisory tokens defensively (source text is already fact-checked)."""
    out = text
    for tok in banned_language(text):
        out = re.sub(rf"\b{re.escape(tok)}\b", "", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()


def _hashtags(story: dict) -> list[str]:
    base = ["#IndianStockMarket", "#Nifty50", "#Sensex", "#StockMarketIndia",
            "#FinancialLiteracy", "#InvestingIndia", "#MarketNews",
            "#StockMarketEducation"]
    theme = {
        "Banking": ["#BankNifty", "#BankingStocks"],
        "IT & AI": ["#ITStocks", "#AIIndia"],
        "Auto": ["#AutoStocks", "#EVIndia"],
        "Energy": ["#EnergyStocks", "#OilAndGas"],
        "Pharma": ["#PharmaStocks", "#Healthcare"],
        "Policy & Macro": ["#RBI", "#IndianEconomy"],
        "IPO & Deals": ["#IPO", "#IPOIndia"],
        "Markets & Index": ["#ShareMarket", "#NSE"],
    }.get(story.get("sector_or_theme", ""), ["#ShareMarket", "#BSE"])
    return base + theme


def run(job_id: str) -> dict:
    sel = state.load_artifact(job_id, "story_selector") or {}
    story = sel.get("selected_story") or {}
    if not story:
        payload = {"slides": [], "caption": "", "hashtags": [],
                   "disclaimer": config.DISCLAIMER, "status": "blocked",
                   "note": "No verified story selected — nothing to script.",
                   "generated_at": config.now_ist().isoformat(timespec="seconds")}
        state.save_artifact(job_id, "slide_script", payload)
        return payload

    headline = _sanitize(story["headline"])
    summary = _sanitize(story["summary"])
    why = _sanitize(story.get("why_it_matters", ""))
    src = (story.get("sources") or [{}])[0]
    src_name = src.get("name", "source")
    theme = story.get("sector_or_theme", "Markets")
    # only lead with a number when it actually carries meaning (unit/₹/%)
    number = next((n.strip() for n in story.get("key_numbers", [])
                   if re.search(r"%|₹|rs|crore|cr|lakh|bn|billion|mn|million|bps",
                                n, re.IGNORECASE)), "")

    body = config.BODY_MAX_WORDS
    slides = [
        {"slide_number": 1, "role": "hook",
         "title": _title_from(headline),
         "body": _clip_words(_sanitize(
             f"{number} — here's what actually happened." if number
             else "Here's what actually happened — in 5 slides."), body),
         "visual_direction": "Bold hero slide: dark editorial gradient, oversized "
                             "headline, accent underline, slide counter.",
         "source_note": f"Source: {src_name}"},
        {"slide_number": 2, "role": "what_happened",
         "title": "What happened",
         "body": _clip_sentence(summary, body),
         "visual_direction": "Clean fact card: short statement, generous spacing, "
                             "subtle sector tag.",
         "source_note": f"Source: {src_name}"},
        {"slide_number": 3, "role": "why_it_happened",
         "title": "Why it happened",
         "body": _clip_words(_sanitize(
             f"{theme} moves like this are driven by flows, earnings and policy "
             "cues — not one villain."), body),
         "visual_direction": "Explainer card: accent bar left, calm typography.",
         "source_note": f"Context: {theme}"},
        {"slide_number": 4, "role": "why_it_matters",
         "title": "Why it matters",
         "body": _clip_words(why or "It shapes how the broader market reads risk "
                             "this week.", body),
         "visual_direction": "Impact card: slightly larger body, accent keyword.",
         "source_note": f"Source: {src_name}"},
        {"slide_number": 5, "role": "maven_takeaway",
         "title": "The Maven takeaway",
         "body": _clip_words("Read the move, understand the why — never chase a "
                             "headline.", body),
         "visual_direction": "Brand close: Maven mark, CTA to trymaven.in, "
                             "disclaimer strip at the bottom.",
         "source_note": config.DISCLAIMER},
    ]

    caption = (
        f"{headline}. \n\n"
        f"What happened, why, and why it matters — in 5 slides. \n\n"
        f"Understand the Indian market with Maven → {config.BRAND_SITE}\n\n"
        f"{config.DISCLAIMER} Not SEBI-registered. Do your own research.\n\n"
        f"Source: {src_name}"
        + (f" ({src.get('url')})" if src.get("url") else "")
    )

    payload = {
        "slides": slides,
        "caption": caption,
        "hashtags": _hashtags(story),
        "disclaimer": config.DISCLAIMER,
        "story_id": story.get("story_id"),
        "status": "scripted",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "slide_script", payload)
    return payload
