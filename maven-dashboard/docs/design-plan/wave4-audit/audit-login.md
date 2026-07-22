# /login — B+

**Verdict:** The plan was executed with real discipline — loops purged, gold capped at two, CTA above the fold, one signature draw — and the page now reads as a coherent quiet threshold rather than a billboard. What keeps it out of the A range next to Linear/Stripe is that the centerpiece artifact is a fake-shaped chart wearing an apology label while the real backtest figures sit inert beneath it, the CTA never became the "pool of light" the concept promised, and the demoted film tile plus a mislabeled "drawdown study" callout leave visible seams.

**Skipped plan items:** 1) Shared MagneticButton in components/motion.tsx was skipped — implemented locally in GoogleSignInCard (documented: focus-ref forwarding). 2) components/auth/DraftStudy.tsx as its own file skipped — inlined in AuthQuotePanel (documented: wave file-ownership). 3) Planned manifest rows ("Saved threads · synced / Broker sync · read-only / Mode · paper-traded") replaced with verbatim backtest figures — an upgrade, not watered down. 4) Plan's chained animate().then() sequencing for the gold callout replaced by a brittle hardcoded whileInView delay of 2.5s. 5) "Delete five of six loops" missed one: GateFilm's branded cover still runs an animate-gate-sweep loop (GateFilm.tsx:82), plus the looping video itself survives as a tile. 6) The concept's "one pool of light on the door (the CTA)" was never realized — the idle button is dark gray with no luminous treatment; the brightest object on the page is the right-panel artifact. 7) Sitemap pruning of /login deferred as planned (flagged out of scope).

## Ranked fixes

### 1. [high/M] Replace the hardcoded illustrative STUDY_D path with a real path derived from the frozen backtest equity export already quoted in the manifest (+129.97% / 14.05% DD): downsample the equity series to ~28 points, generate the SVG d string at build time (constant, still verbatim data), keep the gold dot on the terminal value with a tnum mono callout of the actual figure. Kill the 'Illustrative research view — not live data' apology line — the artifact becomes the proof, not a prop.

_Where:_ components/auth/AuthQuotePanel.tsx:45-75

### 2. [high/S] Realize the 'pool of light on the door' concept: on the idle CTA add a soft radial emerald glow behind the button (blurred pseudo-layer, ~rgba(52,211,153,0.12)) and a top-edge hairline gradient that brightens on hover, so the CTA is the single brightest object on the page. Keep the magnetic translate; add box-shadow bloom on hover only (interaction-gated, no loop).

_Where:_ components/auth/GoogleSignInCard.tsx:154-167

### 3. [med/S] Fix the two honesty/coherence seams in the right panel: rename the callout 'drawdown study · F+ model' (the line rises — label contradicts the drawing; use 'equity study · F+ model' or bind to fix #1's real series), and replace the static 'Live · NSE / BSE' pill with a truthful neutral label ('NSE / BSE coverage') or a session-aware state — a hardcoded 'Live' dot at 2am is a small lie on a page built on honesty.

_Where:_ components/auth/AuthQuotePanel.tsx:66-70 and 144-147

### 4. [med/S] Resolve the orphaned film tile: either fold GateFilm into the glass artifact as a bottom strip inside GlassPanel (one composed object, not three stacked ones) or cut it from /login entirely; while there, delete the animate-gate-sweep loop inside GateFilm's cover — it is the sixth loop the purge missed.

_Where:_ components/auth/AuthQuotePanel.tsx:183-185 and components/auth/GateFilm.tsx:81-83

### 5. [med/M] Give mobile the signature moment: render a compact DraftStudy (same PathDraw, 0.9s, no manifest) inside the mobile quote card in place of the plain text block — currently phones get zero motion identity and the page's only living object is desktop-gated behind min-[880px].

_Where:_ components/auth/GoogleSignInCard.tsx:229-237

### 6. [med/S] Replace the whileInView + hardcoded 2.5s delay on the gold callout with completion-chained sequencing (PathDraw onComplete callback or animate().then()), so the annotation lands exactly when the draw ends at any duration and doesn't mis-fire if the panel mounts off-viewport.

_Where:_ components/auth/AuthQuotePanel.tsx:66-70

### 7. [med/S] Raise the H1 to true editorial scale and stop echoing the wordmark: bump clamp ceiling to ~3.6rem (plan's own 60px+ digest guidance) and swap 'Welcome to Maven' — which repeats 'Maven' twice within 60px of the lockup — for a threshold line in research language (e.g. 'Your research desk, after hours.').

_Where:_ components/auth/GoogleSignInCard.tsx:143-148

