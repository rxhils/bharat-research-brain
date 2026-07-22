# /portfolio — B+

**Verdict:** The redesign genuinely lands its concept — hand-built SVG race with honest common-window normalization, per-book color identity, layoutId tab desk, compact holdings table — and it is cohesive with the house system. But the live SSR literally renders "Combined equity ₹0 / +0.00%" to crawlers and pre-hydration paint, the race chart has zero axis labels or hover readout (a data page whose centerpiece chart cannot be read quantitatively), and the promised head-riding tracer was shipped as a static endpoint dot — the gap between good and Awwwards-exceptional is exactly these three.

**Skipped plan items:** 1) Tracer dot "riding each path head" via getPointAtLength/useAnimationFrame (plan §2) — watered down to a static endpoint dot that fades in after draw completes (motion.tsx PathDraw dot, portfolio-race.tsx:166). 2) Terminal % labels counting up AT the path ends on the chart (plan §2/§5.3) — moved into legend chips below the chart instead. 3) Dedicated components/portfolio-hero-stats.tsx glass stat cards with inset top-highlight + hairline gradient border (plan §3A) — shipped as plain inline HeroStat divs with a border-l divider, no glass. 4) Hero stat "best max-drawdown" (plan §3A) — replaced with blended alpha (defensible swap, but drawdown was the risk-first headline metric elsewhere on the site). 5) Defensive book color emerald-deep #10b981 (plan §1) — shipped as slate #94a3b8 (arguably better separation from Enhanced F+ emerald; noting the deviation). 6) Plan's "hover legend chips that dim other lines" — implemented; not skipped. Everything else (race, tabs, compact table, EquityChart props, noise, disclaimer microcopy) shipped as planned.

## Ranked fixes

### 1. [high/S] SSR/no-JS renders the hero as 'Combined equity ₹0, +0.00%, +0.00%' because CountUp initializes its text state to 0 (confirmed on the live fetch — a crawler reads a fintech page claiming ₹0 equity). Add a startAtTarget-style default to CountUp: initialize text to the formatted `to` value, and on inView snap the MotionValue to 0 then animate up (or animate from 0 only when JS has hydrated). Keeps the count-up moment, fixes SEO/first-paint honesty.

_Where:_ components/motion.tsx:91-106 (CountUp state init), consumed at app/portfolio/page.tsx:110-127

### 2. [high/M] The Race is unreadable quantitatively: no % axis labels (the 0.04-alpha guide lines are invisible and unlabeled), no hover readout. Add three tiny mono tnum SVG text labels (min%, 0%, max%) on the right gutter, and a pointer-move crosshair that shows date + each series' % at the nearest shared date (data is already on a shared date axis, so this is an index lookup, no new deps).

_Where:_ components/portfolio-race.tsx:149-170 (guides) and 141-206 (add pointer handler + readout)

### 3. [high/M] Upgrade the endpoint dot to the planned head-riding tracer: precompute per-series pixel point arrays (already have pts→xPx/yPx), drive a shared MotionValue 0→1 with animate() matching each line's duration/delay, derive cx/cy via useTransform index interpolation, add a soft glow (filter blur circle under the dot). This is the single change that moves the signature moment from 'nice draw-on' to memorable.

_Where:_ components/portfolio-race.tsx:154-169 plus components/motion.tsx:160-229 (PathDraw) or a race-local tracer

### 4. [med/S] Move the terminal % count-ups onto the chart at each line's endpoint (small mono text at endX+6,endY, colored per series, counting up after that line's draw completes) as the plan specified; keep the legend chips for focus/dimming but drop the duplicate numbers there. Ties value to line — the core of 'data as storytelling'.

_Where:_ components/portfolio-race.tsx:154-201

### 5. [med/S] Book color identity dies inside the desk: the engineVersion badge and mandate chip are hardcoded bg-emerald/10 text-emerald on all three books, so the Concentrated (gold) and Defensive (slate) panels contradict their tab/race color. Style both chips with the book color via inline style (background: `${color}1A`, color) — same trick as the tab dot.

_Where:_ components/portfolio-tabs.tsx:120-122 and 130-132

### 6. [med/S] Give the hero stat band the planned glass treatment: wrap the three HeroStats in a subtle glass card (gradient p-px hairline + inset 0 1px 0 rgba(255,255,255,.15) top highlight) instead of the bare lg:border-l divider — currently the combined figures, the page's most important numbers, have the least visual weight of anything in the hero. Stays within the ~6 glass budget (page currently uses ~2).

_Where:_ app/portfolio/page.tsx:107-129

### 7. [med/S] Live page shows a confusing exposure readout ('Cash sleeve: 47.3% · risk-off' next to Invested 47.3% / Cash 52.7%') — the gauge headline number appears to be the invested figure under a 'cash sleeve' label. Verify ExposureGauge's label-to-value binding and make the headline unambiguous (e.g. 'Invested 47.3% · Cash 52.7%').

_Where:_ components/client.tsx ExposureGauge (near line 215-290), consumed at components/portfolio-tabs.tsx:142-144

### 8. [med/S] Race chart accessibility/mobile polish: the legend chips are hover-only for isolation on touch (onMouseEnter/onFocus) — make tap toggle focus (onClick toggles setFocus), and add role=tab-independent aria-pressed so the isolate state is announced. Also the 10px date-range caption at the legend's ml-auto wraps awkwardly under 360px; let it drop to its own line below sm.

_Where:_ components/portfolio-race.tsx:173-205

