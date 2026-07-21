# /strategies — Redesign Plan

**Concept:** A quant desk's tear-sheet wall: fey.com-grade data storytelling on near-black, where the three validated portfolios are plotted as physical objects on an animated risk/return map — every number verbatim from the backtests, every visual earned by real data.

**Signature moment:** RiskReturnMap: an SVG risk/return scatter (x = max drawdown, y = total return) where the Nifty 500 benchmark dot and three strategy dots draw in sequentially via framer-motion pathLength strokes and spring-scaled dots, wrapped in .brand-motion so it plays despite OS reduced-motion; built purely from the page's existing validated figures, so it is honest by construction.

---

# /strategies — Redesign Plan

## 1. CONCEPT
This page should feel like the tear-sheet wall of a serious quant desk — fey.com's "data as storytelling" on Maven's near-black canvas. Today it is a C-grade grid of text cards with a factual bug ("Two strategies are live" over three cards) and zero charts on a page whose entire job is performance. The redesign makes the *numbers themselves* the art: one cinematic risk/return visualization as the hero object (Vercel's glow-behind-the-object trick, Linear's mono eyebrows and hairlines), glass tear-sheet cards beneath it, and the seven dead dashed cards compressed into a single quiet pipeline rail. Discipline: emerald marks performance, gold marks the flagship, everything else three-step gray. All copy stays research-language; every figure is verbatim from the validated backtests.

## 2. SIGNATURE MOMENT
**`RiskReturnMap`** (`components/strategies/risk-return-map.tsx`, "use client"). An SVG scatter: **x = max drawdown (%), y = total return (%)** — plotted from the exact `LIVE` figures plus the Nifty 500 benchmark (+82.17%, and its stated ~38% COVID drawdown as an annotation, not an axis point unless the true index max-DD figure is confirmed). Four objects: benchmark dot (dim gray, dashed hairline reference lines), Quant (emerald + gold ring, crown), Defensive (emerald), Concentrated (emerald). "Better" direction (up-left) labeled with a mono eyebrow: `LOWER DRAWDOWN → HIGHER RETURN`.

Motion spec (framer-motion 11, patterns: Magic UI *Animated Beam* / Aceternity *Tracing Beam*):
- Trigger: `useInView(ref, { once: true, margin: "-15% 0px" })`.
- Axes: two `motion.line`s animate `pathLength` 0→1, 0.5s, `EASE`.
- For each strategy, staggered 0.25s apart: a `motion.path` connector from the benchmark dot to the strategy dot draws via `pathLength` (0.6s, `EASE`), then the dot springs in `scale: 0→1` (`type:"spring", stiffness:300, damping:20`) with its mono label and value fading up 0.2s later.
- Benchmark dot appears first (0.3s fade) so the strategies visibly *depart from* it — the narrative is "distance from index."
- **Reduced-motion reality:** operator machine has RM on. Wrap the whole SVG group in `className="brand-motion"` and drive the sequence with `animate()`/motion values keyed off `useInView` only — do **not** gate on `useReducedMotionSafe`; this is the page's one must-see accent. Total sequence ≈1.6s. Static-final-state fallback only if JS fails (SSR renders final positions; animation is progressive enhancement — initial opacity via inline style set on mount).

## 3. SECTION-BY-SECTION

**Header** (`app/strategies/page.tsx`):
- **Fix the bug**: derive the sentence from data — `` `${LIVE.length} strategies are live and fully backtested` `` rendered as "Three strategies are live…". Never hardcode the count again.
- Keep "Models, ranked." but upscale: `clamp(2.5rem, 1rem + 5vw, 4.5rem)`, Fraunces, `tracking-[-0.02em] leading-[0.98]` (column.com giant-serif register). Eyebrow switches to JetBrains Mono, `tracking +0.08em`.
- Add a mono stat strip under the subhead using existing `CountUp` from `components/motion.tsx` (delete the page-local duplicate `Reveal`/`CountUp` — they already exist in motion.tsx): `3 LIVE · 7 IN VALIDATION · 2021–26 WINDOW · vs NIFTY 500 +82.17%`.

