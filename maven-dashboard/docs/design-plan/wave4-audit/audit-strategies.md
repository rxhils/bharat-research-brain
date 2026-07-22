# /strategies — B+

**Verdict:** Disciplined, honest, and cohesive — derived headline count, gold used exactly twice, verbatim figures, tight validation grid — but the plan's actual signature (the RiskReturnMap scatter) was quietly swapped for per-card sparklines built from invented interpolated series, the one thing the plan explicitly forbade ("never a decorative fake curve"), and the live server HTML renders every hero number as +0.00% before hydration. It reads as a very good fintech page, not an Awwwards one: no singular must-see moment, crowded card mid-sections, and its most prominent visual is shape-fiction on a brand whose whole pitch is data honesty.

**Skipped plan items:** 1) RiskReturnMap signature scatter (plan §2, steps 3-4) — SKIPPED entirely; replaced by per-card sparklines. 2) The "no real series → ship NO sparkline" rule (step 9) — VIOLATED: the ~24-point series in page.tsx:40-80 are hand-authored interpolations, not backtest data (disclosed in a caption, but the plan said don't ship it at all). 3) Drawdown-profile bar pair (amber DD vs benchmark, §3) — replaced with total-return delta bars instead. 4) Pointer-tracked hover spotlight on live cards (step 6) — SKIPPED (only spring lift shipped). 5) pipeline-rail.tsx 7-row ledger with single staggerChildren parent — watered to a two-column grid of chips with per-item Reveals. 6) Component extraction (live-card.tsx, risk-return-map.tsx, steps 3/5/7) — skipped; everything inline in page.tsx. 7) ChartReveal wrapper + perspective settle-to-flat depth trick (§4) — n/a/skipped with the map. Done as planned: count fix, mono stat strip, type scale, glass recipe, methodology eyebrow, gold discipline.

## Ranked fixes

### 1. [high/M] Build the planned RiskReturnMap: SVG scatter (x = max drawdown, y = total return) plotting the Nifty 500 dot plus the three strategies from the verbatim figures only — benchmark fades in first, dashed connectors draw pathLength 0→1 staggered 0.25s, dots spring-scale in, 'LOWER DRAWDOWN → HIGHER RETURN' mono eyebrow, all inside .brand-motion with SSR-final-state markup. Honest by construction and the page's missing wow moment.

_Where:_ new components/strategies/risk-return-map.tsx, inserted in app/strategies/page.tsx after the header (~line 284)

### 2. [high/S] Fix CountUp so server HTML renders the FINAL value (the live page currently ships 'vs Nifty 500 +0.00%' and 0.00 stat tiles pre-hydration — a crawler/first-paint reads placeholder zeros on a performance page). Render the target number in SSR and only run the 0→N count client-side after in-view.

_Where:_ components/motion.tsx CountUp; consumed at app/strategies/page.tsx:249 and :282

### 3. [high/M] Replace the hand-authored sparkline series with real monthly equity-curve JSON exported from the backtest; if no real series exists, drop the sparklines and ship the plan's honest drawdown-bar pair (strategy max-DD amber bar vs benchmark reference) instead. The disclosed-but-fabricated curves are the page's biggest brand-integrity liability.

_Where:_ app/strategies/page.tsx:37-80 (NIFTY_SERIES + per-strategy series), Sparkline at :133-168

### 4. [med/M] Restore hierarchy inside each card: promote Total return to a single hero figure (~text-3xl font-mono, emerald) above the chart and demote max-DD/COVID-DD to a compact two-item row — currently three equal-weight tiles + two bar rows + a sparkline + two paragraphs compete and nothing wins.

_Where:_ app/strategies/page.tsx:244-254 (stat-tile grid) and DeltaBars placement :242

### 5. [med/S] Add the planned pointer-tracked radial-gradient spotlight on live-card hover (useMotionValue mouse coords → background template, hover-only so RM-safe) — the only micro-interaction now is a generic spring lift, which reads templated next to Linear/Vercel.

_Where:_ app/strategies/page.tsx LiveCard :205-265 (or extract to components/strategies/live-card.tsx per plan)

### 6. [med/S] Mobile pass on the cards: the 3-across stat tiles (grid-cols-3, 10px labels, text-lg numbers) cram at 375px — collapse to 1 hero + 2-up row below sm:, and let the sparkline legend wrap instead of justify-between truncating.

_Where:_ app/strategies/page.tsx:244 (grid-cols-3) and :162-165 (legend row)

### 7. [med/M] Give the validation section one typographic beat of its own: convert the chip grid into the planned single-panel ledger — hairline-separated rows, mono strategy name left, style line center, 'In validation' tick right, one Reveal parent with staggerChildren:0.05 — so section 02 feels designed rather than a settings list.

_Where:_ app/strategies/page.tsx:300-320 (SOON grid inside GlassPanel)

