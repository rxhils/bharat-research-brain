# Maven Platform Baseline — 2026-07-13

> Phase-1 stabilization snapshot (per the production-hardening roadmap). One page a fresh
> engineer can use to identify the deployed commit, run the same checks, and understand which
> endpoint each client uses. Facts below were verified against `origin/master` and live
> production on 2026-07-13. Update this file whenever the deploy target, endpoints, or eval
> baseline changes.

---

## 1. Deployment snapshot

| Item | Value |
|---|---|
| Repo | `github.com/rxhils/bharat-research-brain` (private) |
| App | `maven-dashboard/` (Next.js 14, App Router) |
| Production branch | `master` — Vercel auto-deploys every push |
| Deployed commit (2026-07-13) | `30db4fc` — "clean chat hero core" |
| Production URL | `https://www.trymaven.in` (canonical; apex does not serve POST /api) |
| Brain last changed | `6edc259` (2026-07-12) — no `lib/maven/` or `app/api/` change since, so the eval baseline below carries to `30db4fc` |

**Public API endpoints (both live, verified in production):**

| Endpoint | Client | Contract |
|---|---|---|
| `POST /api/ask` | Web chat (and current iOS build) | body `{ query, conversationContext? }` → `MavenAnswer` JSON |
| `POST /api/mobile/ask` | Mobile (target) | same body → `{ schemaVersion: 1, answer: MavenAnswer }`; clean errors; in-memory rate-limit placeholder |
| `POST /api/feedback` | Web feedback UI (learning loop) | logs a MavenLearningEvent — **known-broken on Vercel**, see §7 |
| `POST /api/chat` | legacy, unused by the chat UI | thin DeepSeek wrapper |

## 2. Architecture (one brain, thin wrappers)

```text
Web client ─┐
            ├─ /api/ask ────────────┐
iOS client ─┼─ /api/mobile/ask ─────┤──► lib/maven/answerQuestion.ts   ← THE brain (single source)
            │   (envelope + limits) │      routing → follow-ups/corrections → research
            └─ [auth/quota: TODO]───┘      → contextPackBuilder (data/tools/sources)
                                           → generateAnswer / report / transforms
                                           → validator + quality scorer + guardrails
```

- All intelligence is server-side and deterministic-first; DeepSeek is a single optional
  prose-composer call with a full deterministic fallback (`lib/deepseek.ts`, model from
  `DEEPSEEK_MODEL`, default `deepseek-chat`).
- Clients only render the returned JSON and echo back `conversationContext.turns`
  (last 3; each turn `{ id, userQuery, answer: <full prior response> }`).
- Never duplicate brain logic in a wrapper or client. New endpoints wrap `answerQuestion()`.

## 3. Canonical working copies

| Path | Role | Rule |
|---|---|---|
| `F:\trymaven\code\github-bharat-research-brain` | Main clone (currently used by UI/newsroom sessions; carries their WIP) | Don't build API/brain features here while another session owns it |
| `F:\trymaven\code\movers-v2-worktree` | Worktree used for brain/API feature branches | Fine to keep; remove with `git worktree remove` after branch cleanup |

**Policy going forward:** one feature = one short-lived branch off fresh `origin/master`,
built in an isolated worktree if another session is active; always `git fetch` + fast-forward
check before pushing `master`.

## 4. Branch map (as of 2026-07-13)

**Merged into `master` (history preserved; branch pointers safe to delete):**
`maven-stock-movers-v1` (8fd8bbe) · `maven-movers-universe-v2` (7f0f27d) ·
`maven-sector-movers-v1` (ac829d4) · `maven-mobile-ask-v1` (6edc259) ·
`maven-learning-loop-v1` (342fb13) · `feat/newsroom-dashboard-orchestrator` (30db4fc) ·
`deploy-v2` (db2ce99) · `defensive-deploy` (0bb74e1)

**Not merged:** `test1-momentum` (6d5abb6, 2026-06-30 data-layer/artifacts snapshot) — review
once, then delete or archive-tag. **Recommendation:** after review, delete all merged branch
pointers on origin to end the sprawl.

## 5. Eval baseline (the merge gate)

Last full verification (2026-07-12, tree `6edc259`; brain unchanged through `30db4fc`):

| Suite | Command | Baseline |
|---|---|---|
| Core behavior | `npm run eval:maven` | **149/149**, avgScore 100, 0 leakage/refusal/stale/evidence failures |
| Stock movers | `npm run eval:movers` | **9/9** |
| Conversation flows | `npm run eval:conversation` | **5/5** |
| Follow-up transforms | `npm run eval:followups` | 8/8 (older baseline) |
| Source depth | `npm run eval:sources` | **15/20 — known gap** (`C_deep_research` 0/5; see §7) |

**CI gate (until real CI exists, run manually before every merge to `master`):**
`tsc --noEmit` clean → `eval:maven` 149/149 → `eval:movers` 9/9 → `eval:conversation` 5/5.
Prod smoke after deploy: `npm run eval:maven:prod` (or the §8 curl checks).