**Signature section** — insert `RiskReturnMap` directly after the header inside `ChartReveal` (motion.tsx) at ~420px tall, full content width, radial emerald glow *behind* the SVG (Vercel light-source trick), 2–3% noise overlay to kill banding. Caption in text-dim: "Backtested 2021–26, current index constituents — not a live track record."

**Live cards** (extract to `components/strategies/live-card.tsx`):
- Upgrade to the house glass recipe: `bg-white/[0.06]`, `backdrop-blur-[14px] saturate-[1.7]`, gradient p-px hairline border (brighter top edge, like /broker), `inset 0 1px 0 rgba(255,255,255,.12)`, radius 20px. Flagship keeps gold ring + crown; gold appears nowhere else.
- **Add the missing chart**: each card gets a mini drawdown-profile bar pair — strategy max-DD vs the benchmark reference — as two `motion.div` width bars (amber vs dim) animating `scaleX` on in-view, `transformOrigin:"0%"`, 0.7s `EASE`. Honest: uses only the existing DD figures. If real backtest equity-curve series exist as JSON (check `F:\trymaven\code\github-bharat-research-brain\maven-dashboard\app\` data/assets), add a 48px sparkline per card via `motion.path` pathLength; **if no real series exists, ship no sparkline — never a decorative fake curve.**
- Stat tiles switch to `font-mono tnum` at `text-xl`; hover keeps the current spring lift plus a pointer-tracked radial-gradient spotlight (Magic UI *Border Beam* hover variant, `useMotionValue` mouse coords → background template) — hover-only, so RM-safe.

**In-validation section** — kill the seven dashed cards (dead space). Replace with `components/strategies/pipeline-rail.tsx`: one glass panel containing a 7-row compact ledger — mono name, one-line style (existing copy), and a right-aligned "In validation" tick using a shared-layout hairline treatment. Rows stagger in via one `Reveal` parent with `staggerChildren:0.05`. Height drops from ~3 grid rows to ~320px. Eyebrow: `VALIDATION PIPELINE — NO NUMBERS UNTIL EARNED` (this line is the brand flex; promote it from body copy).

**Disclaimer** — keep verbatim, add a hairline top border and mono `METHODOLOGY` eyebrow so it reads deliberate, not fine-print.

## 4. 3D AND DEPTH
No WebGL. This page's object is a chart, not a scene; R3F's ≥170KB gz chunk buys nothing an SVG can't do here (the digest's own guidance: WebGL on exactly one canvas per site — that budget belongs to the homepage/broker hero). Depth comes free: layered radial glows behind the map and flagship card, glass blur+saturate, noise overlay, and a subtle CSS `perspective(1200px) rotateX(1.5deg)` settle-to-flat on the map container on scroll entry (hover-neutral, `brand-motion`). Perf cost ≈0KB extra JS beyond framer-motion already on the page.

## 5. IMPLEMENTATION STEPS
1. **(S)** Fix headline count — derive from `LIVE.length`. Ship even if nothing else does.
2. **(S)** Delete page-local `Reveal`/`CountUp`; import from `components/motion.tsx`. Run `npx tsc --noEmit` (risk: prop-signature drift between local and shared versions).
3. **(M)** Build `components/strategies/risk-return-map.tsx` with hardcoded validated figures; `brand-motion` wrapper; SSR-final-state markup. tsc risk: SVG `motion.path` prop typing — keep attrs on the motion elements, not spread objects.
4. **(S)** Insert map into page inside `ChartReveal`; glow + noise layers.
5. **(M)** Extract `live-card.tsx`; apply glass recipe + gradient p-px border; add drawdown-bar pair; mono stat tiles.
6. **(S)** Hover spotlight on live cards (`useMotionValue` radial gradient).
7. **(M)** Build `pipeline-rail.tsx`; delete `SoonCard` and its grid.
8. **(S)** Header type scale + mono stat strip.
9. **(S)** Check repo for real backtest series JSON; only if found, add sparklines (M if found).
10. **(S)** Final `npx tsc --noEmit`; verify on localhost per deploy-safety rule; no commit/push without explicit approval. Bundle risk: zero new deps — everything uses framer-motion 11 already shipped.
