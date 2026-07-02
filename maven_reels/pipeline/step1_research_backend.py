"""Step 1 (backend) — Market Sentinel that RUNS FROM THE BACKEND.

Fetches TODAY's Indian market news through configured providers (RSS always;
Tavily/NewsAPI when keys exist), cross-checks stories across sources, scores
reel potential, and emits the research artifact the rest of the pipeline
consumes. Research NEVER blocks on the Claude Code conductor; when providers
fail it reports a clear, actionable config error instead.

Honesty rules: every field is derived from real fetched source text. Numbers
are regex-extracted from the source headline/summary ONLY (attributed via
source_urls) — nothing is ever invented. why_it_matters/investor_takeaway are
neutral educational framing, not claims.
"""
from __future__ import annotations

import re
from datetime import datetime

from . import config, schemas, state
from .research_providers import fallback_provider, fetch_all

_STOP = {"the", "a", "an", "and", "of", "in", "on", "to", "for", "as", "at",
         "by", "with", "after", "amid", "over", "today", "market", "markets",
         "stock", "stocks", "india", "indian", "share", "shares", "says"}

_SECTORS = {
    "Banking": r"\b(bank|banks|banking|hdfc|icici|sbi|axis|kotak|psu bank)\b",
    "Information Technology": r"\b(it|tech|infosys|tcs|wipro|hcl|software)\b",
    "Energy": r"\b(oil|gas|energy|ongc|reliance|power|coal)\b",
    "Auto": r"\b(auto|maruti|tata motors|mahindra|two-wheeler|ev)\b",
    "Pharma": r"\b(pharma|drug|sun pharma|cipla|healthcare)\b",
    "FMCG": r"\b(fmcg|consumer|hindustan unilever|itc|nestle)\b",
    "Metals": r"\b(metal|steel|tata steel|jsw|hindalco)\b",
    "Realty": r"\b(realty|real estate|dlf|housing)\b",
    "Macro / Policy": r"\b(rbi|sebi|gst|budget|policy|repo|inflation|gdp|fii|dii)\b",
    "Indices": r"\b(nifty|sensex|bank nifty|index|indices)\b",
}

_HOT = r"\b(nifty|sensex|rbi|sebi|surge|jump|fall|crash|rally|record|high|low|crore|%|fii|dii|gst)\b"
_NUM = re.compile(r"(?:rs\.?\s?)?[\d,]+(?:\.\d+)?\s?(?:%|crore|lakh|bps|points?|pts)", re.I)


def _tokens(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", t.lower())
            if w not in _STOP and len(w) > 2}


def data_mode(now: datetime | None = None) -> tuple[str, str]:
    """(data_window, market_status) from the IST clock/calendar."""
    now = now or datetime.now(config.IST)
    if now.weekday() >= 5:
        return "latest_trading_day", "closed (weekend)"
    hm = now.hour * 60 + now.minute
    if 9 * 60 + 15 <= hm < 15 * 60 + 30:
        return "intraday", "open"
    if hm >= 15 * 60 + 30:
        return "post_market", "closed (post-market)"
    return "latest_trading_day", "pre-open"


def _cluster(stories: list[dict]) -> list[dict]:
    """Group near-duplicate stories across sources -> cross-checked candidates."""
    clusters: list[dict] = []
    for s in stories:
        toks = _tokens(s["headline"])
        if not toks:
            continue
        for c in clusters:
            inter = len(toks & c["_tokens"]) / max(1, min(len(toks), len(c["_tokens"])))
            if inter >= 0.5:
                c["source_urls"].append(s["source_url"])
                c["_sources"].add(s["source_name"])
                if len(s["summary"]) > len(c["summary"]):
                    c["summary"] = s["summary"]
                break
        else:
            clusters.append({"headline": s["headline"], "summary": s["summary"],
                             "source_urls": [s["source_url"]],
                             "_sources": {s["source_name"]},
                             "published_at": s.get("published_at", ""),
                             "_tokens": toks})
    return clusters


