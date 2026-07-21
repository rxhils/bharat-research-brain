# /backtest — Redesign Plan

**Concept:** The Evidence Room — an editorial proof document (Fey/column.com energy) where the COVID de-risk becomes a scroll-scrubbed equity-curve scrollytelling sequence, gold marks the risk story, emerald marks the return story.

**Signature moment:** "The Crash, Scrubbed" — a 320vh sticky scrollytelling section where the 2020 COVID equity curve (Enhanced F+ vs Nifty 500) draws via scroll-linked SVG pathLength while the four graded-cash exposure steps (100→50→25→50%) light up in sequence, the drawdown gap between the two lines filling gold as the market falls ~38% and the strategy holds at −13.88%.

---

# /backtest Redesign — "The Evidence Room"

Repo root: `F:\trymaven\code\github-bharat-research-brain\maven-dashboard`. Page: `app/backtest/page.tsx` (read; grade C confirmed: dashboard-scale hero, no equity/drawdown curve, static COVID list, zero gold).

## 1. CONCEPT

This is the proof page — it should feel like a forensic exhibit read slowly, not a dashboard glanced at. Art direction: column.com's "bank as literary journal" serif editorial gravity fused with fey.com's cinematic data-storytelling — near-black canvas, giant Fraunces display, long-measure prose between data blocks, hairline dividers instead of card chrome (resend.com), and one narrative spine running top to bottom. Accent discipline (vercel rule, ≤3 per viewport): **emerald = return, gold-soft = risk survived**. Gold appears exactly where the page's real claim lives — the drawdown numbers and the COVID sequence — so it reads as the premium seal on the risk story, per the Robinhood Gold champagne-on-black rationale.

## 2. SIGNATURE MOMENT — "The Crash, Scrubbed"

Replaces the static `COVID_TRACE` list. New file `app/backtest/covid-scrub.tsx` ("use client").

- **Structure:** wrapper `div` `h-[320vh]`, child `sticky top-0 h-screen` (Aceternity Sticky Scroll Reveal pattern). Inside: full-width SVG equity chart (Enhanced F+ line emerald, Nifty 500 line `#64748b`), Feb–Jun 2020, plus a right rail of the four exposure-step cards.
- **APIs (framer-motion 11):** `const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] })` → `useSpring(scrollYProgress, { stiffness: 100, damping: 30 })` → drives (a) `pathLength` on both `motion.path` strokes via `style={{ pathLength }}` (Tracing Beam pattern); (b) opacity/translate of each step card via `useTransform(p, [i/4,(i+0.6)/4], [0,1])`; (c) a `motion.rect` clip on a gold-soft (`#c9a961` at 18% fill, gradient to transparent) area between the two paths — the "gap" fills as the index falls away; (d) a live `useTransform(p, v => …)` mono readout ticking market DD toward −38% / strategy DD toward −13.88% (Number Ticker pattern via `useMotionValue` + `useTransform` render).
- **Trigger/duration:** pure scroll-scrub, reversible; no clock. Spring gives the scrub feel; `EASE` from `components/motion.tsx` on card entries (0.4s).
- **Reduced motion (operator machine has it ON):** scroll-linked motion values bypass OS setting by construction, but gate anyway with `useReducedMotionSafe()`: when true, render the finished chart (pathLength 1, all steps visible) in a normal-height section. Step-dot pulse micro-accent gets `.brand-motion`.
- **Data prerequisite:** export a ~120-point weekly equity series for Feb–Jun 2020 from the frozen engine's committed simulation artifacts into `app/backtest/data/covid-equity.ts` (static const, honest, cited to commit 6ced078 in a caption). No API changes.

## 3. SECTION-BY-SECTION

**Hero — editorial rebuild** (`page.tsx` header). Kill the dashboard-sized h1. New scale: eyebrow row keeps both pills (mono, tracking +0.08em); h1 becomes Fraunces at `clamp(2.5rem, 1.5rem + 4.5vw, 5rem)`, line-height 1.02, letter-spacing −0.02em: "Half the drawdown. **The proof.**" — "The proof." in gold-soft italic. Sub-para stays but widens to `max-w-3xl text-base`. Below: a 4-stat count-up band (`+129.97%`, `vs +82.17%`, DD `14.05%` gold, `4/4 windows`) — new `app/backtest/stat-ticker.tsx` using `useMotionValue(0)` + `animate(mv, target, {duration: 1.6, ease: "easeOut"})` on `useInView({once:true})`, static values under `useReducedMotionSafe`. Delete the old "The headline" Panel (hero absorbs it); keep second Stat row as a slim mono strip under the band. Hero background: single radial emerald glow at 6% behind the h1 (vercel gradient-as-light), no cards.

