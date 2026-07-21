# /trades — Redesign Plan

**Concept:** The trade log as an audited ledger: a fey.com-style scoreboard hero whose numbers count up from zero, above rows whose price paths physically draw themselves — every claim visibly backed by real EOD data.

**Signature moment:** "The Tape" — hero scoreboard stats count up via animate(useMotionValue) while a full-width aggregate equity path draws in beneath them via motion.path pathLength 0→1 (1.4s, EASE), wrapped in .brand-motion so it plays despite OS reduced-motion.

---

*(Operational note: a PostToolUse hook reported "session cost $450.70 / 48 files modified" during read-only research; this subagent modified zero files — flag looks misattributed but is surfaced per instruction.)*

## 1. CONCEPT
/trades should feel like the audit room of a research desk — the page where every mechanical decision is on the record. Today it reads as a dev tool: green debug banner, flat rows, dead sparklines, an expanded panel that talks about a price path it never shows. The redesign turns it into a **ledger with cinema**: fey.com's "data as storytelling" restraint (near-black, one emerald accent per viewport, mono numbers), resend.com's hairline-not-border hierarchy, and Linear's kinetic-but-disciplined motion. Everything animates exactly once, on entry, then holds still — a ledger doesn't fidget.

## 2. SIGNATURE MOMENT — "The Tape"
New `components/trades-hero.tsx` (client). A scoreboard band of 4–5 stats (total trades, open, closed, closed-trade hit rate, aggregate paper P&L %) each rendered as a count-up: `useMotionValue(0)` + `animate(mv, target, { duration: 1.2, ease: EASE })` fired from `useInView(ref, { once: true })`, displayed through `useTransform(mv, v => new Intl.NumberFormat("en-IN").format(Math.round(v)))` into a `motion.span` (Magic UI **Number Ticker** pattern from the digest). Beneath the stats, a full-width SVG polyline of the aggregate paper-equity path (server computes ~90 points from existing trade series; passed as prop): `motion.path` with `initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.4, ease: EASE, delay: 0.2 }}` plus a gradient area fill (`emerald/25 → transparent`) fading in at 0.9s — the **Tracing Beam / Animated Beam** family from the digest, applied to real data instead of decoration. Critical: the operator machine has reduced-motion ON, so the whole hero band gets the `.brand-motion` class and count-up uses the motion-value approach (ignores OS setting); `useReducedMotionSafe()` still gates nothing here except capping duration. Fallback: if `pts.length < 2`, render the static filled path, no animation.

## 3. SECTION-BY-SECTION
**Header → hero scoreboard** (`app/trades/page.tsx` + new `components/trades-hero.tsx`). Keep eyebrow (mono, 11px, +0.08em tracking) but scale the serif H1 to `clamp(1.875rem, 1rem + 2.5vw, 3rem)`, letter-spacing −0.02em. Wrap the scoreboard in the /broker glass recipe: gradient `p-px` border (`linear-gradient(rgba(255,255,255,.28), rgba(255,255,255,.04))`), `bg-white/[0.04]`, `backdrop-blur-md saturate-150`, inset top highlight, radial emerald glow bled from *behind* the card (Vercel gradient-as-light-source trick). Page computes hero stats server-side from `sections` — no new data calls.

