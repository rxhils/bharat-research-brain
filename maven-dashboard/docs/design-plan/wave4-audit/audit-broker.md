# /broker — A-

**Verdict:** The orbital-custody hero is genuinely SOTD-caliber — true preserve-3d depth, sprung pointer shear, inward-flowing beams, and a self-gated WebGL field that all encode the read-only promise as physics, with the emerald thread carrying scroll choreography cleanly through every section. What keeps it at A- is discipline, not ambition: gold appears 10+ times against a 2-use budget, the read-only message is repeated six times, mobile users never see the signature moment at all, and the page is nearly numberless below the hero.

**Skipped plan items:** Plan steps 1-6 and 8 shipped faithfully. Step 7 (R3F field) shipped but watered down in three ways: (a) frameloop="demand" with invalidate-on-pointer-move became frameloop="always" while in view — a continuous rAF loop the plan explicitly avoided; (b) drei <Points> + maath random-in-sphere dropped for raw three primitives with 800 particles instead of ~1,200 (acceptable simplification); (c) the planned "slow inward radial drift" — the read-only metaphor at the particle layer — became a flat rotation.z spin, losing the inward-flow symbolism. Also the plan's "traveling emerald gradient stop" on the tracing beam was implemented as a separate HTML glow head (a reasonable equivalent, not a skip).

## Ranked fixes

### 1. [high/M] Mobile gets no signature moment — the constellation is hidden lg:block and phones see only a logo marquee. Build a lightweight <lg variant: static SVG orbital (medallion center, 6 tiles on one ring, inward beam PathDraw entrance, no 3D/WebGL) replacing the marquee-only fallback, so the page's core idea exists on the device most Indian retail investors use.

_Where:_ components/broker/broker-hero.tsx:83 (hidden lg:block) and :270-301 (mobile block)

### 2. [high/S] Enforce the gold budget: gold-soft currently appears in 4 eyebrows, 2 GRAD_GOLD gradient ems, 4 coming-soon badges, the inner orbit ring, and the phone's split glow — ~11 uses vs the 2-use cap. Keep the hero h1 em + one GRAD_GOLD em; move eyebrows to text-dim, recolor coming-soon badges to neutral white/10 border + text-muted, drop the gold orbit ring stroke to a dim gray, remove gold from the phone glow.

_Where:_ components/broker/broker-grid.tsx:14-19,106-108,131; components/broker/broker-journey.tsx:16-21,153,191; components/broker/broker-hero.tsx:135,231

### 3. [high/S] Deduplicate the read-only message — it appears 6 times (hero shield pill, hero emerald line, hero footnote, grid footnote, step 03, trust band). Keep the hero pill + emerald line and the trust band as the closing seal; delete the hero footnote (mt-5 'Read-only. Maven can see…'), the grid footer line, and rewrite step 03's description to say something new (e.g. the OAuth handoff mechanics). Repetition reads as insecurity, not trust, at this bar.

_Where:_ components/broker/broker-hero.tsx:260-262; components/broker/broker-grid.tsx:149-151; components/broker/broker-journey.tsx:26

### 4. [med/S] Restore the plan's frameloop="demand" contract: replace the always/never toggle with frameloop="demand" plus invalidate() from the pointermove handler and a slow setInterval-free drift via invalidate on scroll/pointer only (or keep a low-frequency rAF cap). Right now the hero burns a continuous render loop the whole time it's in view on every capable desktop.

_Where:_ components/broker/constellation-field.tsx:134 (frameloop={running ? "always" : "never"})

### 5. [med/S] Kill the filler descriptions on coming-soon cards — 'Connect via Anand Rathi' under the heading 'Anand Rathi' is zero-information padding that drags the grid below the Linear bar. Either drop the desc line on soon cards entirely (tighter card, status badge carries the story) or replace with one honest differentiator per broker only where a verbatim fact exists; no invented data.

_Where:_ components/broker/broker-grid.tsx:31-34 (BROKERS descs), :90 (desc render)

### 6. [med/S] The trust band's mono stat row 'Tokens AES-encrypted · SEBI-mandated daily expiry' repeats the two sentences directly above it verbatim — cut the sentences and keep only the mono row (denser, more editorial), then give the final CTA h2 a larger closing scale (e.g. clamp(2rem,1.4rem+3vw,3.4rem)) so the page ends on a crescendo instead of a fourth same-size h2.

_Where:_ components/broker/broker-journey.tsx:246-252 (duplicate copy), :262 (final h2 clamp)

### 7. [med/M] Give the WebGL particles the planned inward radial drift: in useFrame, move each particle a few units toward center per second and respawn at the rim, instead of the current flat rotation.z spin. This is the one place the 'data flows inward' metaphor was dropped, and it's the difference between decoration and meaning at the signature layer. Keep it gated as decorative under reduced motion.

_Where:_ components/broker/constellation-field.tsx:43-54 (useFrame)

### 8. [med/S] Trim the glass budget: six backdrop-blur-md broker cards plus the hero/medallion/mobile pills put the page over the ~6-blur cap. Drop backdrop-blur from the four coming-soon cards (solid bg-panel), which both restores discipline and makes the two live cards' glass read as earned contrast.

_Where:_ components/broker/broker-grid.tsx:70 (card inner div class)