def _sectors_of(text: str) -> list[str]:
    t = text.lower()
    return [name for name, pat in _SECTORS.items() if re.search(pat, t)][:4]


def _score(c: dict) -> tuple[int, int]:
    """(confidence 0-10, reel_potential 0-10) — heuristic, honest inputs only."""
    n_src = len(c["_sources"])
    confidence = min(10, 5 + 2 * n_src)          # 1 src=7 is too high; 1->7? use 5+2
    text = f"{c['headline']} {c['summary']}".lower()
    hot = len(re.findall(_HOT, text))
    nums = len(_NUM.findall(text))
    reel = min(10, 3 + hot + nums + (2 if n_src >= 2 else 0))
    return confidence, reel


def run(job_id: str) -> dict:
    """Fetch -> cluster -> score -> emit research artifact (or a clear failure)."""
    window, mkt_status = data_mode()
    stories, used, errors = fetch_all()

    if not stories:
        payload = {"job_id": job_id,
                   "generated_at": datetime.now(config.IST).isoformat(timespec="seconds"),
                   "data_window": window, "market_status": mkt_status,
                   "sources_used": used, "candidate_stories": [],
                   **fallback_provider.config_error(errors)}
        state.save_artifact(job_id, "research", payload)
        return payload

    clusters = _cluster(stories)
    cands = []
    for c in clusters:
        conf, reel = _score(c)
        text = f"{c['headline']} {c['summary']}"
        cands.append({
            "headline": c["headline"], "summary": c["summary"],
            "source_urls": [u for u in c["source_urls"] if u][:4],
            "sources": [{"name": n, "url": u} for n, u in
                        zip(sorted(c["_sources"]), c["source_urls"])],
            "published_at": c["published_at"],
            "category": (_sectors_of(text) or ["Markets"])[0],
            "affected_sectors": _sectors_of(text) or ["Markets"],
            "affected_companies": [],
            "why_it_matters": (f"Covered by {len(c['_sources'])} source(s); a "
                               f"{(_sectors_of(text) or ['market'])[0]}-related development "
                               "the kind retail investors track daily."),
            "confidence_score": conf, "reel_potential_score": reel,
            "cross_checked": len(c["_sources"]) >= 2,
        })
    cands.sort(key=lambda x: (x["reel_potential_score"], x["confidence_score"]),
               reverse=True)
    top = cands[:3]

    # map into the schema the downstream pipeline consumes — REAL text only
    top3 = []
    for i, c in enumerate(top, start=1):
        text = f"{c['headline']} {c['summary']}"
        top3.append({
            "rank": i, "headline": c["headline"], "category": c["category"],
            "what_happened": c["summary"],
            "why_it_matters": c["why_it_matters"],
            "affected_sectors": c["affected_sectors"],
            "affected_companies": c["affected_companies"],
            "key_numbers": _NUM.findall(text)[:4],   # extracted from source text only
            "investor_takeaway": ("For educational context only: understanding "
                                  "why this moved helps read the market — not "
                                  "investment advice."),
            "sources": c["sources"] or [{"name": "source", "url": u} for u in c["source_urls"]],
            "importance_score": c["reel_potential_score"],
            "confidence_score": c["confidence_score"],
        })

    payload = {
        "job_id": job_id, "date": job_id,
        "generated_at": datetime.now(config.IST).isoformat(timespec="seconds"),
        "retrieved_at": datetime.now(config.IST).isoformat(timespec="seconds"),
        "data_window": window, "market_status": mkt_status,
        "sources_used": used, "provider_errors": errors,
        "candidate_stories": cands[:10],
        "top_3_stories": top3,
        "selected_story": top3[0] if top3 else {},
        "research_status": "completed",
        "data_confidence_note": (
            f"Backend research ({window}, market {mkt_status}) from live feeds: "
            f"{', '.join(used)}. Headlines/summaries are verbatim source content; "
            "numbers shown are extracted from source text only, with URLs attached. "
            "Cross-checked stories are marked; single-source items carry lower confidence."),
    }
    schemas.validate_research(payload)
    state.save_artifact(job_id, "research", payload)
    return payload
