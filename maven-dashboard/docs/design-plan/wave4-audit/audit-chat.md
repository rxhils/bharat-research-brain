# /chat — B+

**Verdict:** The signature Medallion Ignition is genuinely executed and the motion discipline (single-stagger rules, compositor-only loops, reduced-motion paths) is Linear-grade, but the plan's other half — Fey-style data-as-storytelling — was quietly dropped, leaving a beautiful empty state that is numerically mute on a market-intelligence product. The gap to A is not polish, it is the missing live numbers plus a watered-down sidebar and a triple-repeated "India markets" label that dilutes the editorial restraint.

**Skipped plan items:** (1) Hero mono market status line ("NIFTY 50 · 24,315.95 · +0.42% · updated 15:30 IST") — skipped; comment at chat-view.tsx:346 says the support line is "gone by design". (2) Data-rich suggestion cards with live stat (plan §3 + step 4, lib/use-market-snapshot.ts) — skipped entirely; kicker is copy-only (chat-view.tsx:364 comment claims "no data source exists" although MarketTicker renders on the same page). (3) Sidebar date grouping TODAY/THIS WEEK/EARLIER mono headers — skipped, replaced with per-row relative timestamps (chat-sidebar.tsx:53). (4) layoutId="chat-active-rail" sliding active indicator with spring — skipped, replaced with a static hairline span (chat-sidebar.tsx:49). Everything else in the plan (brand de-dup, ignition, headline clamp, GlassPanel extraction with saturate, keyData font-mono, aurora noise, no-WebGL call) shipped as specced.

## Ranked fixes

### 1. [high/M] Build the skipped lib/use-market-snapshot.ts hook sharing MarketTicker's already-fetched data; render a real stat on each SuggestionCard (extend SUGGESTIONS with optional stat {label,value,tone}, bottom-right, font-mono tnum text-xs, emerald/rose by sign) and omit the stat entirely when the snapshot is unavailable — honest omission, no invented figures. This is the plan's core concept ('every suggestion carries a live number') and the single biggest good-to-exceptional lever.

_Where:_ components/chat-view.tsx:13-18 (SUGGESTIONS) and :355-375 (SuggestionCard); new lib/use-market-snapshot.ts; components/market-ticker.tsx (export data)

### 2. [high/S] Add the hero's one honest mono status line under the headline from the same snapshot hook (e.g. 'NIFTY 50 · <value> · <change> · updated <time> IST', font-mono tnum text-xs text-dim), replacing the deleted support line — it anchors the serif headline with data and completes the Fey reference.

_Where:_ components/chat-view.tsx:343-347 (Hero, after the h2)

### 3. [med/S] Restore the planned sidebar upgrades: group conversations under mono uppercase date headers (TODAY / THIS WEEK / EARLIER computed from updatedAt) and convert the static active hairline into a layoutId="chat-active-rail" motion.span (1px, emerald/80, spring stiffness 400 damping 34) so selection slides between rows.

_Where:_ components/chat-sidebar.tsx:41-62 (list render) and :49 (active indicator span)

### 4. [med/S] Kill the label repetition: 'India markets' appears three times in one viewport (page eyebrow at page.tsx:33, composer chip at chat-view.tsx:690-693, answer-card chip at chat-view.tsx:491). Keep only the page eyebrow; delete the composer chip and replace the answer-card chip with something informative (answerType or response timestamp in mono).

_Where:_ components/chat-view.tsx:690-693 and :491; app/chat/page.tsx:33 (keep)

### 5. [med/S] Upgrade the failure state: 'Could not reach Maven.' is a bare rose text line inside an otherwise fully glass-treated column — render it in a small GlassPanel with a mono 'CONNECTION' kicker and a Retry chip (re-invoke send with the paired user query), matching GuestLimitCard's pattern.

_Where:_ components/chat-view.tsx:250 (catch) and :275 (render branch)

### 6. [med/M] Fix the loader's frozen-terminal problem: ReasoningLoader stops at its last step after ~3s and sits static for however long the API takes; add a subtle elapsed-time mono counter (tnum) after ~4s, and crossfade loader→AnswerCard in a shared AnimatePresence container instead of the hard 600ms swap so the reveal reads as one continuous moment.

_Where:_ components/chat-view.tsx:388-418 (ReasoningLoader) and :246-248 (600ms setTimeout swap)

### 7. [med/S] Trim the empty-state blur budget: sidebar GlassPanel + 4 suggestion cards (backdrop-blur-md each) + composer = 6 blur surfaces at the cap before the model dropdown opens (7th). Drop backdrop-blur on SuggestionCard — over the aurora a solid bg-white/[0.04] with the existing inset highlight reads nearly identically and frees budget/GPU on phones.

_Where:_ components/chat-view.tsx:361 (SuggestionCard className)

