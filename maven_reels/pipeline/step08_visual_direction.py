"""Step 8 — Visual Director.

Picks the dark-finance scene design system for the reel (background, typography,
motion, palette). Analogous to the carousel Art Director, tuned for 9:16 motion.
"""
from __future__ import annotations

from . import state

DIRECTIONS = [
    {"name": "Dark Terminal", "background": "near-black navy #05070A with faint grid",
     "typography": "tight geometric sans; oversized bold on-screen lines",
     "motion": "slow Ken-Burns push-in + hard cuts on the beat",
     "palette": ["#05070A", "#FFFFFF", "#1FB6A6", "#EF4444", "#27C281"],
     "fit": "premium, high-contrast, reads instantly on mute"},
    {"name": "Editorial Mono", "background": "charcoal with a single accent bar",
     "typography": "mono for numbers, sans for words; strong hierarchy",
     "motion": "gentle pan + crossfades", "palette": ["#0B1117", "#E6EDF3", "#22D3EE"],
     "fit": "clean research-note feel"},
]


def run(date: str) -> dict:
    chosen = DIRECTIONS[0]
    payload = {"date": date, "directions": DIRECTIONS, "selected": chosen["name"],
               "selection_rationale": (
                   f"'{chosen['name']}' — highest contrast + instant readability on "
                   "mute, which is what carries retention in a finance reel.")}
    state.save_artifact(date, "visual_direction", payload)
    return payload
