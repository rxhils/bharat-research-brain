# /portfolio — Redesign Plan

**Concept:** A live trading-desk triptych: three paper books racing one benchmark, presented like a Fey-style editorial performance page — near-black canvas, serif display headline, one normalized race chart as the centerpiece, and each book given its own honest color identity instead of the current copy-pasted emerald.

**Signature moment:** "The Race" — a full-width custom SVG chart normalizing all three books + Nifty 500 TRI to % return since inception; each line draws left-to-right via motion.path pathLength (staggered 0/0.25/0.5s, 1.6s, EASE) with a glowing tracer dot riding each path head, then terminal return labels count up via useMotionValue+animate. Wrapped in .brand-motion so it plays on the operator's reduced-motion machine.

---

# /portfolio Redesign Plan

Repo: `F:\trymaven\code\github-bharat-research-brain\maven-dashboard`. Confirmed audit bugs resolved: hardcoded "Enhanced F+"/emerald on all three EquityCharts (client.tsx:206-207), `min-w-[640px]` HoldingsTable inside ~380px xl grid columns (client.tsx:333), no hero / no signature motion.

## 1. CONCEPT
The performance page of a premium research desk — Fey's "data as storytelling" on Maven's near-black. Today the page is three cloned columns fighting for 380px each; the redesign makes it a narrative: one editorial serif hero states the experiment ("three books, one risk engine, ₹10L each, paper"), one signature race chart shows all three books against the Nifty 500 TRI on equal footing, then a tabbed full-width detail desk per book. Each book earns a color identity: Enhanced F+ = emerald `#34d399`, Defensive = emerald-deep `#10b981`, Concentrated = gold-soft `#c9a961`; benchmark stays `#5a616a`. Accent discipline per resend/vercel: ≤3 accent elements per viewport. All copy stays research-honest — "paper-traded", "research tool", never advisory words.

## 2. SIGNATURE MOMENT — "The Race"
New `components/portfolio-race.tsx` (`"use client"`). Server page passes `{name, color, curve}` for all three books; component normalizes every `EquityPoint` series to % return since inception and renders one hand-built SVG (viewBox 0 0 800 300, no Recharts — full control of path draw).

- Library/APIs: framer-motion 11 — `motion.path` with `initial={{ pathLength: 0 }}`, `animate={{ pathLength: 1 }}`, `transition={{ duration: 1.6, ease: EASE, delay: i * 0.25 }}` (Aceternity Tracing Beam / Magic UI Animated Beam pattern). Tracer dot: a `motion.circle` following each head via `useMotionValue` progress + `getPointAtLength` in `useAnimationFrame` fallback — simplest robust version: animate a shared MotionValue 0→1 with `animate()` and derive cx/cy per line via `useTransform` over precomputed point arrays. Terminal % labels count up with `useMotionValue(0)` + `animate(mv, target, { duration: 1.2, ease: "easeOut" })` rendered through `useTransform` (Magic UI Number Ticker pattern).
- Trigger: `useInView({ once: true, amount: 0.3 })` on mount into view.
- Reduced motion: wrap the SVG in `className="brand-motion"` and drive everything with MotionValues/`animate()` (JS-driven, ignores OS pref) — required because the operator machine has reduced-motion ON. Still respect `useReducedMotionSafe()` for the tracer dots only (skip dots, keep draw) as a taste valve.
- Depth: radial emerald glow (`bg-[radial-gradient(...)]` 6% opacity) behind the chart, gradient p-px glass border per the /broker recipe, hover legend chips that dim other lines via opacity state.

