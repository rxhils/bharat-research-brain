# cross-page — B-

**Verdict:** The token layer is genuinely unified — emerald/gold discipline, tnum mono figures, one shared motion vocabulary (EASE/PRESS/Reveal), and a nav whose gliding active pill is the best seam on the site — but the editorial grammar above the tokens fractures: section-eyebrow numbering uses three different delimiters across four pages, the serif signature appears on some H1s and not others, and /chat ships a different footer than every other page. Add a completely missing 404 page and a keyboard-invisible primary nav, and this reads as one excellent design system executed by several different editors — Awwwards jurors would feel the seams within three clicks.

**Skipped plan items:** Favicon/tab identity not flagged: icon.svg + manifest + per-page title template are correctly configured in app/layout.tsx. Mobile nav not flagged as broken — the scrollable pill rail with hidden scrollbars is a deliberate, working pattern. Glass-recipe and gold-cap budgets were spot-checked only via fetched page descriptions, not per-page DOM counts (single-page auditors cover those).

## Ranked fixes

### 1. [High — an unstyled 404 is an automatic Site-of-the-Day disqualifier and breaks the premium illusion on any mistyped URL or dead link/Low — one static page reusing existing chrome] Ship a branded not-found.tsx — dark bg, serif headline, mono '404', one emerald link home, footer disclaimer intact. Currently the server returns a bare 404 with no page at all.

_Where:_ maven-dashboard/app/not-found.tsx (file does not exist; verified via glob + live fetch of an unknown route)

### 2. [High — keyboard users get invisible focus on the single most-used surface while every deep component has rings; also an accessibility-judging criterion on Awwwards/Low — class additions only] Add focus-visible rings to the primary Nav: the tab() links, the ★ Backtest CTA, the logo link, and the two footer social icons. Use the house convention already in 20+ components: focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60.

_Where:_ components/client.tsx lines 59-124 (tab + Backtest CTA), components/site-chrome.tsx lines 31-38 (social links)

### 3. [High — this is the most visible cross-page tell that the pages were built in separate waves; one primitive makes 9 signature moments read as one editorial voice/Medium — one component plus 4 page sweeps] Unify the section-eyebrow grammar to one delimiter system sitewide. Today: home renders '01The core idea' (no separator), backtest '01 — The full period' (em-dash), broker '04Broker · Layer 4' (middot), strategies '01 — Live & validated'. Pick the em-dash form, extract an <Eyebrow n label /> primitive, and use it on all four pages.

_Where:_ home/broker/backtest/strategies page components (new shared primitive in components/motion.tsx or client.tsx)

### 4. [Medium-high — the footer is the one element on every page, and it currently changes voice mid-site while underdelivering on the editorial-premium promise/Medium] Reconcile the two footers and upgrade the shared one. /chat renders 'Educational market context…' while every other page renders 'Research tool. Not investment advice…' from site-chrome.tsx; the shared footer is also two lines + two icons with no nav echo, brand mark, or backtest/methodology links. Make chat consume SiteChrome's footer (page-specific line becomes an extra row) and add a slim link row.

_Where:_ components/site-chrome.tsx footer block (lines 21-40) + chat page footer override

### 5. [Medium-high — the serif is the brand's most distinctive typographic signature; applied inconsistently it reads as accident rather than voice/Medium — class changes on ~5 headings plus a one-line convention note] Codify the Fraunces serif rule and apply it uniformly to page-level H1s. layout.tsx comments serif is 'only on /how-it-works headlines' but /broker uses italic-serif emphasis ('Connect your broker.') while /strategies ('Models, ranked.') and /backtest ('Half the drawdown. The proof.') follow different display treatments. Rule: every page H1 = Fraunces with one italic emphasis word; everything below is Hanken.

_Where:_ app/layout.tsx comment line 11, plus H1s on /strategies, /backtest, /chat ('Ask Maven'), and the home hero

### 6. [Medium — the nav already promises continuity (layoutId pill glide); the content contradicting it with a hard cut is the biggest felt seam when actually clicking between the 9 pages/Medium — template-level motion wrapper; verify no Lenis/scroll-restore conflicts] Add a route-level content transition so pages don't hard-cut under the gliding nav pill: wrap SiteChrome's <main> in a keyed motion.div (opacity 0→1, y 8→0, 0.35s house EASE, skipped under reduced motion), matching the pill's spring timing.

_Where:_ components/site-chrome.tsx line 20 (<main>), using primitives from components/motion.tsx

### 7. [Medium — loading/empty moments are where cohesion quietly dies; one primitive keeps the honest-omission copy law visually consistent/Medium] Systematize empty/loading states into shared primitives. Chat's sidebar has a written empty state ('Your past conversations will appear here') and strategies uses deliberate 'In validation — no numbers until earned' withholding, but there is no shared skeleton/empty-state component, so each page improvises tone and treatment.

_Where:_ new components/empty-state.tsx + skeleton primitive; consumers: chat sidebar, portfolio, trades, broker pre-connect

### 8. [Low-medium — it is the first authenticated-flow impression and currently the least Maven-feeling page on the domain/Low] Give /login the brand voice: it renders intentionally bare (SiteChrome early-returns) but currently carries no serif headline, no disclaimer, and no footer — the only page on the site with zero regulatory line. Add the Maven mark, a Fraunces one-liner, and the standard one-line disclaimer.

_Where:_ app/login page + components/site-chrome.tsx line 15 (the /login bypass)

