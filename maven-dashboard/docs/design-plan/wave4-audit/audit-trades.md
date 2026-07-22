# /trades — B+

**Verdict:** Wave 2 landed almost every planned item — glass scoreboard, TapePath, TradeChart in the accordion, layoutId pills, honest provenance footnote — and the code discipline (server-computed stats, honest empty states, .brand-motion gating) is genuinely strong. But the served HTML shows "0 of 60 open, 0% win rate, +0.00% best trade" because CountUp SSRs at zero — a direct honesty failure to crawlers and first paint — and the page below the hero is a 60-row undifferentiated scroll across three identical sections whose signature Tape is a modest, unlabeled 64px line, which keeps it a very good dashboard rather than an Awwwards page.

**Skipped plan items:** 1) Step 8 watered down: plan asked for a right-aligned per-engine mini-stat "scoreboard echo" on each engine card; shipped as a plain left-aligned sub-sentence inside TradesView instead. 2) §4 optional row hover spotlight (Border-Beam-lite radial gradient following pointer) — skipped entirely (plan allowed skipping, but it is the page's only missing micro-interaction layer). 3) §2 count-up trigger: plan specified useInView-fired motion-value ticker rendering the formatted number; the shipped CountUp SSRs zero, so the plan's implicit "every figure verbatim" guarantee is broken in static HTML. 4) TradeChart plan called for exit/latest marker WITH mono date labels and min/max "ruled ticks"; shipped min/max ₹ values but no exit-date label and no ruled tick lines. 5) Footer copy was never updated for the third engine ("Concentrated") — it still describes only Enhanced F+ and Defensive.

## Ranked fixes

### 1. [high/S] Fix CountUp SSR zeros: render the true final value in server HTML (e.g. CountUp renders `{to}` inside the span initially, then on hydrate+useInView snaps to 0 and animates up; or gate the 0-start behind useEffect so pre-JS/crawler HTML shows +28.78% not +0.00%). The live page currently serves 'Open positions 0 of 60' and 'Best trade +0.00% CEMPRO' — factually wrong static HTML that violates the figures-verbatim law for any no-JS reader.

_Where:_ components/motion (CountUp) + app/trades/page.tsx:112-138

### 2. [high/M] Elevate The Tape from decoration to signature: grow h-16 to ~h-24, add a mono caption naming the metric ('mean % move from entry, all trades'), pin start/end % values in tnum mono at the path's first/last points, and drop a single gold-soft marker on the max reading (second sanctioned gold use). Right now the hero's centerpiece is an unlabeled anonymous line — a viewer cannot tell what it measures, which is both a design and an honesty gap.

_Where:_ components/trades.tsx:33-88 (TapePath) + app/trades/page.tsx:142

### 3. [high/M] Break the 60-row monotony: add a slim sticky (top-anchored) engine jump-nav under the hero — three mono pills (ENHANCED F+ · DEFENSIVE · CONCENTRATED) with the shared layoutId pill pattern already in the codebase — and complete plan step 8 by moving each engine's 'n trades · x open · closed avg' into a right-aligned tnum mini-stat block on the card header row.

_Where:_ app/trades/page.tsx:155-163 + components/trades.tsx:368-387

### 4. [med/S] Update the footer methodology line to cover all three live engines — it currently explains only Enhanced F+ (vol-adjusted momentum) and Defensive (low volatility) while the page renders a Concentrated section with 10 real positions; one clause per engine, research language only, no invented detail (pull Concentrated's one-line rule from the same source that feeds the backtest page).

_Where:_ app/trades/page.tsx:165-169

### 5. [med/S] Disclose unrealized figures in the hero: 'Best trade' and 'Avg P&L' include open positions — change captions to 'incl. open (unrealized)' / '{ticker} · open' so a +28.78% headline number is never mistaken for a booked result. Small copy change, large honesty dividend.

_Where:_ app/trades/page.tsx:121-138

### 6. [med/M] Ship the skipped row-spotlight micro-interaction: desktop-only radial-gradient hover following the pointer on TradeRow buttons (useMotionValue x/y into a background template string, transform/opacity only, motion-safe gated) — the one planned layer that would give 60 identical rows tactile depth without adding glass.

_Where:_ components/trades.tsx:241-283 (TradeRow button)

### 7. [med/S] Harden TradeChart labels: clamp the entry label when entryY < ~14% (flip to below the dashed line instead of -translate-y-full, which clips against the 140px container top), and add first/last date ticks in mono 10px at the chart's bottom corners so the x-axis has anchors — the plan's 'ruled ticks' promise, completed.

_Where:_ components/trades.tsx:213-223

