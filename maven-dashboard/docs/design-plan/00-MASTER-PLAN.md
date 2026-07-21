# Master Plan

# trymaven.in Master Redesign Plan — Design Director Consolidation

**Operational flag first:** three research subagents independently reported a PostToolUse hook claiming "session cost $450.70 / 48 files modified." All were read-only passes that modified zero files — the flag looks misattributed, but verify hook accounting before launching implementation agents.

---

## 1. STACK DECISION

**Motion stack: framer-motion 11 (already shipped). Zero new motion dependencies.** All imports from `"framer-motion"`, never `"motion/react"`. Every plan's signature moment is achievable with `useScroll`, `useSpring`, `useTransform`, `useMotionValue`, `animate()`, `motion.path` pathLength, and `layoutId`.

**WebGL: exactly one canvas on the whole site — the /broker hero particle field.** Pinned (React 18.3-compatible; fiber v9/drei v10 require React 19 — do not upgrade):

- `@react-three/fiber@8.18.0`
- `@react-three/drei@9.122.0`
- `three@0.169.0`
- `maath@0.10.8`
- `r3f-perf@7.2.3` (devDependency only)

Loaded via `next/dynamic` `{ ssr: false, loading: () => null }`, mounted only behind `lg:` viewport + `hardwareConcurrency > 4` + hero in-view gates; fallback is the existing aurora div at 0KB. Every other page that flirted with 3D correctly ruled it out — hold that line. No Spline, no shadergradient, no Rive, no Lottie.

**Shared primitives — build once in wave 1, consume everywhere:**

| Primitive | Location | Consumers |
|---|---|---|
| `GlassPanel` | `components/glass-panel.tsx` (extract from chat-view) | all 9 pages |
| `MagneticButton` | `components/motion.tsx` | /, /login, /broker CTAs |
| `CountUp` / NumberTicker | `components/motion.tsx` (dedupe the /strategies page-local copy) | /, /portfolio, /portfolio-mode, /trades, /strategies, /backtest |
| `PathDraw` (motion.path pathLength + gradient fill + endpoint dot) | `components/motion.tsx` | /trades sparklines, /portfolio race, /strategies map, /login DraftStudy, beams |
| `useScrollScrub` (useScroll→useSpring wrapper, house stiffness 100/damping 30) | `components/motion.tsx` | /, /portfolio-mode, /backtest, /broker |
| `ScrollProgress` (2px top bar) | `components/scroll-progress.tsx` | /, /portfolio-mode |
| `LayoutPill` (layoutId active indicator, spring 420/34) | `components/motion.tsx` | /portfolio tabs, /trades filters, /chat sidebar rail, /broker outcomes |
| `SectionEyebrow` (mono caps 11px, tracking +0.08em) | `components/motion.tsx` or tiny component | all 9 |
| `NoiseOverlay` (2% feTurbulence data-URI) | globals CSS class | hero/glass surfaces |
| BorderBeam conic keyframes | `globals.css` | /strategies flagship, /broker trust band, / Quant card |
| `Hero3D` wrapper (dynamic import + capability gate + fallback) | `components/broker/constellation-field.tsx` | /broker only |

---

## 2. DESIGN-SYSTEM MOVES (cross-page law)

**Type ladder (identical everywhere):**
- Hero H1: Fraunces, `clamp(2.25rem, 1rem + 4.5vw, 5rem)` (homepage may reach 5.5rem), `tracking-[-0.02em]`, `leading-[0.98–1.05]`
- Section H2: `clamp(1.75rem, 1rem + 2.5vw, 3rem)` serif
- H3: `clamp(1.35rem, 1rem + 1.2vw, 1.6rem)` — **no 13px headers anywhere** (kills the /portfolio-mode inversion)
- Eyebrows: fixed 11px mono caps, tracking +0.08–0.2em
- Body: fixed 15–16px, never fluid (zoom accessibility)
- Every numeral: `font-mono tnum`, `Intl.NumberFormat('en-IN')`

**Accent discipline:** ≤3 accent elements per viewport. **Emerald = performance/return/live motion. Gold-soft = risk survived, flagship seal, premium punctuation — max 2 uses per page** (Robinhood Gold rule). Rose/amber only for negatives. Benchmark lines always dim slate.

**Glass recipe (the only card treatment):** `bg-white/[0.04–0.06]` + `backdrop-blur-[14px] saturate-[1.7]` + gradient p-px hairline wrapper (brighter top edge, /broker pattern) + `inset 0 1px 0 rgba(255,255,255,.12)` + radius 16–20px + optional 2% noise. **Cap ~6 backdrop-filtered elements per page.** Depth = radial glow *behind* objects (Vercel light-source trick), never on them. Hairline dividers over card borders elsewhere.

**One signature moment per page, and only one.** Each page gets its named beat (Fall Scrubbed, Medallion Ignition, The Race, Pipeline Beam, The Tape, RiskReturnMap, Crash Scrubbed, Draft Study, 3D Constellation). Everything else is `Reveal` staggers (staggerChildren 0.06) or nothing. Delete competing loops (/login loses 5 of 6; homepage loses SnakeScrollLine + EngineCore).

**Reduced-motion policy (operator machine has OS RM ON):** signature moments are driven by raw motion values / `animate()` inside `.brand-motion` — they must play. Decorative loops (border beams, marquees, pulses) respect `motion-reduce`/`useReducedMotionSafe`. Every signature ships a static fully-rendered fallback for JS-off/SSR.

