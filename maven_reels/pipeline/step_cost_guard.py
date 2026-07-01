"""Step — Cost Guard.

The single chokepoint for paid Higgsfield generation. Daily runs must cost ~zero:
they reuse the asset library and render with Remotion. Any paid generation is
BLOCKED unless explicitly allowed (ALLOW_PAID_GENERATION=true) and within the
per-run cap. This module never calls Higgsfield — it only decides whether a
request MAY proceed, and records the decision as an auditable artifact.
"""
from __future__ import annotations

from . import config, state


def evaluate(date: str, *, requested: int, approved: bool = False) -> dict:
    """Decide whether `requested` paid Higgsfield generations may proceed.

    Returns {allowed, requires_approval, reason, cap, requested, ...}. `approved`
    reflects an explicit human OK (from the UI/Telegram). Even then, generation is
    only allowed when ALLOW_PAID_GENERATION is true and within the approval cap.
    """
    allow_paid = config.ALLOW_PAID_GENERATION
    daily_cap = config.MAX_HIGGSFIELD_GENERATIONS_PER_DAILY_RUN
    approval_cap = config.MAX_HIGGSFIELD_GENERATIONS_WITH_APPROVAL

    if requested <= 0:
        decision = {"allowed": True, "requires_approval": False,
                    "reason": "No paid generation requested — reusing asset library.",
                    "cap": daily_cap}
    elif not allow_paid and not approved:
        decision = {"allowed": False, "requires_approval": True,
                    "reason": (f"{requested} paid Higgsfield generation(s) requested but "
                               "ALLOW_PAID_GENERATION=false. Explicit approval required."),
                    "cap": daily_cap}
    elif approved and not allow_paid:
        # approved via UI but env still locked — honour the approval cap only
        allowed = requested <= approval_cap
        decision = {"allowed": allowed, "requires_approval": not allowed,
                    "reason": (f"Approved {requested} generation(s); approval cap is "
                               f"{approval_cap}." if allowed else
                               f"Requested {requested} exceeds approval cap {approval_cap}."),
                    "cap": approval_cap}
    else:  # ALLOW_PAID_GENERATION=true
        allowed = requested <= max(daily_cap, approval_cap if approved else 0)
        decision = {"allowed": allowed,
                    "requires_approval": not allowed,
                    "reason": (f"Paid generation enabled; {requested} within cap."
                               if allowed else
                               f"Requested {requested} exceeds allowed cap."),
                    "cap": max(daily_cap, approval_cap if approved else 0)}

    payload = {"date": date, "requested": requested, "approved": approved,
               "allow_paid_generation": allow_paid,
               "use_existing_asset_library": config.USE_EXISTING_ASSET_LIBRARY,
               "max_per_daily_run": daily_cap,
               "max_with_approval": approval_cap, **decision}
    state.save_artifact(date, "cost_guard", payload)
    return payload