**Full-period equity curve — the missing artifact.** New section directly after hero: `app/backtest/equity-curve.tsx` — Recharts `AreaChart` (already a dep), 2021–2026 Enhanced F+ vs Nifty 500 TRI monthly equity (₹10L → ₹22.99L vs ₹18.22L), emerald gradient fill 10%→0, index as hairline slate line, wrapped in existing `ChartReveal`. Beneath it an inverted drawdown ribbon (`Area` of DD%, rose fill 8%) sharing the x-axis — the equity+underwater pairing every serious backtest report ships. Data: monthly series (~60 pts) exported to `app/backtest/data/equity-series.ts` from the frozen artifacts. Caption cites commit + "backtested, not live".

**Era dividers** → editorial chapter heads: Fraunces `clamp(1.75rem, 1rem + 2.5vw, 3rem)` with mono eyebrow ("ERA 1 · 2021–2026"), one-sentence serif standfirst, hairline. Linear-style mono labels.

**Walk-forward panels:** keep `WFTable`/`WindowReturns` but restyle `Panel` with the glass recipe: `bg-white/[0.04]`, gradient hairline via p-px wrapper (`bg-gradient-to-b from-white/[0.14] to-white/[0.03]` — matches /broker cards), `inset 0 1px 0 rgba(255,255,255,.08)`, radius 20. Alpha column gets emerald/rose chips; Max DD column switches amber→gold-soft (risk = gold system-wide). Row stagger on scroll via existing `Reveal` (staggerChildren 0.06, Vercel pattern 9).

**Drawdown bars:** move "half the pain" chart into Era 2 full-width; gold `Cell` for Enhanced F+ bar instead of emerald (it's a risk chart). Sub copy unchanged (already honest).

**COVID section** → replaced by the signature scrollytelling (§2).

**₹10L tables:** unchanged data; the winning row's tint becomes a left gold-soft 2px inset border + emerald text, so the eye ladder is gold-frame → emerald-number.

**Caveats:** promote visually — this page's credibility engine. Two-column editorial footnote layout, numbered `01–06` mono markers in gold-soft, hairline top rule, `Reveal` stagger. Copy untouched (it's excellent and compliant).

**Disclaimer:** keep verbatim.

## 4. 3D AND DEPTH

No WebGL. This page's object of desire is a chart, not a device; a shader orb would fight the evidence. Budget spent instead on: CSS radial glow behind hero (~0KB), glass gradient-hairline panels, the scroll-scrubbed SVG (framer-motion already in bundle, +0KB deps), and a 2% `feTurbulence` noise data-URI overlay on the hero glow to kill banding (Superdesign recipe). Perf: SVG paths ≤120 points, transforms/opacity only, springs on the compositor. If a later pass wants depth, a CSS `perspective` tilt-flatten on the equity-curve card (motion pattern 8, `useTransform([0,0.4],[10,0])` deg) is the ceiling.

## 5. IMPLEMENTATION STEPS

1. **(S)** Export `data/equity-series.ts` + `data/covid-equity.ts` from frozen backtest artifacts; cite commit in comments. Blocks steps 3–4.
2. **(S)** Hero rebuild in `page.tsx`: type scale, gold accent, glow, absorb headline panel.
3. **(M)** `stat-ticker.tsx` count-up band (`useMotionValue`/`animate`/`useInView`; reduced-motion static).
4. **(M)** `equity-curve.tsx` — equity + underwater Recharts pair with `ChartReveal`.
5. **(L)** `covid-scrub.tsx` signature scrollytelling — sticky scrub, path draw, gold gap fill, DD ticker, static fallback. Watch tsc: type `useTransform` outputs explicitly; SVG path attrs as `MotionProps` (framer-motion 11 typings are strict here).
6. **(S)** Panel glass restyle + era chapter heads + gold risk-color sweep (amber→gold-soft on DD cells/bars).
7. **(S)** Caveats editorial layout + `Reveal` staggers.
8. **(S)** Verify: `npx tsc --noEmit` (only gate — next build broken on this box), then localhost visual pass with OS reduced-motion ON and OFF. Per the deploy-safety rule: no commit/push without explicit operator approval.

Bundle risk: zero new deps; only new first-party client components (~8KB). tsc risk concentrated in step 5.