**Copy law:** research language only — never buy/sell/tip/guaranteed/sure-shot/recommendation ("Entry thesis"/"Exit trigger" on /trades). No fabricated data ever: no decorative fake sparklines, honest omission when a stat is unavailable, all backtest figures verbatim with "backtested, not a live track record" captions.

---

## 3. ROLLOUT ORDER

**Wave 0 — instant fixes (ship today, <1 hour):**
1. **/strategies factual bug:** "Two strategies are live" headline over three cards — derive from `LIVE.length`.
2. **/portfolio factual bug:** all three EquityCharts hardcode "Enhanced F+" + emerald (`client.tsx:206-207`) — add `seriesName`/`color` props, grep all call sites.
3. /trades copy-rule violations: "Why it was bought/sold" → "Entry thesis"/"Exit trigger".
4. Homepage double-H1 check.
Run `npx tsc --noEmit` after each.

**Wave 1 — foundations + front door (highest traffic-per-effort):** Build all shared primitives above, then **/** (homepage: Fall Scrubbed, hero device tilt, deletions) and **/login** (loop purge, DraftStudy, mobile CTA-above-fold fix). Rationale: these two pages are every visitor's first impression, and building primitives against two real consumers hardens them for the rest.

**Wave 2 — the proof pages:** **/backtest** (Crash Scrubbed + missing equity curve — the credibility engine), **/strategies** (RiskReturnMap + pipeline rail), **/portfolio** (The Race + tabs + HoldingsTable compact fix), **/trades** (The Tape + trade-chart). Rationale: these convert skeptics; they share PathDraw/CountUp/LayoutPill heavily, so they go after primitives are proven. /backtest first — it needs the data-export step (`covid-equity.ts`, `equity-series.ts`) which is a prerequisite with its own risk.

**Wave 3 — explainers + the 3D flagship:** **/portfolio-mode** (pipeline beam, type-ladder fix), **/chat** (Medallion Ignition, sidebar polish — app surface, lower marketing urgency), then **/broker** steps 1–6 (CSS preserve-3d depth, tracing beam, phone tilt), and **last and independently revertible: the R3F particle field** (new deps, biggest tsc/bundle risk, purely additive).

---

## 4. SEO MASTER CHECKLIST

**Already done locally (uncommitted — verify on localhost, then get explicit deploy approval):** `layout.tsx` with metadataBase, canonical "/", title template "Maven — AI Research for Indian Markets | TryMaven", OG + twitter blocks, robots meta, Organization+WebSite JSON-LD with alternateName/sameAs; `robots.ts` (allow all, disallow /auth/); `sitemap.ts` (9 routes).

**Fix before deploying that layer:**
1. OG image: replace the 1320×2868 phone screenshot with a proper 1200×630 landscape card; `twitter:card` = `summary_large_image`.
2. Prune sitemap to truly public pages — drop auth-gated /portfolio, /trades, /broker (app), /backtest-if-gated, /login.
3. Pin real `lastModified` dates (kill `new Date()` false freshness).
4. `robots: { index: false }` on /login metadata.

**Then, in order:** (5) per-page `generateMetadata` (unique title/description/canonical) for every public route — fold into each wave's page work; (6) Google Search Console domain property (DNS TXT) + submit sitemap + Request Indexing on public pages; Bing Webmaster too; (7) brand entity: X/Instagram bios link back, consistent "Maven (TryMaven)" naming; (8) content lever: indexable /learn section (drawdown protection, FII/DII flows, bhavcopy reading, survivorship bias, methodology pages) with Article JSON-LD — targets winnable mid-tail ("ai research indian stocks"); (9) backlinks: Product Hunt, Peerlist, GitHub org, Indie Hackers, BetaList, genuine Indian-fintech community participation — 10–15 real referring domains wins all brand queries; (10) CWV pass after the redesign (lazy below-fold, LCP hero H1 unblocked, CLS 0). Expect brand queries #1 in 2–6 weeks post-GSC; mid-tail 3–6 months.

---

## 5. RISKS

- **Build gate:** `npx tsc --noEmit` is the ONLY gate — `next build` is broken on this box; no step may depend on it. Known tsc hotspots: `useMotionValueEvent`/`animate` imports, strict SVG `motion.path` typings, `useScroll` ref types, the EquityChart prop-signature change (touches other pages — grep first), three.js types in wave 3.
- **Bundle:** waves 0–2 add ~0KB deps (~25KB first-party components total). R3F chunk must stay lazy and ≤250KB gz, never in route-initial JS; verify chunk splitting, keep first-load ≤130KB. Revert plan: the field is one dynamic import.
- **Reduced-motion:** operator machine has OS RM ON — every signature must be manually verified playing on localhost with RM ON, and static fallbacks verified with JS disabled.
- **Perf:** transform/opacity/pathLength only; ≤6 backdrop-filters per page; SVG paths ≤120 points; single Canvas, `dpr [1,1.5]`, `frameloop="demand"`.
- **Honesty regressions:** any new visual must trace to real committed data (backtest exports cite the frozen commit); no invented stats in DraftStudy/suggestion cards — omit instead.
- **Process:** per the deploy-safety rule, every wave verifies on localhost (desktop + 375px + RM ON) and nothing is committed, pushed, or deployed without explicit per-change operator approval. Investigate the $450.70 hook flag before spawning implementation agents.
