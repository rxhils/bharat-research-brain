# Maven Self-Learning Improvement Loop (v1)

A supervised **learning + evaluation** loop that lets Maven get measurably better over
time without ever changing its own production behaviour on the fly. Maven observes its
own answers, scores them, logs the failures, classifies them, and turns the recurring
ones into regression eval cases. A human reviews, a developer (or Claude Code) implements
the fix, the evals go green, and only then does the change ship.

This document is the operator's manual for that loop. Every command, file, and data path
referenced here is real and lives in this repo (`maven-dashboard`).

---

## 1. What it is / what it is NOT

**It IS:**

- A **supervised learning and evaluation loop**. It captures where Maven was wrong,
  aggregates patterns, and produces *candidate* regression eval cases.
- **Human-in-the-loop.** Every fix is proposed, reviewed, and approved by a person before
  it ships. Suggestions carry `requiresApproval: true`.
- **Deterministic where it can be.** Failure classification and reporting are plain,
  auditable code — no model call decides whether an answer "failed."

**It is NOT:**

- **Not fine-tuning.** No model weights are trained, updated, or downloaded. There is no
  gradient step anywhere in this loop.
- **Not autonomous self-modifying production code.** Maven does not rewrite its own
  prompts, routing, or handlers at runtime. Nothing is pushed automatically.
- **Not a silent behaviour changer.** Maven must never quietly alter production output.
  Code changes flow through review + eval gates + git like any other change.

### The flow

```
observe ── score ── log ── classify failure ── create eval case ── human approves
                                                                          │
                                          ship ◄── evals pass ◄── Claude Code / dev fixes
```

Read it as a one-way ratchet: a failure only becomes a shipped change after it has been
turned into a green eval and a human has signed off. **Maven must not silently change
production behaviour or push code automatically.**

---

## 2. How feedback is logged

Feedback (from the chat UI feedback controls, or emitted by the training runner) is sent
to a single endpoint:

```
POST /api/feedback
{
  "query":    "Why is Blue Star moving today?",   // required
  "response":  { ...MavenAnswer... },              // optional: the answer being judged
  "conversationContext": { ... },                  // optional: NOT persisted in v1
  "feedback": "not_enough_sources",                // optional: one of the values below
  "expectedBehavior": "should cite 5+ sources",    // optional: free text
  "notes": "..."                                    // optional
}
```

**Response:** `{ id, failureTypes, severity }`.

### Feedback values

| Value                 | Meaning                                          |
| --------------------- | ------------------------------------------------ |
| `good`                | Answer was correct and useful.                   |
| `bad`                 | Answer was wrong/unhelpful (unspecified reason). |
| `too_generic`         | Answer was shallow / boilerplate.                |
| `outdated`            | Answer used stale data.                          |
| `wrong`               | Answer was factually incorrect.                  |
| `not_enough_sources`  | Answer was under-sourced.                        |

The endpoint runs the deterministic classifier (§3), builds a `MavenLearningEvent`, and
appends it to storage. Explicit feedback is also mapped onto failure types
(`not_enough_sources → thin_sources`, `outdated → stale_metric`, `wrong → weak_reasoning`,
`too_generic → weak_reasoning`), so a human tag and an automatic signal reinforce each other.

### Where events are stored

Events are stored as JSON via `lib/maven/learningStore.ts`:

- `data/maven-learning/events.json` — one array of `MavenLearningEvent`.
- `data/maven-learning/suggestions.json` — aggregated fix suggestions.

The store **redacts before writing**: emails, phone numbers, and long opaque tokens/API
keys are stripped; raw `conversationContext` is never persisted in v1; strings are capped
at 2000 chars and arrays at 25 items; writes are near-atomic (temp file + rename).

> **Caveat — production storage.** Local JSON files are fine for **local/dev** use. On
> serverless platforms (e.g. Vercel) the filesystem is **ephemeral and read-only outside
> `/tmp`**, so writes will not persist and may fail. Durable production feedback capture
> should later move to a **Supabase-backed store** behind the same `learningStore`
> interface. Treat the JSON files as a dev-only substrate.

---

## 3. Failure types

Classification is **deterministic** and lives in `lib/maven/learningFailureClassifier.ts`.
It is conservative by design — it under-flags rather than inventing failures, because every
flagged event can become a regression eval case. The 16 types
(`MavenFailureType` in `lib/maven/learningTypes.ts`):

