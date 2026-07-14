# Maven Mobile API — `/api/mobile/ask` runbook

> Production contract + operations for the mobile endpoint. Architecture rule: **one brain**
> (`lib/maven/answerQuestion.ts`) behind thin wrappers — the mobile route adds identity, durable
> quotas, envelopes and logging, never answer logic. See `docs/BASELINE.md` for the platform
> snapshot.

## Contract

**Request** — `POST /api/mobile/ask` (POST only), JSON:

```jsonc
{
  "query": "top gainers today",                  // required, ≤ 2000 chars
  "conversationContext": {                        // optional, last 3 turns used, ≤ 10 accepted
    "turns": [ { "id": "t1", "userQuery": "...", "answer": { /* FULL prior MavenAnswer */ } } ]
  }
}
```
`Authorization: Bearer <Supabase access token>` is **required**. `userId` in the body is ignored
by design. Raw body cap 256 KB.

**Success** — `{ "schemaVersion": 1, "answer": { ...MavenAnswer } }`

**Failure** — `{ "schemaVersion": 1, "error": { "code", "message", "retryAfterSeconds"? } }`
with stable codes: `INVALID_REQUEST` (400) · `UNAUTHENTICATED` (401) · `FORBIDDEN` (403,
reserved) · `RATE_LIMITED` (429, + `Retry-After` header) · `SERVICE_UNAVAILABLE` (503) ·
`INTERNAL_ERROR` (500). Every response carries `X-Request-Id`. No provider/model/stack detail
is ever returned.

## Token verification

- The client sends a **Supabase access token** (obtained via Supabase Google OAuth — the same
  identity system the web app uses).
- The server verifies it with `supabase.auth.getUser(token)` (`lib/supabase/server.ts` →
  `getSupabaseForToken`); RLS applies to everything done with that client. There is **no**
  unverified JWT decode and **no** service-role key in this app.
- Failure categories (missing / malformed / invalid-or-expired / unresolved) are logged as
  categories only and all surface to the client as a single `UNAUTHENTICATED`.
- **iOS prerequisite:** the app must sign in via Supabase (Google) and attach the session's
  access token from its secure auth layer. Until it does, `/api/mobile/ask` returns 401 by
  design (the current app build, which still calls `/api/ask`, is unaffected).
- Local testing only: `MAVEN_TEST_AUTH_SECRET` + `x-maven-test-secret`/`x-maven-test-user`
  headers mint a test identity. This path is **hard-disabled whenever `VERCEL` is set** — it
  cannot exist in production.

## Quota classes (env-tunable; defaults in `lib/maven/apiGuard.ts`)

| Class | Key | Default | Store |
|---|---|---|---|
| Pre-auth IP burst | IP + route | 10 / 60s | Upstash |
| Per-user daily | verified user id | 150 / day | Upstash (IP change ≠ reset) |
| Deep-research daily | user id | 10 / day | Upstash |
| Deep concurrent | global | 3 slots | Upstash INCR/DECR |
| Web anon burst | IP | 30 / min | Upstash (best-effort) |
| Web authed daily | user id | 150 / day | Supabase `usage_events` (caller's own JWT) |

**Fail-closed rule:** in production (`VERCEL` set) with no Upstash configured, `/api/mobile/ask`
returns `SERVICE_UNAVAILABLE` — a missing limiter never means unlimited traffic. The in-memory
limiter exists for tests/local dev only and is never selected in production. The web path
degrades best-effort instead (anonymous web access remains a product decision).

## Required environment (names only)

`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` (durable limiter — required for mobile),
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (identity),
`MAVEN_EVAL_TOKEN` (eval bypass; never bypasses auth), plus the optional quota knobs listed in
`.env.example`.

## What to monitor (structured logs, `src:"maven-api"`)

- `evt:"auth"` — spike in `invalid_or_expired`/`malformed` = token abuse or a broken app build.
- `evt:"quota"` `outcome:"limit"` — per bucket; sustained `mobile_burst_ip` limits = scraping.
- `evt:"quota"` `outcome:"no_durable_limiter"` — **page immediately**: mobile is failing closed.
- `evt:"complete"` `latencyMs` — p95 drift; `evt:"error"` `errorCategory:"internal"` — bugs.
- Logs contain request-ids and short identity hashes only — never tokens, queries, bodies,
  raw provider responses, or plaintext user ids/IPs.

## Local testing without weakening production

```bash
# parity (no special env): mobile 401s, web unchanged
npm run dev            # then: npm run eval:guard

# enforcement matrix (test-only auth + tiny quotas):
RATE_LIMIT_ENABLED=1 API_BURST_PER_MIN=3 WEB_ANON_BURST_MAX=3 MOBILE_BURST_MAX=50 \
MOBILE_USER_DAILY_MAX=2 MAVEN_TEST_AUTH_SECRET=guard-test-secret \
MAVEN_EVAL_TOKEN=guard-test-bypass npm run dev
# then: npm run eval:guard -- --enforce

# production fail-closed simulation:
VERCEL=1 npm run dev   # then: npm run eval:guard -- --prodsim
```

Full regression gate: `tsc --noEmit` + `eval:maven` + `eval:movers` + `eval:conversation`
(+ `eval:sources`, known 15/20 baseline) — see `docs/BASELINE.md` §5.
