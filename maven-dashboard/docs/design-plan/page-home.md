# / — Redesign Plan

**Concept:** A dark editorial research desk that opens on the product and proves one claim — "half the fall" — with a single scroll-scrubbed drawdown sequence. Fey-style data storytelling, Linear-style discipline: one signature animation, everything else hairlines, glass, and restraint.

**Signature moment:** "The Fall, Scrubbed" — a sticky 300vh scroll-scrubbed covid drawdown proof: as the visitor scrolls, the market line carves down to −38% while Enhanced F+ traces its shallower −13.88% path in emerald, counters ticking in lockstep with scroll position, gap band filling last. Driven by raw useScroll motion values inside a .brand-motion container so it plays on the operator's reduced-motion machine.

---

# Redesign plan — trymaven.in / (homepage)

**Operational note first:** PostToolUse hooks report session cost **$450.70** and 48 files modified this session. This planning agent modified zero files; flag looks misattributed but the operator should verify before further agent runs.

Files: `maven-dashboard/app/page.tsx`, `maven-dashboard/components/explainer.tsx` (1293 lines, all sections inline).

## 1. CONCEPT
The page should feel like fey.com run by a Mint editorial desk: near-black canvas, Fraunces serif at extreme contrast, one emerald claim per viewport, gold only as punctuation. Today the page argues with itself — SnakeScrollLine, EngineCore rings, and DrawdownChart all compete, and the hero leads with abstract rings instead of the product. The redesign is subtractive: the product (live phone mock) owns the hero, the drawdown proof becomes the page's single cinematic beat, and everything else drops to quiet Reveal staggers. "Linear meets a premium research desk" — data as the drama, not ornament.

## 2. SIGNATURE MOMENT — "The Fall, Scrubbed"
Promote `DrawdownChart` from an inView one-shot into a sticky scroll-scrub proof (Aceternity "Sticky Scroll Reveal" + "Tracing Beam" patterns from the motion digest).
- **New file** `components/drawdown-scrub.tsx` ("use client"). 300vh wrapper `ref`; sticky child `top-0 h-screen grid place-items-center`.
- `const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] })` → `useSpring(scrollYProgress, { stiffness: 100, damping: 30 })`.
- Market path: `useTransform(spring, [0.05, 0.55], [0, 1])` → `style={{ pathLength }}` on `motion.path` (reuse existing `smooth(mPts)` data — move the W/H/MONTHS/MARKET/FPLUS constants into this file). F+ path: `[0.25, 0.75]`. Gap band opacity: `[0.7, 0.9]` → `[0, 1]`.
- Counters: `useTransform(spring, [0.05,0.55], [0,-38])` rendered via a `motion.span` + `useMotionValueEvent` writing `toFixed(0)` (Number-Ticker pattern) — the −38% and −13.88% tiles tick with scroll, JetBrains Mono `tnum`.
- Trough marker spring lands when spring > 0.78 (`useMotionValueEvent` toggling a state; spring `{stiffness:520, damping:13}` — keep the existing payoff beat).
- **Reduced-motion reality:** scroll-scrub is user-driven, so drive it from raw motion values (never gated by `useReducedMotionSafe`) and add `className="brand-motion"` on the sticky container. Keyboard/no-scroll fallback: if `spring` never exceeds 0.1 within view (or JS off), a static fully-drawn SVG renders beneath (server-renderable) — zero-cost fallback.
- Easing: the spring is the easing; no duration constants. Total scrub distance ≈ 2 viewport heights of reading pace.

**Deletions that make it signature:** remove `SnakeScrollLine` entirely (lines ~989–1015 + its mount). Remove `EngineCore` (~813–833) from the hero. Keep `ScrollProgress` (2px bar) — it's chrome, not a competitor.

