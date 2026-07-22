# / — B+

**Verdict:** The overhaul genuinely lands its concept — the sticky 3D "Fall, Scrubbed" drawdown proof is a real signature moment with structurally-desync-proof counters, the hero leads with product, and the honesty copy is exemplary — but the page still ships crawler-visible "+0.00%" hero stats, a 9-card strategy text-wall with no visual differentiation, and slow hero choreography that Linear/Stripe would never tolerate. It is a strong A- system executed to B+ finish; the gap is polish density, not concept.

**Skipped plan items:** (1) Plan §2 keyboard/no-JS fallback promised "a static fully-drawn SVG renders beneath (server-renderable)" — shipped only as faint 0.22–0.30-opacity ghost tracks on the back plane, and both counter tiles read "0%" with JS off, so the page's central proof is nearly invisible to crawlers/no-JS. (2) Plan §3 layer connector was spec'd as a Magic-UI-style animated beam between layers — shipped as a timid 72px vertical stub (LayerBeam) that reads as a divider, not a connector. (3) Plan §3 "single-H1 check" on LandingAuthFlow is unverifiable from the shipped files and page.tsx carries no comment confirming it was done. (4) Plan §3 said validation "live" checklist items get font-mono tnum where numeric — items got a `tnum` class but stayed in the sans face with no numerals present. (5) Scrub height was quietly reduced 300vh→240vh (180vh mobile) — acceptable, but a deviation. Everything else (SnakeScrollLine/EngineCore deletion, HeroDeviceTilt, layer-2 Balanced mock swap, magnetic CTA, glass recipe, border-beam, metadata title) shipped as planned.

## Ranked fixes

### 1. [high/S] Server-render the real hero figures. CountUp currently hydrates from 0, so crawlers, no-JS, and the LCP frame show '+0.00% Enhanced F+ vs +0.00% Nifty 500' — the page's headline claim rendered as zero (confirmed in live WebFetch). Render the final strings ('+129.97%','+82.17%') in the SSR HTML and have CountUp read/animate from the existing textContent instead of 0. Apply the same to the honest-claim panel's inline CountUps (14.05/18.59).

_Where:_ components/explainer.tsx:1294-1296 (hero GlassPanel) and :1511 (honest claim); root cause in components/motion.tsx CountUp

### 2. [high/M] Break the 9-card strategy text-wall. Three tiers of visually identical how/looks/bestFor paragraphs carry the same weight as the Quant signature card and read at ~600 words. Collapse 'How it works' + 'What it looks for' behind a hover/tap disclosure (or show only oneLine + bestFor by default), and give each card one mono-tnum differentiator glyph/metric row so the eye can scan the grid. Keep all copy verbatim — this is layout, not rewriting.

_Where:_ components/explainer.tsx:1416-1458 (STRAT_TIERS render), data at :496-539

### 3. [med/S] Compress hero choreography and kill the infinite chevron bob. CTA appears at ~1.2s behind a 0.6→0.95→1.2s delay chain — Linear resolves its hero in <700ms. Cut delays roughly in half (0.3/0.5/0.65) and replace the repeat:Infinity chevron y-loop with a hover-only nudge (group-hover:translate-y) — it is a decorative loop that never freezes for non-reduced users, off-system next to the page's otherwise disciplined 'loops freeze' stance.

_Where:_ components/explainer.tsx:1288-1313

### 4. [med/S] Deliver the promised no-JS/crawler drawdown fallback: raise the back-plane static tracks to full-strength strokes with the two trough labels ('Market −38%','Enhanced F+ −13.88%') server-rendered as HTML, then dim/hide them on hydration (a mounted-state class). Right now the signature proof is a near-empty grid plus '0%' tiles for anyone without scroll-driven JS — the plan explicitly required a fully-drawn static SVG beneath.

_Where:_ components/explainer.tsx:912-932 (back plane) and :994-1003 (counter tiles)

### 5. [med/S] Either commit to the layer connector beam or delete it. The 72px LayerBeam stub reads as an accidental divider. Make it span the full gap between layer rows (measure with a ref, ~200-300px), draw with scroll as designed, and land in the next layer's '0n' numeral so the four layers read as one pipeline — or remove it and let the gap breathe. Half-measures are the tell between good and exceptional.

_Where:_ components/explainer.tsx:1231-1252, mounted at :1380-1388

### 6. [med/M] Fix mock legibility at small sizes: the phone screens use 5-6px type that turns to noise in the 100px gallery frames (Stable/Bold, Brokers/Sign-in) and on 375px viewports. Bump small-gallery width to ~140px mobile / 170px sm, and inside gallery screens drop the lowest-value rows (e.g. the α/holdings 5px line) so what remains is readable rather than a blur of grey.

_Where:_ components/explainer.tsx:723-765 (Device w classes) and PortfoliosScreen/BrokerListScreen text sizes :424-485,:664-681

### 7. [med/S] Restore section-numbering cohesion: sections run Eyebrow 01 (Core idea), 02 (Four layers), 03 (Why trust it), 04 (Live & forward), but 'Portfolio strategies' between 02 and 03 uses a bare gold <p> label with no index — the one break in an otherwise strict editorial system. Use <Eyebrow index='03'>Portfolio strategies</Eyebrow> and renumber the following two to 04/05.

_Where:_ components/explainer.tsx:1407 (plain label) vs Eyebrow at :1327,1376,1490,1532

### 8. [med/S] Close the plan's open single-H1 verification: confirm LandingAuthFlow renders no second <h1> alongside the explainer's 'Beats the market.' h1 (view-source or grep components/auth/landing-auth-flow.tsx); if it does, demote the tag only. Duplicate H1s undercut the SEO intent of the new absolute title.

_Where:_ components/auth/landing-auth-flow.tsx (verify) vs components/explainer.tsx:1279

