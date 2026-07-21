# /broker — Redesign Plan

**Concept:** A private custody vault rendered as an orbiting solar system: broker marks hold true spatial depth around the Maven medallion, data flows only inward, and every scroll beat hands off to the next section along one continuous emerald thread.

**Signature moment:** The constellation gains real z-depth (preserve-3d, per-node translateZ 40–110px) with spring pointer-parallax and a scroll-linked tilt-flatten, over a lazy R3F instanced particle drift — depth you can feel the moment the page loads and the rings shear in parallax.

---

# /broker Redesign Plan

*Repo: `F:\trymaven\code\github-bharat-research-brain\maven-dashboard`. Prior-audit JSON was unreachable (path "undefined"); findings below re-derived from code: 2D-flat constellation, beam not scroll-linked, no scroll choreography between sections, static trust band, mobile hero is a bare logo strip.*

## 1. CONCEPT
The page should feel like standing inside a small, precise orrery in a dark vault: six broker moons in real depth around the Maven medallion, light flowing strictly inward (the read-only promise as physics), and one emerald thread that the scroll pulls from hero → steps → phone → trust seal. Fey's "data as storytelling" restraint + Linear's kinetic precision; gold stays scarce (eyebrows, one gradient em per section), emerald carries motion.

## 2. SIGNATURE MOMENT — True-3D Orbital Constellation
Upgrade `Constellation` in `components/broker/broker-hero.tsx`:
- **Depth**: keep `perspective: 1100` wrapper; give the parent `transformStyle:"preserve-3d"` all the way down. Each broker tile gets `translateZ` = 40–90px (alternating by ring position); medallion at `translateZ: 110`; orbit SVG at `translateZ: 0`; aurora/grid at `translateZ: -60` with `scale 1.12` to compensate. Pointer parallax now shears layers at different rates — genuine parallax depth, not a flat tilt. Same `useMotionValue`/`useSpring` (stiffness 60, damping 18) pipeline; widen rotate range to ±8°. Motion-value pipeline ignores OS reduced-motion (operator machine has it ON) — gate the *idle* orbit spin behind `reduce`, keep pointer response always-on via the existing `.brand-motion` convention.
- **Scroll tilt-flatten** (Linear-style, motion digest pattern 8): `useScroll({target: heroRef, offset:["start start","end start"]})` → `useTransform(scrollYProgress,[0,0.6],[0,-14])` extra rotateX + `[1,0.94]` scale, piped through `useSpring`. Constellation leans back and recedes as you scroll off it.
- **R3F particle drift** (threeD digest stack, pinned): `@react-three/fiber@8.18.0`, `@react-three/drei@9.122.0`, `three@0.169.0`. New `components/broker/constellation-field.tsx`: one `<Canvas dpr={[1,1.5]} frameloop="demand">`, drei `<Points>` ~1,200 emerald/gold particles (maath random-in-sphere), slow inward radial drift, invalidate on pointer-move only. Mounted via `next/dynamic` `{ssr:false, loading:()=>null}` inside the constellation, desktop-only (`lg:` + `hardwareConcurrency>4` gate); fallback is the existing aurora div — 0KB cost when skipped. Trigger: mount on hero in-view. Durations: entrance unchanged (spring 260/20 tiles); flatten is scrub, no duration; drift 0.02 rad/s equivalent, `EASE` from `components/motion.tsx` everywhere else.

## 3. SECTION-BY-SECTION
**Hero (`broker-hero.tsx`)** — Signature moment above. Copy/type unchanged except h1 → `clamp(2.5rem, 1.6rem + 4.5vw, 4.4rem)`, letter-spacing −0.02em (design digest scale). CTA becomes `MagneticCTA` (new `components/broker/magnetic-cta.tsx`; motion digest pattern 6: pointer offset → `useMotionValue` → `useSpring({stiffness:350,damping:25})`, cap ±10px, reset on leave; reuses `pressTap`). **Mobile**: replace the flat logo strip with a horizontal marquee (pattern 12: duplicated track, CSS `x:"-50%"` linear loop under `.brand-motion`, mask-image edge fades) with the read-only shield pill centered above it.