## 3. SECTION-BY-SECTION
**Hero (lines 1037–1092).** Lead with product, per audit. Left column unchanged copy-wise: keep "Beats the market. / Half the fall." at `clamp(2.5rem, 1rem + 6vw, 5.5rem)` (bump from current 4.6rem cap; tighten `tracking-[-0.025em]`, `leading-[0.98]`). Right column: replace `<EngineCore/>` with `<Device mock={<MarketModeScreen/>}/>` inside a new `HeroDeviceTilt` wrapper — CSS `perspective: 1200px`, initial `rotateX(18deg) rotateY(-6deg) scale(0.94)`, flattening via `useTransform(scrollYProgress, [0, 0.35], …)` (Linear tilt-flatten, pattern #8; motion-value-driven so it works under reduced motion, wrap in `.brand-motion`). Behind it, one radial emerald glow (Vercel "gradient-as-light-source": glow bleeds from behind the phone, never on it) + 2% SVG noise overlay to kill banding. Stat band stays; wrap the two return figures in the glass recipe: `bg-white/[0.06] backdrop-blur-[14px] saturate-[170%]`, gradient-hairline top edge, `inset 0 1px 0 rgba(255,255,255,0.15)`. CTA gains the magnetic-button treatment (SmoothUI pattern: pointer-offset → `useSpring({stiffness:400,damping:28})`, motion values so it survives reduced-motion, `.brand-motion`).

**Core idea (1095–1126).** The prose column stays; `<DrawdownChart/>` swap → `<DrawdownScrub/>` becomes the full-width sticky block below the H2 (prose above, scrub after — the reading order sets up the payoff). H2 stays `clamp(1.8rem, 1rem + 2.5vw, 3rem)`. Delete old `DrawdownChart` (858–920) after porting. Principles grid: keep, but adopt gradient p-px borders like /broker cards (wrap in `p-px bg-gradient-to-b from-white/[0.14] to-white/[0.03] rounded-xl2`).

**Four layers (1129–1149).** Fix the near-identical Layer1/Layer2 mocks: change `mainMock` (751–757) so layer 2 returns `<PortfoliosScreen variant="Balanced"/>` full-size ("Models, ranked." — visually distinct: card list + featured tile vs Ask screen); move `PortfolioAskScreen` out of use (delete ~357–439 or keep for gallery slot "Ask"). Gallery for layer 2 becomes Stable/Bold only. Add a 1.5px gold-to-emerald SVG connector beam between layers (Magic UI "Animated Beam" style, `pathLength` from per-section `useScroll` — static faint line under reduced OS setting since it's decorative, no `.brand-motion`).

**Strategies (1152–1231).** Layout keeps. Quant signature card gets a slow conic border-beam (Magic UI "Border Beam") as a CSS `@keyframes` on a pseudo-element — decorative, respects `motion-reduce:animate-none`. Type/eyebrows unchanged (already on contract: mono index + gold label).

**Validation + Live & forward (1234–1289).** Honest-claim panel: upgrade to full glass recipe + noise. The four "live" checklist items get `font-mono tnum` where numeric. No new motion — RevealGroup stagger is enough.

**Metadata (`app/page.tsx`).** Title → "Maven — AI Research for Indian Markets | TryMaven" (matches the uncommitted SEO layer; front-loads winnable brand terms per SEO digest). Verify only one `<h1>` renders — if `LandingAuthFlow` contains the second H1, demote its tag only (presentational; do not touch auth logic/flow).

## 4. 3D AND DEPTH
**No WebGL on this page.** The threeD digest's own guidance: CSS carries secondary sections, WebGL earns its ~250KB only for a hero centerpiece — and our hero centerpiece is the product mock, which CSS `perspective` renders perfectly. Depth stack (design digest): near-black base → radial glow behind phone → glass cards with gradient hairlines → 2–3% feTurbulence noise data-URI → emerald/gold accents ≤3 per viewport. Budget: zero new dependencies, zero new route JS beyond the ~4KB scrub component. Fallback: everything degrades to static SVG/static transforms; no dynamic imports needed.

## 5. IMPLEMENTATION STEPS
1. **(S)** Delete `SnakeScrollLine` + mount; delete `EngineCore` + hero usage. Run `npx tsc --noEmit`.
2. **(M)** Build `components/drawdown-scrub.tsx` (port constants + `smooth()`; useScroll/useSpring/useTransform scrub; `.brand-motion`; static fallback). *tsc risk: `useMotionValueEvent` typing — import from "framer-motion".*
3. **(S)** Swap into Core idea section; delete old `DrawdownChart`.
4. **(M)** Hero: `HeroDeviceTilt` wrapper + `Device(MarketModeScreen)` right column, glow+noise, glass stat band, bumped clamp scale.
5. **(S)** `mainMock` layer-2 swap to `PortfoliosScreen "Balanced"`; prune gallery; remove `PortfolioAskScreen` if unreferenced.
6. **(S)** Magnetic CTA via motion values (`.brand-motion`).
7. **(S)** Glass recipe + gradient p-px borders on principles/honest-claim cards; Quant border-beam keyframes in globals. *Watch: backdrop-filter over many cards — cap at ~6 glassed elements.*
8. **(S)** Layer connector beam (decorative, OS-respecting).
9. **(S)** `app/page.tsx` metadata title/description update; single-H1 check.
10. **(S)** Verify: `npx tsc --noEmit`, localhost visual pass with OS reduced-motion ON (signature must still scrub), mobile 375px pass. No deploy without operator approval per deploy-safety rule.

Copy untouched except metadata — all existing honesty language ("backtested, not a live track record", read-only) preserved verbatim.
