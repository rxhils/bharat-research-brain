# /login — Redesign Plan

**Concept:** The threshold of a private research desk: one calm dark room, one door (the Google CTA), and behind frosted glass one living artifact — a self-drawing index study — instead of six flickering ornaments. Fey-grade restraint with a single champagne-gold signature on the wordmark.

**Signature moment:** "The Draft Study": in AuthQuotePanel, an SVG NSE-index line chart draws itself once via framer-motion animate() on a useMotionValue driving pathLength (motion-value approach bypasses OS reduced-motion, per the operator's brand-motion reality), 1.8s, EASE [0.22,1,0.36,1], followed by a gold-soft annotation dot + mono label settling in. Every other loop animation on the page is deleted.

---

# /login Redesign Plan — trymaven.in

Repo: `F:\trymaven\code\github-bharat-research-brain\maven-dashboard`. Files audited: `app/login/page.tsx`, `components/auth/{GoogleSignInCard,AuthQuotePanel,GateFilm,login-client}.tsx`. Confirmed findings resolved: (1) six competing loops, (2) zero gold, (3) mobile CTA below fold, (4) promised mini-chart shipped as three generic pills.

## 1. CONCEPT
The login is a threshold, not a billboard. It should feel like stepping up to a private research desk after hours: near-black room (fey.com's cinematic-data-calm), one pool of light on the door (the CTA), and behind glass exactly one living object — a chart drawing itself, proof the desk is working. Resend's three-step gray ladder (#888/#ccc/#fff on #0a0b0d) carries hierarchy; Fraunces serif does the only talking; gold appears exactly twice (Robinhood Gold discipline: metallic only on the product object and nowhere else). Stillness is the luxury signal — the current six loops read as anxiety; one deliberate motion reads as confidence.

## 2. SIGNATURE MOMENT — "The Draft Study"
The promised mini-chart, finally real, and the page's ONLY hero animation. New component `components/auth/DraftStudy.tsx` ("use client"), replacing the browser-frame film block in `AuthQuotePanel`.

- **What**: an SVG line study of a Nifty-style series (hardcoded honest-shaped path, labeled "Illustrative research view — not live data" in 9.5px mono so no stat lies), inside a glass card. Emerald `motion.path` stroke; beneath it a dimmer white/10 baseline; at the line's end a 5px gold-soft (#c9a961) annotation dot with a mono callout tag ("drawdown study · F+ model") — gold use #1.
- **How** (framer-motion 11, digest patterns #4 beam-draw + #5 count-up): `const p = useMotionValue(0)` → `style={{ pathLength: p, opacity: useTransform(p,[0,0.05],[0,1]) }}`; on mount (after a 0.5s delay so the panel's `rise` stagger lands first) call `animate(p, 1, { duration: 1.8, ease: EASE })`. Because it's a motion value driven by `animate()`, it renders regardless of the OS reduced-motion flag — this IS the `.brand-motion` surface (mirror `GateFilm`'s documented precedent). Also add the CSS class for consistency. Gold dot + tag fade in via a second `animate()` chained in the first's `.then()`, 0.4s.
- **Trigger**: once on mount, never loops. On `error`/`status==="done"` no replay — stillness after the moment.
- **Fallback**: none needed (SVG, ~0KB); if JS fails the `<path>` renders complete via a `pathLength`-less SSR default of the static stroke.

## 3. SECTION-BY-SECTION

**Motion audit — delete five of six loops.** In `GoogleSignInCard.tsx`: remove eyebrow `animate-gate-sweep` (line 96 — static emerald/40 tick instead), CTA `gateSweep` shimmer (line 136 — replace with digest pattern #6 magnetic hover: `useMotionValue` x/y from pointer offset, capped 6px, `useSpring({stiffness:400,damping:28})`, reset on leave; interaction-triggered, so OS reduced-motion is honored naturally), both `gateShimmer` gradient-text loops (lines 115, AuthQuotePanel 64 — static emerald gradient text, no animation). In `AuthQuotePanel.tsx`: remove `animate-gate-spark` on the live dot (static dot + soft box-shadow). Keep: `gate-spin` (functional loading) and done-state progress sweep (functional, aria-live). Net: one signature + two functional.

**Left panel — `GoogleSignInCard.tsx`.**
- *Mobile order fix (finding 3)*: move the action zone `motion.div` (lines 125–199) ABOVE the mobile quote block (lines 110–122) in DOM; on ≥880px keep visual order with `min-[880px]:order-*`. Shrink the mobile block: drop `GateFilm` from mobile entirely (video below a CTA on a login is weight without persuasion; saves decode + guarantees CTA in first viewport at 375×667), keep one serif line + the three chips condensed to a single caption row.
- *Type*: H1 stays serif but tighten to `clamp(2rem, 1rem + 3.5vw, 3rem)`, `leading-[1.02] tracking-[-0.02em]` (design digest 60px+ guidance). Eyebrow to mono (`font-mono text-[10px] tracking-[0.2em]`) — Linear's technical-label move. Body fixed 15px, never fluid.
- *Gold use #2*: wordmark tagline "India Market Intelligence" gets `text-[#c9a961]/80`. Nothing else on the page is gold.
- *CTA*: keep copy and state machine untouched (no auth-flow changes); wrap idle button in new `MagneticButton` in `components/motion.tsx` (S, reusable) using `pressTap`/`PRESS` helpers.

**Right panel — `AuthQuotePanel.tsx`.**
- Replace the pills row (lines 91–104, finding 4) AND the film's browser frame (74–88) with one composed glass artifact: `DraftStudy` on top, and below it a compact 2-row "desk manifest" table (mono, tnum): `Saved threads · synced`, `Broker sync · read-only`, `Mode · paper-traded` — honest, data-shaped, no advisory words. Glass recipe per digest: `bg-white/[0.06]`, `backdrop-blur-[14px] saturate(170%)`, gradient p-px hairline border (brighter top edge, the /broker pattern), `inset 0 1px 0 white/15`, 2% feTurbulence noise data-URI to kill banding.
- Keep `GateFilm` but demote it: small 16:9 tile under the manifest, no hover-scale, no chrome dots.
- Quote type: `clamp(1.6rem, 1rem + 2vw, 2.4rem)`; ghost watermark opacity 0.05 → 0.03.
- Depth: single radial emerald wash stays; add Vercel's glow-behind trick — a blurred emerald radial BEHIND the DraftStudy card so light bleeds around it, not on it.

**`app/login/page.tsx`**: add `description` + `robots: { index: false }` to metadata (SEO digest: auth pages shouldn't compete for index; also prune /login from sitemap.ts — flag for the separate SEO task, out of scope here).

## 4. 3D AND DEPTH
No WebGL. A login must render instantly and convert; the digest's own budget logic (≤250KB lazy chunk) is unjustifiable for a page whose LCP is a button. Depth comes free: layered radial glows, glass hairlines, noise overlay, and one CSS `perspective(1200px) rotateX/Y ≤2deg` pointer-parallax on the DraftStudy card (desktop pointer-fine only, spring-smoothed motion values, zero on touch). Perf budget: 0KB new deps, +~4KB component code, no layout shift (chart box has fixed aspect-ratio).

## 5. IMPLEMENTATION STEPS
1. **S** — Delete five loop animations + prune unused keyframes (`gateSweep`, `gateShimmer`, `gate-spark`) from globals. Risk: none.
2. **S** — Mobile DOM reorder in `GoogleSignInCard` (CTA above quote, drop mobile GateFilm); verify at 375×667 that CTA is fully in first viewport.
3. **M** — `MagneticButton` in `components/motion.tsx` (motion values + spring, pointer-fine gate); wrap idle CTA. Flag: new exports — run `npx tsc --noEmit`.
4. **M** — `components/auth/DraftStudy.tsx`: SVG path, motion-value pathLength draw, gold annotation, "illustrative" label, `.brand-motion` class. Flag: `animate` import from "framer-motion" (NOT motion/react) — tsc gate.
5. **M** — Recompose `AuthQuotePanel`: glass recipe card, DraftStudy + manifest rows, demoted film, glow-behind, parallax tilt.
6. **S** — Gold accents: tagline + annotation dot only; grep page for any third gold occurrence and remove.
7. **S** — Type-scale pass (clamp values above), mono eyebrows.
8. **S** — Metadata tweak in `app/login/page.tsx`; note sitemap pruning as follow-up.
9. **S** — Verify: `npx tsc --noEmit`, localhost check both breakpoints + OS reduced-motion ON (operator's machine) confirming the chart still draws. No deploy without explicit approval (deploy-safety rule).