**Grid (`broker-grid.tsx`)** — Keep glass p-px cards; add (a) hover spotlight: `onPointerMove` writes mouse coords to motion values feeding a `radial-gradient` background template (Border Beam/spotlight variant, pattern 13) on live cards only; (b) `saturate(170%)` added to the card `backdrop-blur` per design-digest glass recipe; (c) a 2% SVG-noise data-URI overlay on the section to kill banding. Stagger stays. Live cards get one-line honest data rows in mono (`font-mono tnum`, 11px): "Holdings · avg price · daily token refresh".

**Journey steps (`broker-journey.tsx`)** — Replace the fire-once `pathLength` line with a scroll-scrubbed tracing beam (Aceternity Tracing Beam, pattern 4): `useScroll` on the steps container, `scrollYProgress` → `useSpring({stiffness:100,damping:30})` → `pathLength`, plus a traveling emerald gradient stop. Each step's `Glyph` ignites (border-emerald fade-in, 0.3s `EASE`) when the beam passes its x-position — derive per-step thresholds from the same progress value via `useTransform`. Scrub works under reduced-motion (motion-value driven).

**After-you-connect + phone** — Give `PhoneMockup` the scroll-linked 3D entrance (pattern 8): initial `rotateX 22° / scale 0.92` inside a `perspective:1200` div, `useTransform(scrollYProgress,[0,0.45],[22,0])` flatten as it enters; keep `animate-floatY` idle after. Outcomes list: convert to a mini sticky-index feel — active outcome highlighted with `layoutId="outcome-pill"` emerald bar (pattern 10/11) as its row scrolls center. H2s: `clamp(1.75rem, 1.2rem + 2.4vw, 2.9rem)`.

**Trust band** — Add a slow conic-gradient border beam (Magic UI Border Beam, `.brand-motion`, 8s loop, emerald→transparent) on the rounded-3xl container; add one honest mono stat row: "Tokens AES-encrypted · SEBI-mandated daily expiry" (no invented numbers). Final CTA reuses `MagneticCTA`; disclaimer line unchanged (copy rules).

**Page (`app/broker/page.tsx`)** — Add per-page canonical + OG in `metadata` (SEO digest gap 4). No auth/API changes.

## 4. 3D AND DEPTH
Real WebGL earns its cost **only** as the hero particle field — everything else is CSS `preserve-3d`/perspective (free, GPU-composited). Budget: 3D chunk ≤250KB gz (three ~155 + fiber ~13 + tree-shaken drei), lazy, never in route-initial JS; single Canvas, `dpr [1,1.5]`, `frameloop="demand"`, <10 draw calls via one Points instance. Fallbacks: no-WebGL/low-end/mobile → existing aurora gradient (0KB); context-lost → unmount to aurora. Phone tilt, constellation depth, grid spotlight: pure CSS/motion-values, work everywhere.

## 5. IMPLEMENTATION STEPS
1. **S** — Hero type clamp, glass `saturate()`, noise overlay, grid mono data rows.
2. **S** — `MagneticCTA` component; swap both CTAs.
3. **M** — Constellation preserve-3d z-tiers + widened parallax + scroll tilt-flatten. *(tsc risk: low; verify `npx tsc --noEmit`.)*
4. **M** — Journey tracing beam scroll-scrub + glyph ignition thresholds.
5. **M** — Phone scroll tilt-flatten + outcome `layoutId` pill.
6. **S** — Trust-band border beam; mobile hero marquee.
7. **L** — R3F `constellation-field.tsx`: install pinned deps, dynamic ssr:false, capability gate, demand frameloop. **⚠ bundle-size + tsc risk** (three types are heavy; pin versions exactly per digest; confirm chunk stays lazy via build output). Ship steps 1–6 first; 7 is independently revertible.
8. **S** — Page metadata canonical/OG; run `npx tsc --noEmit`; verify on localhost before any deploy (per deploy-safety rule — no push without explicit approval).