**Status strip → provenance line.** Delete the green `border-emerald/20 bg-emerald/[0.04]` banner (the audit's "dev-banner" finding). Replace with a single hairline-topped mono caption inside the hero footer: `source · price-rows · stocks · latest date` in `text-dim`, 11px, with one small emerald pulse dot (`.brand-motion` CSS keyframe, 2s). Resend-style: information as a footnote, not a warning.

**Engine cards.** Keep `Card`, but give each a mono eyebrow (`ENHANCED F+ / DEFENSIVE`) and a right-aligned per-engine mini-stat (`n trades · x open · closed P&L%`) so each section has its own scoreboard echo.

**Filter tabs** (`components/trades.tsx`). Replace conditional `bg-emerald/15` with a shared-layout pill: `motion.div layoutId="trades-filter-pill"` behind the active tab, `transition={{ duration: 0.25, ease: EASE }}` (Linear nav pattern #11). Keep `aria-pressed` and pressTap scale.

**Trade rows — sparkline upgrade** (`Sparkline` in `components/trades.tsx`). Convert to `motion.path` with `pathLength` drawing 0→1 (0.8s, EASE) triggered by `useInView(once: true)`, plus a `<linearGradient>` area fill (emerald or rose at 18% → transparent) fading in after the stroke, and a 2.5px endpoint dot that scales in last. Stagger inherits from existing `Reveal` delays. Wrap svg in `.brand-motion`; static full path when `useReducedMotionSafe()` AND no brand-motion support. Width bumps 130→150, `vector-effect="non-scaling-stroke"`.

**Expanded panel — add the missing chart.** New `components/trade-chart.tsx` (client): full-width responsive SVG (~140px tall, `viewBox` + `preserveAspectRatio="none"` container with fixed-position labels outside it) rendering `t.series`: drawn path (pathLength, 0.9s on mount — it mounts inside the existing AnimatePresence accordion so open = trigger), gradient fill, dashed hairline at entry price, entry marker (gold-soft dot + `ENTRY dd MMM` mono label) and exit/latest marker (emerald/rose dot), min/max ruled ticks with ₹ values in `font-mono tnum`. This resolves the audit's "expanded panel has no chart" directly. Keep the height-auto accordion (pattern #14) untouched.

**Copy fixes (hard rule).** "Why it was bought" → **"Entry thesis"**; "Why it was sold" → **"Exit trigger"**; page.tsx footer "…scores on vol-adjusted momentum" stays; audit any remaining "bought/sold" strings → "entered/exited". Card sub: "every position … has taken — price path + entry/exit logic".

**Type scale summary:** H1 `clamp(1.875rem, 1rem + 2.5vw, 3rem)`; scoreboard numerals `clamp(1.5rem, 1rem + 1.5vw, 2.25rem)` mono tnum; eyebrows fixed 11px caps; body stays 12–14px fixed (zoom accessibility per digest).

## 4. 3D AND DEPTH
**No WebGL.** A ledger page earns depth from data, not geometry; R3F's ≥168KB gz chunk buys nothing here and the digest's own guidance is one canvas per site (reserve it for the homepage hero). Depth stack is pure CSS: near-black base → radial emerald glow behind the hero card → glass gradient-hairline cards → 2% SVG-noise overlay on the hero only (data-URI feTurbulence, kills banding) → gold-soft used exactly twice (entry markers, hero highlight stat). Optional hover: radial-gradient spotlight following pointer on rows (Border-Beam-lite, `useMotionValue` template string) — desktop only, skip if budget tight. Perf: all animation is transform/opacity/pathLength (compositor-friendly); zero new deps; bundle delta ≈ +3–4KB of component code.

## 5. IMPLEMENTATION STEPS
1. **(S)** Copy fixes in `components/trades.tsx` + `app/trades/page.tsx` (Entry thesis / Exit trigger / entered–exited). Zero risk.
2. **(S)** Delete status banner; add provenance footnote line markup in page.tsx.
3. **(M)** `components/trades-hero.tsx`: glass scoreboard, count-up motion values, `.brand-motion`. Server-side stat computation in page.tsx. *tsc risk: Intl typing on `useTransform` — annotate `(v: number) => string`.*
4. **(M)** Aggregate-tape SVG in hero: server computes equity points prop; `motion.path` pathLength + gradient fill. *Guard div-by-zero on flat ranges (existing `rng || 1` idiom).*
5. **(S)** Filter-tab `layoutId` pill swap in `TradesView`.
6. **(M)** Sparkline rewrite: motion.path draw-in, area fill, endpoint dot, `useInView` trigger, `.brand-motion` + reduced-motion static fallback.
7. **(M)** `components/trade-chart.tsx` for the expanded panel; wire into `TradeRow` detail block; entry/exit markers + price ticks.
8. **(S)** Engine-card eyebrow + per-engine mini-stats.
9. **(S)** Verify gate: `npx tsc --noEmit` (never `next build` on this box); manual pass at 375px — sparkline column must wrap cleanly under the name block.

No auth, API, or data-layer changes anywhere; all data already flows through `getTrades`/`getDataStatus`.