## 3. SECTION-BY-SECTION
**A. Hero** — modify `app/portfolio/page.tsx`. Eyebrow: mono caps 11px, tracking +0.08em, `text-dim`: "PAPER PORTFOLIOS · LIVE". H1 `font-serif`, `clamp(2.25rem, 1rem + 4.5vw, 4.25rem)`, tracking -0.02em, line-height 1.02: "Three books. One risk engine." Sub-paragraph keeps existing strategy copy (already honest). Right-aligned stat band (new `components/portfolio-hero-stats.tsx`, client): combined current equity, combined return %, best max-drawdown — each count-up on view (same Number Ticker pattern, `.brand-motion`), `font-mono tnum`, glass card with `inset 0 1px 0 rgba(255,255,255,.15)` top highlight + hairline gradient border.

**B. The Race** — signature section above the fold, full width (§2). Sub-caption cites data honestly: "Normalized to % return since each book's inception · paper-traded · Nifty 500 TRI benchmark."

**C. Book desk (replaces the 3-column grid)** — new `components/portfolio-tabs.tsx` (client). Tab bar of three book pills using `layoutId="book-active-pill"` shared-layout glide (identical spring to Nav's `nav-active-pill`: stiffness 420, damping 34) — Linear/Clerk pattern from the digest. Active tab colored by book accent. Panel content is the existing `PortfolioPanel` composition made **full width**: header card (equity + alpha), then a 2-col lg grid of EquityChart (span 2) / ExposureGauge + Key stats, then HoldingsTable. `AnimatePresence mode="wait"` cross-fade 0.25s between books, gated by `useReducedMotionSafe`.

**Bug fixes in `components/client.tsx`:**
1. `EquityChart` gains props `{ seriesName: string; color?: string }`; line 207 becomes `name={seriesName} stroke={color ?? "#34d399"}`. Callers on /portfolio pass `displayName(name)` + book color. Other call sites (home) keep working via the default — check with Grep before shipping.
2. `HoldingsTable` gains `compact?: boolean`: compact drops Name/Sector/Entry columns and `min-w`, keeping Ticker/Weight/Current/P&L with `min-w-0`. Full-width desk layout uses the full table on `lg:` and compact below — solves the 640px-in-380px scroll trap and mobile.

**D. Footer disclaimer** — keep existing line; add engine-version + "read-only broker sync" microcopy in `text-dim`.

Type scale: section H2 `clamp(1.5rem, 1rem + 1.5vw, 2.25rem)` serif; body fixed 15px (no fluid body, per OddBird zoom-accessibility guidance); numbers always `font-mono tnum`.

## 4. 3D AND DEPTH
No WebGL. This is a data-truth page; a shader orb would undermine credibility and the R3F chunk (~250KB gz) buys nothing a drawn SVG race doesn't. Depth budget: CSS only — radial glow behind hero chart, glass gradient p-px borders on hero stats + active book panel, 2% SVG-noise overlay on the hero band (data-URI feTurbulence per the Superdesign recipe), `hover:-translate-y-0.5` already on Card. Zero new dependencies; bundle delta ≈ +6-8KB of component code.

## 5. IMPLEMENTATION STEPS
1. **S** — Fix `EquityChart` props (`seriesName`, `color`) + update all call sites (Grep `EquityChart` first). *tsc risk: prop signature change touches other pages.*
2. **S** — Add `compact` prop to `HoldingsTable`; remove forced min-width in compact mode.
3. **M** — Build `components/portfolio-race.tsx`: normalization util, motion.path draw, tracer MotionValues, count-up labels, `.brand-motion`, legend chips.
4. **M** — Build `components/portfolio-tabs.tsx` with layoutId pill + AnimatePresence panel swap; move `PortfolioPanel` markup into it (client component receives serialized panel data — ensure types in `lib/types` are JSON-safe).
5. **S** — Build `components/portfolio-hero-stats.tsx` count-up band.
6. **M** — Rewrite `app/portfolio/page.tsx`: hero, race, tabs, disclaimer; delete 3-col grid.
7. **S** — Verify: `npx tsc --noEmit` (the only gate — next build is broken on this box), then localhost visual pass on mobile/desktop widths. *Do not commit/push/deploy without explicit operator approval (trymaven deploy safety rule).*

No auth or API changes. No new packages. All copy research-language only.
