# /brain — D+

**Verdict:** This page is the most interesting story on the site — an agent pipeline that decides a real paper book — rendered as an undesigned admin panel: two default Card shells, eleven visually identical buttons, and a "click to explain" label doing the work a designed affordance should. The honesty (live vs offline, no fake busy agents) is A-grade; the craft is first-draft, with no display type, no signature moment, no glass, no gold, and no data hierarchy anywhere near the Linear/Stripe bar.

**Skipped plan items:** no prior plan

## Ranked fixes

### 1. [high/L] Replace the flat live-agent grid with a designed pipeline diagram: the 5 live agents as connected stages (Price Ingest → Daily Mark → Exposure/Regime → Quarterly Rebalance → F+ Scorer) with hairline connectors, numbered mono stage labels, and cadence chips ('Daily, after close' in JetBrains mono). Offline agents become a visually recessed 'research layer' band below — smaller, desaturated, clearly subordinate. This turns 11 identical cards into a hierarchy that mirrors the system's actual architecture.

_Where:_ components/agents.tsx:208-247 (AgentExplainer layout) + agents.tsx:129-184 (AgentCard variants)

### 2. [high/M] Add the page's signature motion moment: a single tracer pulse that travels the pipeline connectors on scroll-into-view, lighting each live agent's status dot in sequence and terminating at the F+ Scorer node — one pass, framer-motion 11, on .brand-motion so it plays under reduced motion; no infinite loop (keep the existing static-glow discipline). This is the 'the system runs' moment the page currently lacks entirely.

_Where:_ components/agents.tsx (new PipelineTrace component wrapping the live section, ~line 223)

### 3. [high/M] Build a real page header: Fraunces display hero at clamp(2rem,5vw,3.25rem) — e.g. 'Five agents decide. Six more are waiting.' — with a mono stat strip beneath (5 live agents / 6 offline / 25-stock book / ~500-stock universe, all figures already verbatim in the copy) in JetBrains mono tnum. The current text-2xl h1 over an 11px eyebrow gives the page no editorial scale at all; everything below it lives at 10-13px.

_Where:_ app/brain/page.tsx:27-30

### 4. [high/M] Give the 'Is it working?' chart a data-rich frame: a mono readout row above the chart (the ABReadout figures — engine vs Nifty 500 TRI values, verbatim from the backtest/paper source, with as-of date) instead of the chart floating under a one-line sub. Add the 'research agents are offline and do NOT affect picks' honesty line into this card as a styled footnote rather than a loose page-bottom paragraph.

_Where:_ app/brain/page.tsx:38-46 (readout is already fetched at line 22 but passed only into ABChart)

### 5. [med/M] Apply the house glass recipe (gradient p-px hairline + backdrop-blur) to exactly two surfaces: the pipeline section shell and the performance card — replacing the flat border-hairline bg-bg/40 look. Use gold-soft #c9a961 exactly once, on the 'Enhanced F+ Composite Scorer' node ('the actual brain') to mark the page's centerpiece; the page currently uses zero glass and zero gold, so it reads as a different, cheaper product than the rest of the shipped site.

_Where:_ app/brain/page.tsx:33-40 (Card usage) + components/agents.tsx:57-63,140 (scorer card styling)

### 6. [med/S] Kill the anti-pattern micro-details: replace the 10px 'click to explain' text with a rotating chevron affordance on the card row; remove the redundant 'live'/'offline' text badge (the status dot + section header already carry it — keep the badge only when a real run status overrides it); and animate the expanded detail with a slight y-settle so the reveal feels authored, not just height:auto.

_Where:_ components/agents.tsx:132-134,147-149,179

### 7. [med/S] Gate the 8-second /api/agents polling: fetch once on mount, and only continue polling when the response reports a running agent (board shows 'running' status); currently every visitor hammers the endpoint every 8s forever to render 'No nightly run has recorded heartbeats yet.' Also style that empty-state line as a proper mono system-status footnote rather than a bare dim paragraph.

_Where:_ components/agents.tsx:189-200,241-246

### 8. [med/M] Mobile pass: on small screens the page collapses into a single column of 11 near-identical tall cards. Collapse the offline band into one summarized disclosure row ('6 research agents — built, not in the live signal — expand') and keep the live pipeline vertical with visible connectors, so the phone reading order still tells the live-vs-offline story in one screen and a half.

_Where:_ components/agents.tsx:227-238 (grid breakpoints + offline section)

