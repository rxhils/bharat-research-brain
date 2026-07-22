# /backtest — B+

**Verdict:** The Evidence Room concept mostly landed: the scroll-scrubbed COVID sequence is a genuine signature moment (single MotionValue driving paths, gold gap, live DD readouts, step cards — Fey-grade engineering), and the honesty layer (caveats, verbatim-figure captions, disclaimers) is best-in-class. What keeps it off A is craft residue: the hero's headline numbers SSR as "+0.00%", the risk color is an off-token amber instead of the planned gold system, numeric table columns are left-aligned, and the two era sections repeat an identical table+redundant-bar-chart layout that reads templated next to the bespoke scrub.

**Skipped plan items:** From docs/design-plan/page-backtest.md: (1) §3 "gold risk-color sweep (amber→gold-soft on DD cells/bars)" — SKIPPED; WFTable/CapTable DD cells still use text-amber (#fbbf24, not a house token) and the Enhanced F+ drawdown bar Cell is EMERALD, not gold. (2) §3 caveats "numbered 01–06 mono markers in gold-soft" — watered down to text-dim. (3) §3 ₹10L winning row "left gold-soft 2px inset border" — watered down to an emerald inset (page.tsx:274). These three were consciously traded away for the "gold exactly twice" rule (page.tsx:19-21), but the plan's gold-=-risk semantic was the stronger system; amber survived as an unplanned third accent. (4) §2 reduced-motion static fallback for the scrub ("render finished chart in normal-height section") — replaced by the house .brand-motion policy (plays under OS reduced-motion); defensible but a divergence. (5) §2 320vh scrub height trimmed to 300vh (minor). (6) §2 per-card useTransform opacity ranges replaced by a stepped setState activation — arguably better. Everything else (hero rebuild, stat band, equity+underwater pair, era chapter heads, glass panels, caveat layout) shipped as planned.

## Ranked fixes

### 1. [high/S] Fix CountUp SSR so the server HTML contains the final figures, not zeros. Render the target value as initial text content (e.g. span defaults to formatted `to`), then on mount set it to 0 and animate up — or animate only after hydration via useEffect while keeping the real number in the markup. Live fetch of trymaven.in/backtest currently shows '2021–26 return: +0.00%, Max drawdown 0.00%, Bull windows beaten 0/4' — the proof page's headline claim is zeroed for crawlers, link previews, and slow connections.

_Where:_ components/motion.tsx (CountUp) + app/backtest/stat-ticker.tsx:33-43; same pattern check for CovidScrub readouts (covid-scrub.tsx:266-274, which at least start honestly at 0%)

### 2. [high/S] Retire amber (#fbbf24) — it is not a house token and acts as an unplanned third accent competing with gold. Recolor Max DD cells in WFTable/CapTable and the STRESS_DD Enhanced F+ bar to either muted slate with a rose tint at severity, or complete the plan's gold-=-risk sweep at whisper opacity (gold-soft/60 text) so the two prominent gold moments (hero 'The proof.', gap band) stay the only loud uses. Either direction restores one-system color; today the page speaks emerald, gold, amber, and rose simultaneously.

_Where:_ app/backtest/page.tsx:58 (AMBER const), :226, :279 (text-amber cells), :98-102 (STRESS_DD accents)

### 3. [high/S] Right-align all numeric columns in WFTable and CapTable and add a quiet row-hover state (hover:bg-white/[0.02]). Left-aligned mono numerals with ragged right edges is the single most visible table-craft tell vs Linear/Stripe; tnum only pays off when digits stack on a shared right edge. Add className tnum + text-right to return/Sharpe/DD/trades/alpha cells and matching th alignment.

_Where:_ app/backtest/page.tsx:201-289 (WFTable td/th ~lines 208-244, CapTable ~lines 261-282)

### 4. [high/M] Give the equity curve its editorial data-labels: end-of-line value labels (₹22.99L emerald, ₹18.22L slate) pinned at the right edge of the top chart, and a ReferenceDot + small mono annotation at the max-drawdown trough on the underwater ribbon ('−14.05% · worst point'). The section is billed as 'the missing artifact' but renders as a default Recharts pair whose payoff numbers live only in an 11px caption — Awwwards-level chart storytelling puts the conclusion on the chart itself. All figures already exist in data/equity-series.ts; no new data.

_Where:_ app/backtest/equity-curve.tsx:55-154 (add Recharts ReferenceDot + absolutely-positioned end labels)

### 5. [med/M] De-duplicate the era sections: WindowReturns bar charts repeat exactly the numbers in the table directly above them, so the page's midsection is table→bars→table→bars boilerplate. Replace each bar chart with a dumbbell/alpha strip per window (slate dot = index, emerald dot = Enhanced F+, connecting line colored by sign of alpha) rendered inline as a compact SVG — adds the alpha-gap reading the table can't show and breaks the templated rhythm between the two eras.

_Where:_ app/backtest/page.tsx:157-176 (WindowReturns) used at :361-363 and :389-391

### 6. [med/S] Add a scrub affordance and progress cue to the signature moment: on entering the sticky viewport, show a one-time 'scroll to scrub' pill with a subtle downward shimmer that fades after first scroll input, plus a hairline progress track (2px, emerald fill driven by the existing lineProg MotionValue via scaleX) along the panel's bottom edge. Right now the only instruction is an 11px caption at the very bottom; users who don't scroll past the first frame see a mostly-empty chart and may bounce through 300vh confused.

_Where:_ app/backtest/covid-scrub.tsx:135-284 (inside the sticky panel; reuse lineProg, no new MotionValues)

### 7. [med/M] Tighten the mobile scrub layout: at 375px the sticky frame stacks legend + chart + 2-col step cards + 2 readout tiles + 3-line caption inside h-svh, and the internal-scroll escape hatch only triggers at max-height:640px — tall narrow phones (812-932px) can still clip the caption or readouts. Audit at 375x812/390x844; likely fixes are hiding the step-card notes (keep date+%) below sm, dropping the caption into a post-sticky block, and letting the readout tiles shrink to text-xl.

_Where:_ app/backtest/covid-scrub.tsx:135-140 (wrapper/sticky media queries), :254-275 (rail + readouts)

