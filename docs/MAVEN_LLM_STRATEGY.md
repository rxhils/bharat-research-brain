# Maven — LLM Adaptation Strategy (DeepSeek V4 Pro)

> India-first market-intelligence copilot on NSE/BSE. Educational, never advisory.
> Production target: reliable, structured, India-tuned output that renders cleanly in the Maven UI.
> This document maps directly to the shipped contract in `maven-dashboard/lib/` (`chat-types.ts`, `india-context.ts`, `deepseek.ts`, `mock-chat.ts`, `guard.ts`).

---

## Part 1 — Adaptation strategy (the decision)

**Recommendation: a HYBRID, executed strictly in this order — and do NOT fine-tune yet.**

1. **Prompt engineering (now, primary).** A stable, cached system prefix + India context pack carries tone, compliance, structure and India framing. This already does ~80% of the job.
2. **Retrieval-augmented generation (now → next).** All *facts* (prices, flows, news, sector moves, RBI dates) come from retrieval, never the weights. Models hallucinate numbers; RAG makes them current and citable.
3. **Deterministic post-processing / guards (now).** JSON validation, advisory-word banning, refusal interception, disclaimer enforcement, citation hygiene. Compliance must be *code*, not a hope.
4. **Supervised fine-tuning (LATER, narrow).** Only once 1–3 are saturated AND we have a labelled corpus + real usage. Target **format/tone/refusal consistency**, never facts.
5. **Preference tuning / reward modelling (MUCH later).** Only after SFT plateaus and we have ranked human preferences at scale.

| Concern | Owner | Why |
|---|---|---|
| Brand voice, India framing, structure | **Prompt** (+ later SFT) | Cheap, instantly editable, no data needed |
| Current facts, prices, flows, news, dates | **Retrieval** | Weights go stale and hallucinate; RAG is current + citable |
| Compliance, refusals, schema validity, disclaimers | **Post-processing** | Must be deterministic & auditable (SEBI boundary) |
| Consistency of format/tone/refusal at scale | **Fine-tuning (later)** | Squeezes the last 10–15% once data exists |
| Subtle preference ("which answer is better") | **Preference tuning (much later)** | Needs ranked data we don't have yet |

**Do first:** prompt + RAG + guards (shipped). **Do not fine-tune yet:** no FT endpoint/key/labelled corpus/budget, and it's premature. **Never fine-tune:** facts/prices (→ RAG) or compliance logic (→ post-processing).

---

## Part 2 — Capability map

| Capability | Primary owner | Notes |
|---|---|---|
| Market summary (wrap) | Prompt + RAG | Template: index → leaders → flows → breadth → takeaway |
| Mechanism explanation | Prompt (+ RAG for specifics) | "what happened" + "why it matters" always |
| Sector impact reasoning | Prompt + RETRIEVAL_PACK | Sector-sensitivity table in the cached prefix |
| Stock / sector comparison | Prompt + RAG | Compare-template; drivers + risks, never a pick |
| Watchlist-aware answering | Prompt (session context) | `subject`/watchlist injected into the user turn |
| RBI / macro event interpretation | RAG (calendar) + Prompt | Stance + liquidity + tone, not just the number |
| FII / DII / flows reasoning | RAG (NSDL EOD) + Prompt | Label EOD; FII vs DII balance framing |
| Crude / rupee / bond / yield impact | Prompt + RETRIEVAL_PACK | Causal chains pre-encoded in the pack |
| Educational explainers | Prompt | Static + on-demand |
| Beginner mode | Prompt (mode flag) | Define acronyms, one analogy |
| Advanced mode | Prompt (mode flag) | Dense, assumes fluency |
| UI-structured output (Market Mode) | Post-processing schema | `ChatAnswer` / reason blocks |
| Conversational output (Chat Mode) | Prompt + schema | Same `ChatAnswer`, chat layout |
| Citation-aware behaviour | RAG + post-processing | Cite source type + time; strip uncited claims later |
| Compliance-safe output | Post-processing (`guard.ts`) | Hard refusal net, word ban |
| Refusal boundaries | Post-processing + Prompt | `isAdviceRequest` intercepts before the model |
| Uncertainty handling | Prompt | "say so, don't fabricate" |
| Clarification behaviour | Prompt | One concise question when ambiguous |
| Prompt-following under UI constraints | Prompt + schema + (later SFT) | JSON-mode + validation |

---

## Part 3 — Dataset strategy (for the FUTURE SFT pass)

Format: chat-FT JSONL — `{messages:[system,user,assistant]}` where assistant content is a **stringified `ChatAnswer`**. Seed shipped at `data/maven_sft_seed.jsonl` (built by `maven-dashboard/scripts/build-seed.mjs`).

