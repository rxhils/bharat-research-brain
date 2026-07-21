# /portfolio-mode — Redesign Plan

**Concept:** An editorial two-chapter explainer — emerald "Portfolio Mode" chapter, gold "Broker connection" chapter — where the pipeline paragraph becomes the page's centerpiece: a scroll-scrubbed animated beam diagram in the fey.com data-as-storytelling mode, with column.com serif editorial type replacing the current 13px flat text-wall.

**Signature moment:** Scroll-scrubbed "How a portfolio gets built" pipeline diagram: an SVG tracing beam (Magic UI Animated Beam / Aceternity Tracing Beam pattern) whose pathLength is driven by useScroll+useSpring, lighting up five stage nodes (Universe → Filters → Rank → Weights → Two clocks) as the reader scrolls, with a .brand-motion bypass since the operator machine has OS reduced-motion ON.

---

# /portfolio-mode — Redesign Plan

**Operator note first:** a PostToolUse hook flagged "session cost $450.70 / 48 files modified." This planning subagent modified zero files and did read-only work; the flag appears misattributed but surface it before further agent runs.

## 1. CONCEPT

This page explains how research becomes a portfolio — it should feel like a **premium research desk walking you through its machine**, not a FAQ. Art direction: fey.com's "data as storytelling" (cinematic reveals of the live equity curve), column.com's serif editorial confidence (big Fraunces chapter heads over plain near-black), resend.com's hairline-divider restraint. The page has a natural two-chapter structure the current design buries: an **emerald chapter** (Portfolio Mode — the live machine) and a **gold chapter** (Broker connection — the planned, read-only future). One accent per chapter, ≤3 accent elements per viewport. Kill every 13px header; the type ladder must be unambiguous top-to-bottom.

## 2. SIGNATURE MOMENT — Pipeline Tracing Beam

The pipeline paragraph (lines 116–125) becomes `components/pipeline-diagram.tsx` ("use client"). Five glass stage nodes in a vertical rail — **Universe → Strategy filters → Rank → Target weights (4/sector cap) → Two clocks (quarterly re-pick / weekly de-risk / 15% cut)** — connected by one SVG `motion.path`.

- **APIs (framer-motion 11):** `useScroll({ target: ref, offset: ["start 80%", "end 45%"] })` → `useSpring(scrollYProgress, { stiffness: 100, damping: 30 })` → bind to `pathLength` on `motion.path` with an emerald→gold `linearGradient` stroke (Aceternity Tracing Beam / Magic UI Animated Beam pattern). Each node's opacity/border lights via `useTransform(spring, [i/5, (i+1)/5], [0.35, 1])`.
- **Trigger/duration:** scroll-driven and reversible; no fixed duration. Spring gives the scrub feel.
- **Reduced-motion reality:** OS reduced-motion is ON on the operator machine. Wrap the beam in `.brand-motion` and drive it from motion values (which ignore the OS flag) — do **not** gate on `useReducedMotionSafe` for the beam itself; use it only to skip the node-glow pulse. Static fallback = fully-drawn path (initial `pathLength: 1`) if JS/hydration fails.
- Sticky-scrub variant (Aceternity Sticky Scroll Reveal, 250vh wrapper) is optional polish — ship inline-scroll first.

## 3. SECTION-BY-SECTION

All edits in `F:\trymaven\code\github-bharat-research-brain\maven-dashboard\app\portfolio-mode\page.tsx` unless noted. Reuse `Reveal`, `EASE`, `pressTap` from `components/motion.tsx`.