| #  | Failure type                  | One-line meaning                                                                 |
| -- | ----------------------------- | -------------------------------------------------------------------------------- |
| 1  | `wrong_route`                 | Query handled by the wrong answer type / pipeline.                               |
| 2  | `out_of_scope_false_positive` | An in-scope Indian-market query was wrongly bounced to the "out of scope" card.  |
| 3  | `bad_followup_handling`       | A follow-up/reshape ("make it a table", "show sources") wasn't applied to the prior answer. |
| 4  | `wrong_symbol`                | Single-stock intent resolved to the wrong ticker — or to no ticker at all.       |
| 5  | `thin_sources`                | A research-style answer was backed by too few sources (fewer than 5).            |
| 6  | `stale_metric`                | A figure/fiscal year presented as current is actually 2+ years stale.           |
| 7  | `unsupported_metric`          | An approximate/percentage number appears with no visible citation.               |
| 8  | `fake_catalyst`               | A stated reason/catalyst for a move isn't supported by the sources.              |
| 9  | `wrong_chart`                 | A chart doesn't match the data/intent (wrong series or type, or charting when not asked). |
| 10 | `weak_reasoning`              | Generic or shallow reasoning; answer marked `wrong` or `too_generic`.            |
| 11 | `missing_sources`             | Claims were made with no sources attached at all.                                |
| 12 | `provider_leakage`            | Model/provider/backend internals (e.g. model names, "LLM", stack traces, API keys) leaked into user text. **Critical.** |
| 13 | `advice_leakage`             | Buy/sell/target-price/"multibagger" advisory language reached the user. **Critical.** |
| 14 | `bad_ui_render`               | Answer content was malformed for the UI (broken blocks/markup).                  |
| 15 | `slow_response`               | Response breached the latency budget.                                            |
| 16 | `other`                       | A real problem not captured above; routed to a manual eval case.                 |

**Severity** is derived automatically: `advice_leakage` / `provider_leakage` → `critical`;
`stale_metric` / `unsupported_metric` / `wrong_symbol` → `high`; `thin_sources` /
`bad_followup_handling` → `medium`; everything else → `low`. Each failure type maps to a
suggested fix area (routing rule, stock resolver, source search, metric validator, answer
generator, UI render, guardrail, or a plain eval case).

---

## 4. How to generate eval cases

```bash
npm run learn:evals            # print suggested eval cases derived from logged failures
npm run learn:evals -- --apply # ALSO write scripts/evals/learned-eval-cases.suggested.json
```

- With no flag, it **prints** suggestions to the console for review — it changes nothing.
- With `-- --apply`, it writes the suggestions to
  **`scripts/evals/learned-eval-cases.suggested.json`** (a staging file).
- It **never auto-edits the main eval file** (`scripts/evals/maven-eval-cases.mjs`).
  Promoting a suggested case into the main eval set is a manual, reviewed step: a human
  copies the approved case(s) across. This keeps the authoritative eval dataset
  human-owned.

---

## 5. How to run learning reports

```bash
npm run learn:report   # aggregate events + suggestions into a readable console report
npm run learn:loop     # run the evals, then print a prioritized fix plan
```

**`learn:report`** (`scripts/maven-learning-report.mjs`) reads
`data/maven-learning/events.json` and `suggestions.json` and prints:

- Totals (events, suggestions).
- Failures by type, and the top **repeated patterns** (`failureType @ answerType`, count ≥ 2).
- Critical failures and their queries.
- Unresolved failures (status `new` | `triaged`) with their ids.
- Suggested fixes grouped by fix type, each flagged `[needs approval]`.
- Whether a suggested-eval file exists yet.

It is **CI-safe**: it exits non-zero **only** when there are unresolved **critical**
failures (advice/provider leakage), so it can gate a pipeline without failing on
low-severity noise.

**`learn:loop`** (`scripts/maven-improvement-loop.mjs`) is the end-to-end driver: it runs
the eval suite and emits a **prioritized fix plan** off the aggregated failures, so you
see "what to fix next" in one command.

---

## 6. How to stress-test (training questions)

```bash
npm run train:maven       # run the 50 training questions against local /api/ask
npm run train:maven:log   # same, but also log failures via POST /api/feedback
```

The 50 questions live in `scripts/evals/training-questions.mjs`, grouped by
`conversation_followup`, `market_summary`, `macro_sector`, `single_stock`,
`stock_comparison`, `safety`, and `scope`. The runner (`scripts/run-training-questions.mjs`)
drives each one against the **local** `/api/ask`. `train:maven:log` additionally feeds each
failure back through the feedback endpoint so it lands in the learning store.