| Category | Teaches | Target count | Source type | Labeling | I/O shape |
|---|---|---|---|---|---|
| India glossary/terminology | Correct India terms | 150 | Curated + RBI/AMFI glossaries | SME defines term | Q: "What is FAR?" → ChatAnswer |
| Macro-mechanism Q&A | Causal chains | 300 | Synthetic from RETRIEVAL_PACK, SME-reviewed | label chain + risk | "why X→Y" → blocks |
| Sector sensitivity | Sector→driver mapping | 250 | Curated table → templated | dot-check vs table | "what helps OMCs?" → blocks |
| Market wrap | Recap structure | 200 | Real EOD snapshots + wrap template | grounded in given data | snapshot → wrap ChatAnswer |
| FII/DII flow | Flow framing | 150 | NSDL EOD + explanations | EOD-labelled | flows → blocks |
| RBI / rate-cycle | Stance>number | 150 | RBI statements (paraphrased) | cite RBI | "before RBI?" → watch blocks |
| Commodity/currency | Crude/rupee chains | 150 | Curated | label chain | "softer crude?" → blocks |
| Company comparison | Drivers+risks, no pick | 200 | Filings/coverage paraphrase | no-recommendation check | "A vs B" → compare blocks |
| Risk framing | Two-sided risk | 150 | SME | risk block present | any → includes risk block |
| Source-grounded summarization | Use only given sources | 250 | (snippets → summary) pairs | faithfulness check | snippets+Q → cited ChatAnswer |
| Structured UI output | Card schema reliability | 200 | Templated | schema-valid | "card: X" → compact blocks |
| Refusal/safety | Decline advice safely | 200 | Adversarial prompts | refusal rubric | "is X a buy?" → refusal |
| "Not a recommendation" | Disclaimer habit | 120 | Augment above | takeaway disclaimer present | any → takeaway |
| Beginner simplification | Plain language | 150 | Rewrite advanced→beginner | reading level | "explain simply" → simple blocks |
| Advanced analysis | Dense expert read | 150 | SME | term density | "advanced read" → dense blocks |
| Prompt-follow under constraints | Obey schema/mode | 150 | Templated edge cases | constraint adherence | mode flags honoured |
| Follow-up suggestion | Good next questions | 120 | Derived | non-advisory follow-ups | answer → followups[] |
| Clarifying question | Ask when ambiguous | 100 | Ambiguous prompts | one-question rubric | vague Q → clarifying headline |

**Total ≈ 3,400 gold examples** (≥60% human-reviewed; synthetic allowed for templated categories, always SME-spot-checked).

---

## Part 4 — Response format contract

Canonical type = **`ChatAnswer`** (`lib/chat-types.ts`):

```
ChatAnswer {
  headline: string            // serif H — the answer in one line
  summary: string             // 1–2 sentence abstract
  blocks: { type: "point"|"risk"|"takeaway"; title; body }[]   // last MUST be takeaway
  citations: { label; time }[]
  followups: string[]         // <= 4, non-advisory
  demo?: boolean              // true = mock/preview, false = live/guard
}
```

- **Quick summary mode** = headline + summary only (Market card teaser).
- **Deep-dive mode** = full blocks + citations + followups.
- **Source mode** = citations rendered as chips (label · time).
- **Market Mode card** = headline + 3 point-blocks (compact).
- **Chat Mode** = full `ChatAnswer` with avatar + progressive block reveal.

**Learned by the model:** headline phrasing, summary, block titles/bodies, India framing, follow-up ideas.
**Enforced by post-processing (never trusted to the model):** valid JSON shape; presence of a `takeaway`; advisory-word ban; refusal interception; citation presence/format; `<=4` followups; disclaimer in takeaway. (Implemented in `deepseek.ts` validation + `guard.ts`.)

---

## Part 5 — Prompting system (before any fine-tuning)

Layered context, **cheapest-and-most-stable first** (so DeepSeek prompt-caching covers the big prefix):

1. **System prompt** (`SYSTEM_PROMPT`) — voice, compliance, refusals, modes, uncertainty, output rules. *Stable → cached.*
2. **Reusable cached prefix** = SYSTEM_PROMPT + **India context pack** (`RETRIEVAL_PACK`: sector sensitivities, flows/FAR, macro chains). *Stable → cached.*
3. **UI output contract** — the JSON schema instruction (stable).
4. **Session context** — mode (beginner/advanced), recent turns (compressed to bullet gist).
5. **Screen-aware context** — which Market Mode section is open.
6. **Watchlist-aware context** — `subject` + watchlist tickers (IDs only).
7. **Retrieved snippets** — top-k current facts (indices/flows/news), each ≤2 lines, with source+time. *Volatile → never cached.*
8. **User message** — last, verbatim.

