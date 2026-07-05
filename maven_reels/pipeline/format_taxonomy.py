"""Maven Reels — Viral Format Taxonomy (Indian finance). Local, free, canonical.

Six formats a market event can become. This is the "format brain" the whole
Newsroom now selects from BEFORE hooks/scripts/prompts are written. Each format
is educational-first (SEBI-safe): explanation, not tips. No "buy/sell", no
guaranteed returns, no unregistered-advice framing.

These are PRINCIPLES, not copies of any creator. The Story+Format Selector maps
a story to one format; the Format Director turns the format into an exact Reel
structure; the Template Library gives it a proven beat sheet.
"""
from __future__ import annotations

# canonical id -> definition
FORMATS = {
    "hidden_mechanism": {
        "id": "hidden_mechanism",
        "name": "Hidden Mechanism",
        "when_to_use": "The headline index moved because of something underneath it.",
        "example_hook": "The index hid the real story.",
        "first_frame_promise": "There's a reason under the number — I'll show you.",
        "best_for": ["Bank Nifty moving Nifty", "sector rotation", "FII/DII flows",
                     "rate-sensitive sectors", "index-weight effects"],
        "save_reason": "Teaches how to read what's under an index move — a reusable mental model.",
        "share_reason": "Feels like insider clarity: 'most people only saw the index'.",
        "teaching_anchor": "The index is the result, not the reason.",
        "compliance_note": "Explain the mechanism only. Never imply a trade.",
    },
    "one_sector": {
        "id": "one_sector",
        "name": "One Sector Changed Everything",
        "when_to_use": "One sector explains the broader market's mood today.",
        "example_hook": "One sector changed the mood.",
        "first_frame_promise": "One sector did the heavy lifting — here's which.",
        "best_for": ["banks", "IT", "energy", "auto", "defence", "pharma", "metals"],
        "save_reason": "Shows sector weight matters more than the index headline.",
        "share_reason": "Simple, surprising cause → easy to send to a friend who invests.",
        "teaching_anchor": "Sector weight can move the whole market.",
        "compliance_note": "Describe the sector move factually, sourced. No sector 'call'.",
    },
    "policy_signal": {
        "id": "policy_signal",
        "name": "Policy Signal",
        "when_to_use": "RBI, SEBI, budget, tax or regulation is the driver.",
        "example_hook": "One policy signal moved stocks.",
        "first_frame_promise": "A single official signal rippled into the market.",
        "best_for": ["RBI rate/policy", "SEBI rule", "Budget", "tax change",
                     "regulation", "government reform"],
        "save_reason": "Connects a policy to the sectors it actually touches.",
        "share_reason": "Explains news everyone saw but few understood.",
        "teaching_anchor": "Policy affects different sectors differently.",
        "compliance_note": "Attribute the policy to its official source + date. No forecast as fact.",
    },
    "retail_mistake": {
        "id": "retail_mistake",
        "name": "Retail Investor Mistake",
        "when_to_use": "There's a common way retail investors misread this move — a teaching angle.",
        "example_hook": "Most investors read this wrong.",
        "first_frame_promise": "Here's the mistake most people are making right now.",
        "best_for": ["misread earnings", "chasing a spike", "ignoring sector weight",
                     "confusing price with value", "reacting to headlines"],
        "save_reason": "A protective lesson viewers want to keep — high save-rate.",
        "share_reason": "'Don't make this mistake' is inherently shareable.",
        "teaching_anchor": "The obvious read is often the wrong read.",
        "compliance_note": "Frame as education. Never 'do this instead' as advice — 'understand this instead'.",
    },
    "market_myth": {
        "id": "market_myth",
        "name": "Market Myth Bust",
        "when_to_use": "The obvious interpretation of the day is actually wrong.",
        "example_hook": "Nifty wasn't the full story.",
        "first_frame_promise": "What looked true today wasn't — here's what really happened.",
        "best_for": ["misleading green/red day", "narrow rally", "index vs breadth",
                     "headline vs reality"],
        "save_reason": "Corrects a belief — viewers save myth-busts to remember them.",
        "share_reason": "Contrarian truth invites 'wait, really?' shares.",
        "teaching_anchor": "The headline number can hide market breadth.",
        "compliance_note": "Bust the myth with sourced facts, not a counter-tip.",
    },
    "risk_explainer": {
        "id": "risk_explainer",
        "name": "Scam / Risk Explainer",
        "when_to_use": "A risk, trap or fraud pattern is genuinely relevant and factual.",
        "example_hook": "This is how investors get trapped.",
        "first_frame_promise": "Here's the trap — so you can see it coming.",
        "best_for": ["pump-and-dump", "guaranteed-return scam", "fake tips",
                     "unregistered advisor", "F&O over-leverage"],
        "save_reason": "Protective knowledge — among the highest save-rate finance content.",
        "share_reason": "People share risk warnings to protect friends and family.",
        "teaching_anchor": "Risk comes from what you don't see.",
        "compliance_note": "Aligns with SEBI investor-education direction: anti-tip, anti-guaranteed-return. "
                           "Factual only — never name-and-accuse without a cited source.",
    },
}

FORMAT_IDS = list(FORMATS.keys())

# Signal words in a story that nudge toward a format (deterministic scoring).
_FORMAT_SIGNALS = {
    "hidden_mechanism": ["index", "nifty", "sensex", "weight", "bank nifty", "fii", "dii",
                         "flows", "rotation", "underneath", "heavyweight"],
    "one_sector": ["sector", "banks", "banking", "it ", "energy", "auto", "defence",
                   "pharma", "metals", "realty", "fmcg", "psu"],
    "policy_signal": ["rbi", "sebi", "budget", "tax", "policy", "rate", "repo",
                      "regulation", "government", "reform", "tariff", "duty"],
    "retail_mistake": ["retail", "investors", "beginner", "mistake", "chasing", "panic"],
    "market_myth": ["record", "all-time high", "rally", "crash", "green", "red",
                    "breadth", "narrow"],
    "risk_explainer": ["scam", "fraud", "trap", "guaranteed", "tip", "pump", "leverage",
                       "default", "penny", "warning"],
}


def score_formats(text: str) -> dict[str, int]:
    """Deterministic keyword overlap score per format for a story blob."""
    t = (text or "").lower()
    return {fid: sum(1 for kw in kws if kw in t) for fid, kws in _FORMAT_SIGNALS.items()}


def best_format(text: str, *, default: str = "hidden_mechanism") -> str:
    scores = score_formats(text)
    top = max(scores, key=lambda k: scores[k])
    return top if scores[top] > 0 else default


def get(format_id: str) -> dict:
    return FORMATS.get(format_id, FORMATS["hidden_mechanism"])