**Hero.** Upgrade H1 to `clamp(2.25rem, 1rem + 4vw, 4rem)` Fraunces, `tracking-[-0.02em]`, `leading-[1.02]`. Eyebrow → `font-mono text-[0.75rem] tracking-[0.08em] uppercase` (Linear technical-label). Add a thin `scaleX` scroll-progress bar (pattern #2: `useScroll` + `useSpring` fixed top, 2px emerald) in a small client component `components/scroll-progress.tsx` — this page is a long read; earn it.

**Type ladder fix (audit: 13px headers < body).** All four `h3` at `text-[13px]` → `h3 font-serif text-xl sm:text-2xl text-ink` (`clamp(1.35rem, 1rem + 1.2vw, 1.6rem)`). Section `h2`s → `clamp(1.75rem, 1rem + 2.5vw, 2.75rem)`. Body stays fixed 15–16px (don't fluid-scale body). Eyebrows above h3s in mono-caps 12px replace the current lost hierarchy.

**"One engine, many tilts" panel.** Apply the glass recipe: `bg-white/[0.05]`, gradient p-px hairline wrapper (brighter top edge, per broker-page pattern), `inset 0 1px 0 rgba(255,255,255,.12)`, radius 16. Break the paragraph's five chassis facts into a 5-item inline spec row (mono numerals, `tnum`): quality gate · graded cash sleeve · 15% stop · quarterly rebalance · interest on idle cash. Data-richness without new claims.

**"Three kinds of numbers".** Keep the 3-card grid but make cards glass with per-card accent (emerald/emerald/gold), card titles up to `text-sm font-medium`, and add one honest anchor figure per card where data exists (e.g. backtest window "2021–26" as a mono stat). Stagger-reveal (pattern #9: `whileInView`, `staggerChildren: 0.06`) via existing `Reveal`.

**Pipeline → `components/pipeline-diagram.tsx`** (signature moment, §2). The prose paragraph shrinks to a 1-sentence lede; the diagram carries the content. Two-clock stage renders as a split node (quarterly vs weekly) with the 15% cut as a rose-tinted always-on rule chip.

**"See it running".** Frame `EquityChart` in a glass card with an emerald radial glow **behind** it (Vercel gradient-as-light-source — glow bleeds from behind, not on). Add a count-up stat band above the charts (pattern #5: `useMotionValue` + `animate` + `useInView({once:true})`, `Intl.NumberFormat('en-IN')`) in `components/stat-ticker.tsx` — feed it real `acct` figures only (equity value, return since start, live-book count). Mono `tnum` numerals. Wrap tickers in `.brand-motion`.

**Style lineup (audit: content hidden in `title=` attrs).** Replace pill-with-tooltip rows with a **3×3 bento grid** (Linear pattern): each style is a small glass card showing name + its `oneLine` visibly + tier tag; tier labels become a left mono-caps column on `lg`, stacked headers on mobile. The Quant/"Enhanced F+" signature card gets a slow conic Border Beam (pattern #13, CSS-var rotation inside `.brand-motion`) plus `signature` gold tag. Cards get `pressTap` hover. New component `components/style-grid.tsx` taking `STYLE_TIERS` as props.

**Broker connection chapter.** Insert a full-width hairline divider + gold chapter eyebrow to mark the chapter switch. Keep `StatusTag`. "Design principle" panel: gold-tinted glass, and pull "Read-only. No trading." out as a `font-serif text-xl` pull-quote line — it's the trust sentence of the page. Broker chips: keep visible "(planned)" suffix (honest), upgrade to a single-row hover-pause marquee (pattern #12) only if ≥8 names; at 6, a static wrap-row with slightly larger chips is calmer — do the static row.

**Disclaimer.** Unchanged copy; add top hairline. All copy stays research-language; no new performance claims.

## 4. 3D AND DEPTH

**No WebGL.** This is a mid-funnel explainer; a 250KB R3F chunk doesn't earn its cost here (reserve the digest's R3F stack for the homepage hero if ever). Depth comes free: radial glow behind the equity-curve card, glass hairlines, 2–3% SVG noise overlay on panels, and optional CSS `perspective` tilt (≤4°, pointer-driven motion values, `.brand-motion`) on the equity-curve card only. Perf budget: **0 new dependencies**; all new client components are framer-motion-only, transform/opacity animations, lazy `whileInView` triggers. Fallback everywhere = fully-rendered static state.

## 5. IMPLEMENTATION STEPS

1. **(S)** Type-ladder pass in `page.tsx`: h1/h2/h3 clamps, mono eyebrows, kill 13px headers. Pure Tailwind, zero tsc risk.
2. **(S)** Glass recipe + chapter divider + gold pull-quote. Tailwind only.
3. **(M)** `components/style-grid.tsx` bento grid; move `STYLE_TIERS` render out of `page.tsx`; delete `title=` tooltips. Verify server→client prop serialization (plain JSON — safe).
4. **(L)** `components/pipeline-diagram.tsx` tracing beam. Flag: `useScroll` ref typing under strict TS (`RefObject<HTMLElement>`), run `npx tsc --noEmit`; keep SVG inline (no bundle risk).
5. **(M)** `components/stat-ticker.tsx` count-up band wired to `acct`; `.brand-motion` wrapper; en-IN formatting.
6. **(S)** `components/scroll-progress.tsx` top bar.
7. **(S)** Border Beam on Quant card (CSS conic + keyframes inside `.brand-motion`; no JS).
8. **(S)** Verify on localhost with OS reduced-motion ON (operator reality) and at 375px width; then `npx tsc --noEmit` gate. Per deploy-safety rule: no commit/push without explicit approval.

Bundle risk: only framer-motion (already shipped) — new client components add ~3–5KB. No step relies on `next build`.