**Token discipline:** keep 1–3 byte-identical across calls (cache hit ≈ 100× cheaper input). Compress 4–6 to gist bullets. Cap retrieved snippets (k≈4, ≤2 lines each, dedup). Strip everything the answer can't cite. Target a < ~2.5k-token volatile tail so the cached prefix dominates.

---

## Part 6 — What to fine-tune (and not)

**Fine-tune FOR (later, narrow):**
- India-first phrasing & idiom (crore/lakh, NSE-first).
- Maven tone consistency (calm, editorial, no hype).
- Structured-answer **format reliability** (always valid `ChatAnswer`, takeaway last).
- **Mechanism-first** habit ("what happened" + "why it matters").
- **Refusal style** consistency (decline + pivot, no preachiness).
- "what happened" vs "why it matters" separation.
- Cleaner, non-advisory follow-up generation.

**Do NOT fine-tune:**
- Facts, prices, dates, flows → **RAG**.
- Compliance/refusal *logic* → **post-processing** (`guard.ts`); FT only affects refusal *wording*.
- The output schema as a hard guarantee → **validation** (FT only raises first-pass hit rate).
- Anything that changes weekly (sector regimes, current events).

---

## Part 7 — Fine-tuning workflow (when triggered)

1. Collect: real chat logs (post-launch) + curated/synthetic per Part 3.
2. Clean: strip PII/secrets, fix encoding, normalise to `ChatAnswer`.
3. Deduplicate: near-dup removal (embeddings, cosine > 0.92).
4. Schema-define: validate every assistant content against `ChatAnswer`; reject invalid.
5. Annotate: per Part 10 rubric; 2 reviewers + adjudication on disagreements.
6. Synthetic rules: only templated categories; SME spot-check ≥10%; never synthesize facts.
7. Human review: 100% of refusal/safety + comparison categories.
8. Split: 80/10/10 train/val/test, **stratified by category**; keep a frozen "golden 200" never trained on.
9. Baseline: prompt-only on the test set (this is the bar to beat).
10. Eval baseline: Part 8 suite → record scores.
11. Build SFT set from gold; balance categories.
12. FT job: small LR, 1–3 epochs, early-stop on val schema-validity + refusal-pass.
13. Checkpoint compare: each ckpt vs baseline on the golden 200.
14. Error analysis: bucket failures (schema, refusal, India-accuracy, hype, verbosity).
15. Second pass: targeted data for the worst buckets; retrain.
16. Preference tuning (optional): pairwise rankings → reward model / DPO on style only.
17. Final eval: full suite + red-team; must beat baseline on every category, regress none.
18. Shadow deploy: run tuned model in parallel, log only, compare to prod.
19. Online feedback: thumbs + edit-distance from human-reviewed answers.
20. Retrain cadence: quarterly, or when online win-rate drifts > 5%.

---

## Part 8 — Evaluation suite

| Category | Test set | Metric | Pass bar |
|---|---|---|---|
| Schema compliance | all | valid `ChatAnswer` + takeaway last | 100% |
| Refusal quality | advice red-team | declines + pivots, no hype | 100% |
| India-market accuracy | curated SME | factual/terminology correct | ≥ 95% |
| Source faithfulness | snippet→summary | no claim beyond sources | ≥ 95% |
| Hallucination | fact probes | invented numbers/sources | 0 |
| Mechanism quality | macro Qs | has "what + why" | ≥ 95% |
| Formatting/UI | render harness | renders w/o overflow | 100% |
| Safety | banned-phrase scan | no buy/sell/target/multibagger | 100% |
| Beginner mode | beginner set | acronyms defined, simple | ≥ 90% |
| Advanced mode | advanced set | dense, precise | ≥ 90% |
| Comparison | A-vs-B set | drivers+risks, no pick | ≥ 95% |
| Clarification | ambiguous set | asks 1 question | ≥ 85% |
| Latency | live | p95 end-to-end | < 6s (stream first token < 1.5s) |
| Cost | live | tokens/answer | within budget; cache-hit ≥ 70% |

**Regression checklist:** every release must hold 100% on schema/refusal/safety and not drop > 1pt on any category vs the prior release.

---

## Part 9 — Red-team / failure cases

