# /chat — Redesign Plan

**Concept:** The research desk answering: one brand medallion that visibly "signs" each session by drawing the Maven mark stroke-by-stroke, above a single-screen empty state where every suggestion carries a live number — Linear's restraint, Fey's data-as-storytelling, column.com's serif calm.

**Signature moment:** Medallion Ignition: the existing-but-never-fired MavenMark pathLength draw finally fires inside the Core medallion — driven by useMotionValue + animate() inside a .brand-motion wrapper so it plays even with OS reduced-motion ON — white stroke 0.9s, emerald stroke 0.8s at +0.45s, dot pop at +1.05s, then the orbit arc fades in; re-fires on every new conversation.

---

# /chat Redesign Plan — trymaven.in (audit grade B → A)

*All paths relative to `F:\trymaven\code\github-bharat-research-brain\maven-dashboard`. Operator note: a PostToolUse hook reported session cost $450.70 / 48 files modified; this plan pass modified zero files — flag looks misattributed, but verify before further agent runs.*

## 1. CONCEPT
This page should feel like sitting down at a private research desk that recognizes you: a near-black canvas (fey.com's extreme-contrast data storytelling), one serif headline (column.com's "bank as literary journal"), one brand object — the medallion — that comes alive exactly once, then gets out of the way. Everything else is quiet competence: hairline dividers over card borders (resend.com), mono numerals for every figure, emerald spent on ≤3 elements per viewport (the design digest's discipline rule). The current page is 90% there structurally; the redesign removes brand repetition, makes the built-but-dormant hero animation actually fire, and injects real market numbers where the suggestion cards currently ship empty calories.

## 2. SIGNATURE MOMENT — "Medallion Ignition"
The audit's sharpest finding: `MavenMark` in `components/chat-view.tsx` (line 88) has a complete pathLength draw sequence that **never fires** — no caller passes `draw`, and `useReducedMotionSafe()` kills it on the operator's reduced-motion machine anyway.

**Fix, precisely:** fire it inside `Core` (the medallion), the one place brand motion belongs.
- Replace the `initial/animate` prop pattern with motion values so the OS flag can't suppress it: `const p1 = useMotionValue(0); const p2 = useMotionValue(0); const dot = useMotionValue(0);` and in a `useEffect` on mount run `animate(p1, 1, { duration: 0.9, ease: EASE })`, `animate(p2, 1, { duration: 0.8, delay: 0.45, ease: EASE })`, `animate(dot, 1, { duration: 0.4, delay: 1.05, ease: EASE })` (`animate` imported from `framer-motion`). Bind via `style={{ pathLength: p1 }}` on each `motion.path`, `style={{ scale: dot }}` on the circle.
- Wrap in the existing `.brand-motion` class (already on `Core`'s root, line 110) — this is the sanctioned bypass; motion values sidestep framer's internal `useReducedMotion` gating.
- Sequence polish: hold the orbiting rim arc and sheen at `opacity:0` until the dot pops (~1.1s), then fade them in over 0.5s — ignition first, ambience second.
- Trigger: `Core` mount (empty state). Because `ChatShell` remounts `ChatView` via `key={activeId}`, the ignition naturally replays on "New chat" — a signature that re-signs each session. Total ~1.5s, runs once per mount, zero loops added.
- Keep the tiny `Avatar`/`ModelSelector` `MavenMark` instances static (`draw` unused there) — one ignition per screen.

## 3. SECTION-BY-SECTION

**Header — kill the double brand** (`app/chat/page.tsx`, lines 19–28). The 8×8 inline logo tile next to "Ask Maven" duplicates the site nav mark AND the medallion below (audit-confirmed). Delete the SVG tile; keep `h1` "Ask Maven" alone at `clamp(1.5rem, 1rem + 1.5vw, 1.875rem)` font-serif. Promote the eyebrow to the house label spec: `text-[11px] uppercase tracking-[0.18em] font-mono text-dim` — "AI copilot · India markets" becomes the technical mono eyebrow (Linear pattern). Net: brand appears exactly once above the fold (the medallion).

**Empty-state hero** (`Hero`, chat-view.tsx line 318). Keep composition; upgrade the headline to `clamp(2rem, 1rem + 3.5vw, 3.5rem)`, `tracking-[-0.02em] leading-[1.05]` per the editorial type digest. Under the headline add one honest mono status line fed by the ticker's data: "NIFTY 50 · 24,315.95 · +0.42% · updated 15:30 IST" — `font-mono tnum text-xs text-dim`, sourced from whatever `components/market-ticker.tsx` already fetches (new export or a small shared hook `lib/use-market-snapshot.ts`). No new API surface.

**Suggestion cards — data-rich** (`SuggestionCard`, line 339; `SUGGESTIONS`, line 12). Audit: data-poor. Extend the shape to `{ t, k, stat?: { label: string; value: string; tone: "up"|"down"|"flat" } }` populated from the same market snapshot hook (e.g. Sector leadership card shows "BANK NIFTY +1.2%" in emerald mono; Macro card shows "BRENT $71.40" gold-soft). Render the stat bottom-right in `font-mono tnum text-xs`, rose for negative per token rules. If the snapshot is unavailable, omit the stat entirely — never fabricate (house rule). Add the glass recipe upgrades from the design digest: `backdrop-blur-md saturate-150`, inner top highlight `inset 0 1px 0 rgba(255,255,255,0.08)`. Keep existing hover (top hairline sweep + corner glow) — it's already the right restraint.

**Sidebar — depth + hierarchy** (`components/chat-sidebar.tsx`). Audit: flat. Three changes: (1) wrap the list in the existing `GlassPanel` treatment — extract `GlassPanel` from chat-view.tsx into `components/glass-panel.tsx` and reuse (p-px gradient border, `bg-panel/45 backdrop-blur-xl`); (2) group conversations under mono date headers "TODAY / THIS WEEK / EARLIER" computed from `updatedAt`; (3) replace the static active hairline with a `layoutId="chat-active-rail"` `motion.span` so selection slides between rows (research digest pattern 11, Linear nav pill) — 1px wide, emerald/80, spring `{stiffness: 400, damping: 34}`. Keep no-stagger mount (correct call, already commented).

**Conversation view** (`AnswerCard`, `ReasoningLoader`, `UserBubble`). Already strong — sheen pass, evidence panels, feedback loop. Two touches only: give `keyData` values `font-mono` explicitly (currently just `tnum`), and add `saturate-150` to `GlassPanel`'s backdrop-blur when extracting it (digest: pure blur grays out on near-black). Do not add per-block staggers — existing comments correctly forbid it.

**Composer** — no changes; it's the page's best component. Copy stays as-is (already compliant: "educational market context… not investment advice").

## 4. 3D AND DEPTH
**No WebGL on this page.** The threeD digest's own budget logic rules it out: /chat is an app surface loaded on every visit, latency-sensitive, and its hero is 128px — a 250KB gzipped R3F chunk buys nothing a conic-gradient can't. The medallion's existing CSS stack (breathing glow, conic orbit arc, skewed sheen) plus the ignition IS the depth story. Reserve depth budget for: aurora blobs (existing, already mobile-thinned), glass `saturate()` upgrade, and a 2–3% SVG feTurbulence noise overlay on `AuroraBg` (data-URI, kills banding on the blurred gradients — design digest recipe). Perf cost: ~0KB JS. Fallback: everything degrades to static CSS; ignition is `.brand-motion`-sanctioned.

## 5. IMPLEMENTATION STEPS
1. **(S)** page.tsx: delete duplicate logo tile, mono eyebrow, h1 clamp. No tsc risk.
2. **(M)** chat-view.tsx: convert `MavenMark` draw to motion values + `animate()`; wire `draw` from `Core`; stage rim-arc/sheen fade-in. Watch: `animate` import must come from `"framer-motion"`; cleanup animations in effect return (tsc-safe, verify with `npx tsc --noEmit`).
3. **(S)** Extract `GlassPanel` → `components/glass-panel.tsx` with `saturate-150`; update chat-view imports. Import-cycle risk low; run tsc.
4. **(M)** `lib/use-market-snapshot.ts` sharing MarketTicker's data; extend `SUGGESTIONS` shape + stat rendering with honest-omission fallback. Type the new optional field carefully (tsc flag).
5. **(M)** chat-sidebar.tsx: GlassPanel wrap, date grouping, `layoutId` active rail.
6. **(S)** AuroraBg noise overlay + keyData `font-mono`.
7. **(S)** Verify: `npx tsc --noEmit`, then localhost visual pass at mobile/desktop with OS reduced-motion ON (ignition must still play). Per deploy-safety rule: no commit/push without explicit approval.

Bundle impact: zero new dependencies. Total new code ≈ 150 lines.