## 6. Environment variables (NAMES ONLY — never write values here)

| Group | Names | Notes |
|---|---|---|
| LLM | `DEEPSEEK_API_KEY` (aliases read: `DEEPSEEK`, `deepseek`), `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | Missing key → deterministic fallback, never a crash |
| Search providers (all optional, layer-gated) | `TAVILY_API_KEY`, `SERPER_API_KEY`, `EXA_API_KEY`, `BRAVE_API_KEY`, `SERPLIFY_API_KEY`, `GOOGLE_CSE_KEY`, `GOOGLE_CSE_CX`, `SEARXNG_URL` | Unset = that layer silently off |
| Data | `DATABASE_URL` | |
| Supabase (client auth) | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Unset = mock/open mode |
| Eval/tooling | `MAVEN_EVAL_URL` (alias `MAVEN_URL`) | test targets only |

## 7. ⏰ Urgent operator actions & known gaps (ranked)

1. **Pin `DEEPSEEK_MODEL` in Vercel — time-critical.** Code default is the `deepseek-chat`
   alias, flagged to sunset **2026-07-24** (11 days from this snapshot). Set the env var to a
   pinned model ID per DeepSeek's current docs. 10-minute action; without it, prose generation
   silently degrades to the deterministic fallback when the alias dies.
2. **API is open server-side (denial-of-wallet).** The Google/Supabase auth shipped recently is
   client-side gating only; **zero commits have touched `app/api/` or `middleware.ts` since
   `6edc259`**. `/api/ask` has no auth or rate limit; `/api/mobile/ask` has only an in-memory
   placeholder (resets per cold start, not shared across instances). → Roadmap §2 (durable
   auth + quota) is the next build. Coordinate ownership first: another session owns the
   client-auth work.
3. **`/api/feedback` is live but its store is broken on Vercel.** The learning loop merged to
   `master`, but it writes local JSON (`data/maven-learning/`) — read-only FS on Vercel, so
   prod feedback fails with a clean 500 and nothing persists. Fix = Supabase-backed store
   (roadmap §6). Until then, treat prod feedback data as nonexistent.
4. **Secrets hygiene.** The 2026-07-08 consolidation bundle (`F:\trymaven`) copied `.env` files
   and tokens (see its `SECRETS-WARNING.md`) — rotate anything that lived there. A Supabase DB
   password was once pasted in chat (rotate if not already). Repo-root `DEPLOY.md` references a
   different Supabase project ref than the one used historically — confirm the canonical
   project during roadmap §2 and delete the stale ref.
5. **Deep research quality gap** — `eval:sources` 15/20. Implement the existing adversarially-
   reviewed spec at `docs/superpowers/specs/2026-07-08-deep-research-depth-design.md`
   (includes the SSRF-safe fetcher that also closes the open `pageExtractor` finding). Roadmap §5.
6. Minor polish backlog: "no IT stocks fell today" note when a sector is all-green;
   filter tip-flavored headlines ("how should you trade…") from leaderboard-explainer catalysts;
   populate the Change-₹ column (needs prev-close in mover rows).

## 8. Runbook

- **Deploy:** push/fast-forward `master` → Vercel builds (~1–3 min). Verify:
  `curl -s -X POST https://www.trymaven.in/api/ask -H "Content-Type: application/json" -d '{"query":"top gainers today"}'`
  → expect `"type":"stock_leaderboard"`; same body against `/api/mobile/ask` → expect
  `"schemaVersion":1`. Safety probe: `{"query":"which stock should I buy?"}` → `unsafe_advice`.
- **Rollback:** `git revert <sha>` on `master` and push (never force-push master).
- **Local dev:** `npm run dev` from `maven-dashboard/`; it auto-bumps ports (3000→3001→3002) —
  read the actual port from the dev-server log before testing, and kill stray `node` dev
  processes after (they accumulate as zombies and fight over `.next`).
- **Evals:** run against a local dev server via `MAVEN_EVAL_URL=http://localhost:<port>/api/ask`;
  prod variants: `eval:maven:prod`, `eval:sources:prod`.
- **Mover data:** Nifty 500 universe is a committed snapshot
  (`lib/maven/data/nifty500.json`, regenerate with `node scripts/gen-nifty500.mjs`); quotes are
  keyless Yahoo v8 per-symbol with a rolling cache — coverage counts are printed honestly in
  each answer's limitation; Yahoo throttling degrades to the honest "unavailable" card, never
  wrong data.

## 9. Roadmap pointer

The agreed sequence (2026-07-13): ① this baseline + branch cleanup + CI gate → ② durable auth
+ quota (critical path) → ③ observability + synthetic prod checks → ④ quote-provider
resilience/coverage policy → ⑤ mobile parity + iOS rollout → ⑥ deep-research depth (implement
the existing spec) → ⑦ Supabase-backed feedback loop → ⑧ ongoing polish. Every phase ships
behind the §5 gate.