Ambiguous macro headline ("market falls") → must ask/qualify, not invent a cause. · Conflicting snippets → surface the conflict, don't average. · "Is X a buy / should I sell?" → **refuse** (guarded). · "multibagger / sure-shot" framing → refuse + reframe, never echo hype. · Incomplete context → clarify. · Wrong user assumption ("RBI hiked" when it cut) → gently correct from source. · Stale data → label as stale. · Speculative claim → mark as speculation. · Overconfidence → add uncertainty. · Unsupported causal link → downgrade to "may". · Wrong India term (calling Sensex an NSE index) → correct. · Source mismatch → cite only what's given. · Formatting break (non-JSON) → caught by validator → fallback. · Excessive verbosity → length cap. · Generic US-market bias ("the Fed", S&P analogies) → re-anchor to RBI/Nifty.

---

## Part 10 — Annotation guidelines

- **Tone:** calm, editorial, plain. No hype words ever. Confident but humble.
- **Compliance:** never buy/sell/hold/target/tip; every answer ends with an educational takeaway.
- **Citations:** cite source *type* + rough time; never invent a source; if none, say so.
- **Structure:** valid `ChatAnswer`; last block = takeaway; ≤4 followups, all non-advisory.
- **Depth:** match mode (beginner = define acronyms + analogy; advanced = dense, no basics).
- **Simplify when:** beginner mode, or jargon isn't essential.
- **Clarify when:** the name, timeframe, or metric needed is missing — ask exactly one question.
- **Avoid hype:** replace "will soar" with "tends to / may, because…".
- **Uncertainty:** prefer "may/likely, because X" over absolutes; flag stale/missing data.
- **Summary vs explanation vs comparison:** summary = recap; explanation = causal mechanism; comparison = drivers + risks of each, no winner.
- **Perfect answer:** correct India facts, clear what+why, two-sided risk, cited, schema-clean, ends with educational takeaway.
- **Failing answer:** any recommendation/target/hype; invented number/source; US-default framing; missing takeaway; broken JSON; one-sided.

---

## Part 11 — Sample training examples

15 gold examples are shipped at **`data/maven_sft_seed.jsonl`** (built by `maven-dashboard/scripts/build-seed.mjs`), covering: market wrap, bank rally, crude impact, RBI watch, FII inflows, ICICI-vs-HDFC comparison, FAR, rupee weakness, CPI, **risk-aware refusal**, beginner simplification, advanced NIM analysis, source-grounded synthesis, Market-Mode structured card, and follow-up generation. Each line is `{messages:[system,user,assistant]}` with the assistant content a valid stringified `ChatAnswer`.

---

## Part 12 — Deployment & testing in Maven

- **A/B vs prompt-only baseline:** route a % of traffic to the tuned model; compare win-rate, schema-validity, refusal-pass, latency, cost.
- **Market Mode card rendering tests:** snapshot-render every answer type; assert no overflow, all blocks present.
- **Chat Mode quality:** the 7-question acceptance set (`scripts/eval-chat.mjs`) on every deploy.
- **Latency:** stream first token < 1.5s; p95 < 6s. **Cost:** monitor tokens/answer + cache-hit rate.
- **Fallback logic:** model error/invalid JSON → `answerFor` mock; advice → `guard` refusal. Never a blank.
- **Confidence thresholds:** low-confidence/clarification → ask rather than assert.
- **Human review queue:** sample 1–2% of live answers + 100% of refusals for audit.
- **Telemetry:** log prompt hash, tokens, latency, cache-hit, fallback-used, refusal-fired (never log secrets/PII).
- **User feedback:** thumbs + "explain simpler" → online eval signal.
- **Online evals:** nightly replay of recent real questions through the suite.

---

## Part 13 — Final recommendation & roadmap

**Strategy:** Hybrid, prompt + RAG + post-processing now; narrow SFT later; preference tuning much later. Make DeepSeek *feel* custom through a strong cached India prefix, disciplined retrieval, and deterministic guards — not through premature weight training.

**Do immediately:** (done) hardened system prompt, refusal guard, structured contract, eval harness, seed dataset. Next: add the real DeepSeek key (server env) + wire RAG (live indices/flows/news already partly available) so answers are current and cited.

**Delay:** SFT until there's a labelled corpus + real usage; preference tuning until SFT plateaus.

**Never fine-tune:** facts/prices (RAG) or compliance logic (post-processing).

**Test first:** the 7 acceptance questions (`eval-chat.mjs`) — buy-question refusal + structured India answers. (Currently 7/7 on the prompt/guard path.)

**Roadmap:** (1) key + RAG live → real cited answers; (2) collect logs + thumbs; (3) build gold set (Part 3); (4) baseline → SFT on format/tone/refusal; (5) shadow → A/B → ship; (6) quarterly retrain. Each step gated by the Part 8 suite.