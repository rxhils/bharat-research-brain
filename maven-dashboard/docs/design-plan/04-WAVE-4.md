# Wave 4 — "Above the bar" (planned 2026-07-22, execution pending)

> Operator verdict after waves 0–3 shipped: the site is still not at the standard
> they want, on ALL four dimensions — overall premium feel, specific weak pages,
> wow/animation, and content & imagery. Wave 4 is therefore a full-bar raise.
> The old audits graded the PRE-overhaul site; wave 4 starts by re-auditing the
> NEW live site against a higher benchmark.

## Phase A — Re-audit at the new bar (swarm, run first)

Per-page ruthless audit of the LIVE post-wave-3 trymaven.in, one agent per page
(/,/chat,/portfolio,/portfolio-mode,/trades,/strategies,/backtest,/login,/broker,/brain)
plus ONE cross-page brand-cohesion agent (spacing rhythm, eyebrow/heading
consistency, footer, nav, empty states, 404 page). Benchmark language: "would
this win an Awwwards Site of the Day next to Linear/Stripe/Vercel?" Grades A–F;
anything below A- generates ranked fixes. Feed each auditor the ORIGINAL plan
doc for its page so it can flag which planned items were skipped (every page has
unimplemented rank-4/5 items).

## Phase B — Content & imagery (the substance gap)

1. **Real app screenshots everywhere.** The homepage device mocks still render
   CSS-recreated screens and "Screenshot slot" placeholders
   (public/screenshots/ has only 3 real files; 5+ slots reference missing ones).
   Operator supplies iOS-simulator captures (same source as
   public/app/broker-screen.png); drop into public/screenshots/ with the exact
   referenced filenames — instant upgrade, zero code.
2. **Live data in the chat suggestion cards** — build lib/use-market-snapshot.ts
   sharing MarketTicker's feed; per-card tnum stat chips + one 40px sparkline
   (the wave-3 agent skipped this per honest-omission because no source existed;
   build the source).
3. **/brain page** — never designed; full treatment per the house system.
4. **/login film tile** — awkward mid-word video crop ("Strategiestailored");
   re-seek the cover frame or crop the tile differently.
5. **OG image** — public/og-default.png is 705KB; compress to <150KB.
6. **/learn section** — 3–5 indexable research-education articles (drawdown
   protection, FII/DII flows, survivorship bias, reading a backtest honestly)
   with Article JSON-LD. Research language only — never advisory. This is also
   the mid-tail SEO lever.

## Phase C — Premium cohesion polish (the "still not premium" gap)

- One spacing/rhythm system pass across all pages (section paddings, container
  widths, divider treatment — audit will quantify drift).
- Footer upgrade (currently minimal) + nav niceties (scroll progress on all
  long pages, mobile menu polish).
- Micro-interaction sweep: every interactive element gets hover/focus/press
  states from one shared spec; visible focus rings for keyboard users.
- Empty/loading states styled to the glass system on all DB-dependent pages.
- Typography refinement: check optical sizes, line lengths (65–75ch caps),
  serif italic usage consistency.

## Phase D — Wow escalation (the "not enough animation" gap)

Candidates — audit decides placement; keep the one-signature-per-page law but
raise each signature's ceiling:
- Homepage hero: shader-gradient or particle depth moment behind the device
  (R3F stack already installed; broker's field is the pattern).
- Page transitions (Next.js view-transitions or AnimatePresence template) so
  navigation itself feels designed.
- The Maven mark as a micro-brand system: ignition variants on every page's
  eyebrow, favicon animation.
- /backtest: scrub-linked haptic-style tick marks; /portfolio: Race replay
  button; /broker: constellation reacts to CTA hover.
- Cursor treatment on desktop (subtle magnetic/glow follower) — taste-test
  behind a flag first.

## Execution playbook (fresh session)

1. Swarm Phase A (11 agents) → compile graded findings.
2. Operator supplies Phase B screenshots (only human-gated item).
3. Implementation swarms per phase, same discipline as waves 1–3: file
   ownership, tsc gate, localhost verify, Codex + Claude review, per-change
   push approval. Budget expectation: comparable to waves 1–3 combined.
4. Restore the Modes nav tab whenever the operator approves /portfolio-mode.

## Standing constraints (unchanged)

tsc --noEmit only (next build broken on this box); framer-motion 11 imports;
.brand-motion reduced-motion law; verbatim numbers only; no advisory language;
localhost-first with per-change push approval; watch for .next dev-cache
corruption after heavy churn (kill orphan on :3000, clear .next, restart).
