# /portfolio-mode — B+

**Verdict:** The two-chapter editorial structure, honest empty-state, and scroll-scrubbed pipeline beam are genuinely well-built — this is the strongest information architecture on the site. But it stops one polish pass short of exceptional: SSR leaks ₹0/+0.0% placeholder figures on a page whose whole thesis is numeric honesty, the beam's second act (the fork) breaks its own one-motion-value rule, and the lineup/number cards shipped as flat minimum-viable versions of what the plan specified.

**Skipped plan items:** (1) stat-ticker.tsx never built — CountUp inlined instead (acceptable, but no en-IN grouped formatting band as planned); (2) "Three kinds of numbers" cards shipped flat (bg-white/[0.03], all-emerald) instead of the planned glass recipe with per-card emerald/emerald/gold accents; (3) pressTap hover on style cards dropped — only a border-color transition remains; (4) pipeline beam gradient is emerald→emerald (#10b981→#34d399), not the planned emerald→gold stroke; (5) fork/branch beam uses time-based PathDraw (duration:1) instead of the shared scroll MotionValue, contradicting both the plan and the file's own header comment; (6) Border Beam on the signature card was deliberately moved OUT of .brand-motion (freezes under OS reduced motion — matches house law, contradicts plan; on the operator's reduced-motion machine it is invisible); (7) optional sticky-scrub variant and equity-card perspective tilt skipped (explicitly allowed).

## Ranked fixes

### 1. [high/M] Fix CountUp SSR/pre-hydration state: render the real final value server-side (or set initial motion value to the target and animate only after useInView fires client-side), so no-JS, crawler, and first-paint output shows the true book value instead of '₹0' and '+0.0%'. The live fetch of the page returned '₹0 since 22 Jun 2026, +0.0%' — a fabricated-looking zero on the 'Proof first' panel.

_Where:_ components/motion.tsx (CountUp) + app/portfolio-mode/page.tsx:151-171

### 2. [high/M] Drive the fork section from the same scrub MotionValue as the rail: replace the duration-based PathDraw exit curve and add useTransform-staggered opacity on the three BranchCards keyed to the final 15% of the scrub range (extend offset to ['start 0.85','end 0.35']). Also switch the beam gradient's end stop to gold (#c9a961) as planned, so the signature moment carries the page's emerald-to-gold arc.

_Where:_ components/portfolio-mode/pipeline-diagram.tsx:124, 138-141, 165-197

### 3. [high/M] Add a truthful status chip per style card — 'Live paper — since 22 Jun 2026' on Enhanced F+ (from acct.inceptionDate, passed as a prop), 'Backtested 2021-26' or 'Planned' on the rest, matching what /strategies actually shows. The copy says 'Not every style is live yet' but the grid never says which, leaving nine identical cards with zero data. Restore pressTap hover while in the file.

_Where:_ components/portfolio-mode/style-grid.tsx:27-44 + app/portfolio-mode/page.tsx:41-57, 319

### 4. [med/S] Enforce the gold budget: gold currently appears in StatusTag, chapter divider, gold eyebrow, GRAD_GOLD h2, gold glow panel, and the Signature tag (~6 uses vs max 2). Keep gold for the Broker h2 gradient and the glow panel only; make the divider a neutral hairline, StatusTag border-dim, eyebrow tone default, and the Signature tag emerald.

_Where:_ app/portfolio-mode/page.tsx:72, 328-339 + components/portfolio-mode/style-grid.tsx:37

### 5. [med/S] Upgrade the 'Three kinds of numbers' cards to the plan's spec: gradient p-px hairline glass wrappers (GlassPanel or the broker-page recipe), distinct accent per card, and slightly larger mono anchor figures ('2021-26', 'since 22 Jun 2026') pulled up to stat weight instead of 11px corner labels.

_Where:_ app/portfolio-mode/page.tsx:270-303

### 6. [med/S] Give the signature card a reduced-motion-visible treatment: since border-beam freezes under OS reduced motion (correct per house law), add a static gold-tinted p-px gradient border as its frozen state so the flagship card still reads as special without animation — right now it likely differs only by a 5% emerald tint on the operator's own machine.

_Where:_ components/portfolio-mode/style-grid.tsx:30-34 + globals.css (.border-beam frozen state)

### 7. [med/S] Replace the two bare text-xs hover:underline links ('See every live book in full', 'See backtested figures') with the site's arrow-slide link affordance (translate-x on the arrow, hairline underline grow) — page-end momentum currently dies on the two most important internal CTAs.

_Where:_ app/portfolio-mode/page.tsx:187-189, 321-323