> **Caveat — you need a live server WITH API keys.** A *meaningful* run requires the app
> running locally **with real API keys** (DeepSeek + the search providers). A **keyless**
> run only exercises routing / safety / scope behaviour; the data-dependent questions will
> come back under-sourced and undated, and the classifier will log **false**
> `thin_sources` / `stale_metric` events. **Do not run the full, data-dependent training
> set keyless** — you'll poison the learning store with noise. Keyless, restrict yourself
> to the routing/safety/scope subset.

---

## 7. How to turn repeated failures into fixes

The loop is a triage pipeline, not an autopilot:

1. **Capture** — failures accumulate in `data/maven-learning/events.json` (from the UI,
   from `train:maven:log`, or from direct `POST /api/feedback` calls).
2. **Triage** — mark events (`new → triaged → converted_to_eval → fixed`, or `ignored`).
3. **Find the pattern** — `npm run learn:report` surfaces repeated `failureType @ answerType`
   patterns and critical failures. `npm run learn:loop` adds a prioritized plan.
4. **Generate an eval case** — `npm run learn:evals -- --apply` writes candidate cases to
   `scripts/evals/learned-eval-cases.suggested.json`.
5. **A human approves** — review the suggested case, then copy the approved one into the
   main eval file `scripts/evals/maven-eval-cases.mjs`. **This is the gate. Nothing past
   here happens without sign-off.**
6. **Implement the fix** — a developer (or Claude Code) changes the relevant code
   (routing rule, resolver, source search, metric validator, guardrail, UI render, …).
7. **Evals go green** — `npm run eval:maven` (plus `learn:loop`) must pass, including the
   new regression case.
8. **Ship** — commit and push through the normal review process.

**Approval is required before any code change is shipped. Nothing is auto-pushed.** The
learning loop *proposes*; humans *dispose*.

---

## 8. Safety invariants

These hold at every step of the loop and are non-negotiable:

- **No secrets stored.** The store redacts emails, phone numbers, and long tokens/API keys
  before writing, and never persists raw conversation context in v1. Keys never enter
  `data/maven-learning/`.
- **No provider/model/backend leakage to users.** `provider_leakage` is a first-class,
  *critical* failure. Model names, "LLM", stack traces, and internal errors must never
  reach a user; the feedback endpoint itself also refuses to leak internals to clients.
- **No weakening of financial guardrails.** The loop exists to *strengthen* the
  advice-leakage and no-fabrication guards (`advice_leakage`, `fake_catalyst`,
  `unsupported_metric`, `stale_metric`), never to relax them. A fix that would soften a
  guardrail is out of scope.
- **No autonomous production changes.** Every fix is human-approved and shipped through
  git. Maven does not self-modify, and nothing is pushed automatically.

---

## Quick reference

| Command                          | Script                                   | What it does                                             |
| -------------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| `npm run learn:report`           | `scripts/maven-learning-report.mjs`      | Aggregate events + suggestions; CI-gate on critical.     |
| `npm run learn:evals`            | `scripts/generate-evals-from-learning.mjs` | Print suggested eval cases.                            |
| `npm run learn:evals -- --apply` | ″                                        | Also write `scripts/evals/learned-eval-cases.suggested.json`. |
| `npm run learn:loop`             | `scripts/maven-improvement-loop.mjs`     | Run evals + prioritized fix plan.                        |
| `npm run train:maven`            | `scripts/run-training-questions.mjs`     | Run 50 training questions vs local `/api/ask`.           |
| `npm run train:maven:log`        | ″ `--log-failures`                       | Same, and log failures via `/api/feedback`.              |

| File / path                                     | Role                                             |
| ----------------------------------------------- | ------------------------------------------------ |
| `app/api/feedback/route.ts`                     | Feedback ingest endpoint.                        |
| `lib/maven/learningStore.ts`                    | JSON event/suggestion store (with redaction).    |
| `lib/maven/learningTypes.ts`                    | Shared type contract (16 failure types, etc.).   |
| `lib/maven/learningFailureClassifier.ts`        | Deterministic failure classifier.                |
| `data/maven-learning/events.json`               | Logged learning events (dev substrate).          |
| `data/maven-learning/suggestions.json`          | Aggregated fix suggestions.                       |
| `scripts/evals/training-questions.mjs`          | 50 stress-test questions.                        |
| `scripts/evals/maven-eval-cases.mjs`            | Authoritative eval dataset (human-owned).        |
| `scripts/evals/learned-eval-cases.suggested.json` | Staging file for machine-suggested eval cases. |
