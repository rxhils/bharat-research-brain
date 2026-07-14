// API-guard test matrix (keyless - no Supabase/Upstash account needed).
//
// Modes (target from MAVEN_EVAL_URL, default localhost:3000):
//
//  default    dev server started with NO special env.
//             Asserts: web /api/ask unchanged; mobile requires auth (401 UNAUTHENTICATED with
//             the versioned envelope); malformed requests get INVALID_REQUEST; X-Request-Id set.
//
//  --enforce  dev server started with:
//               RATE_LIMIT_ENABLED=1 API_BURST_PER_MIN=3 WEB_ANON_BURST_MAX=3
//               MOBILE_BURST_MAX=50 MOBILE_USER_DAILY_MAX=2
//               MAVEN_TEST_AUTH_SECRET=guard-test-secret MAVEN_EVAL_TOKEN=guard-test-bypass
//             Asserts: valid (test-only) identity reaches the brain and the success envelope +
//             refusal semantics are intact; per-user daily quota canNOT be bypassed by a new IP;
//             burst limits 429 with Retry-After; eval-token bypass works; wrong token doesn't.
//
//  --prodsim  dev server started with: VERCEL=1   (and no UPSTASH_* config)
//             Asserts: mobile fails CLOSED with SERVICE_UNAVAILABLE (durable limiter missing in
//             "production"), and the test-only auth headers are ignored (impossible in prod).
//
// Usage: npm run eval:guard [-- --enforce | --prodsim]

const ROOT = (process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask").replace(/\/api\/ask\/?$/, "");
const MODE = process.argv.includes("--enforce") ? "enforce" : process.argv.includes("--prodsim") ? "prodsim" : "default";
const TEST_SECRET = "guard-test-secret";
const BYPASS = "guard-test-bypass";
const TEST_USER = "11111111-1111-4111-8111-111111111111";

let fails = 0;
const check = (name, cond, detail = "") => {
  console.log(`${cond ? "OK " : "XX "} ${name}${detail ? `  (${detail})` : ""}`);
  if (!cond) fails++;
};

async function post(path, body, headers = {}, rawBody) {
  const r = await fetch(ROOT + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: rawBody !== undefined ? rawBody : JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  return { status: r.status, j, h: r.headers };
}

const authHeaders = (ip) => ({
  "x-maven-test-secret": TEST_SECRET,
  "x-maven-test-user": TEST_USER,
  ...(ip ? { "x-forwarded-for": ip } : {}),
});

const errEnvelope = (j, code) => j?.schemaVersion === 1 && j?.error?.code === code && typeof j?.error?.message === "string";
const noLeak = (j) => !/deepseek|openai|supabase|upstash|stack|econnrefused|jwt/i.test(JSON.stringify(j));

if (MODE === "default") {
  const a = await post("/api/ask", { query: "hi" });
  check("web /api/ask unchanged (200 + answer)", a.status === 200 && !!a.j.type, `status=${a.status}`);
  check("web response carries X-Request-Id", !!a.h.get("x-request-id"));

  const m = await post("/api/mobile/ask", { query: "hi" });
  check("mobile without token -> 401 UNAUTHENTICATED", m.status === 401 && errEnvelope(m.j, "UNAUTHENTICATED"), JSON.stringify(m.j));
  check("mobile 401 carries X-Request-Id", !!m.h.get("x-request-id"));

  const mal = await post("/api/mobile/ask", null, { Authorization: "Bearer not-a-jwt" }, JSON.stringify({ query: "hi" }));
  check("malformed bearer -> 401 UNAUTHENTICATED", mal.status === 401 && errEnvelope(mal.j, "UNAUTHENTICATED"), `status=${mal.status}`);

  const badJson = await post("/api/mobile/ask", null, {}, "{not json");
  check("invalid JSON -> 400 INVALID_REQUEST", badJson.status === 400 && errEnvelope(badJson.j, "INVALID_REQUEST"));

  const noQ = await post("/api/mobile/ask", {});
  check("missing query -> 400 INVALID_REQUEST", noQ.status === 400 && errEnvelope(noQ.j, "INVALID_REQUEST"));

  const bigCtx = await post("/api/mobile/ask", { query: "hi", conversationContext: { turns: Array.from({ length: 11 }, (_, i) => ({ id: `t${i}`, userQuery: "x" })) } });
  check("oversized context turns -> 400 INVALID_REQUEST", bigCtx.status === 400 && errEnvelope(bigCtx.j, "INVALID_REQUEST"));

  check("no provider/internal leakage in error bodies", [m, mal, badJson, noQ, bigCtx].every((x) => noLeak(x.j)));
} else if (MODE === "enforce") {
  // Valid (test-only) identity reaches the SAME brain: envelope + semantics intact.
  const ok = await post("/api/mobile/ask", { query: "hi" }, authHeaders("9.9.9.1"));
  check("verified identity reaches answerQuestion (schemaVersion+answer)", ok.status === 200 && ok.j.schemaVersion === 1 && !!ok.j.answer?.type, `status=${ok.status}`);

  const refusal = await post("/api/mobile/ask", { query: "which stock should I buy?" }, authHeaders("9.9.9.2"));
  check("safety refusal intact through wrapper", refusal.j?.answer?.type === "unsafe_advice", `type=${refusal.j?.answer?.type}`);

  // Daily user quota (MOBILE_USER_DAILY_MAX=2; the two calls above consumed it) - NEW IP must NOT reset it.
  const third = await post("/api/mobile/ask", { query: "hi" }, authHeaders("77.77.77.77"));
  check("daily user quota NOT bypassed by new IP", third.status === 429 && errEnvelope(third.j, "RATE_LIMITED"), `status=${third.status}`);
  check("429 carries Retry-After header", !!third.h.get("retry-after"));

  // Web anonymous burst (WEB_ANON_BURST_MAX=3): 4th rapid anonymous request -> 429 legacy shape.
  let lastWeb = null;
  for (let i = 0; i < 4; i++) lastWeb = await post("/api/ask", { query: "hi" }, { "x-forwarded-for": "8.8.8.8" });
  check("web anonymous burst limits (legacy {error} shape)", lastWeb.status === 429 && typeof lastWeb.j.error === "string", `status=${lastWeb.status}`);

  // Eval bypass defeats rate limits (but NOT auth: bypass without identity still 401).
  const bypassNoAuth = await post("/api/mobile/ask", { query: "hi" }, { "x-maven-eval-token": BYPASS });
  check("eval bypass does NOT bypass auth", bypassNoAuth.status === 401, `status=${bypassNoAuth.status}`);
  const bypassAuthed = await post("/api/mobile/ask", { query: "hi" }, { ...authHeaders(), "x-maven-eval-token": BYPASS });
  check("eval bypass + identity defeats quota", bypassAuthed.status === 200, `status=${bypassAuthed.status}`);
  const wrong = await post("/api/mobile/ask", { query: "hi" }, { ...authHeaders("9.9.9.3"), "x-maven-eval-token": "wrong" });
  check("wrong bypass token stays limited", wrong.status === 429, `status=${wrong.status}`);
} else {
  // prodsim: VERCEL=1, no Upstash -> durable limiter missing -> mobile fails CLOSED.
  const m = await post("/api/mobile/ask", { query: "hi" });
  check("prod without durable limiter -> 503 SERVICE_UNAVAILABLE", m.status === 503 && errEnvelope(m.j, "SERVICE_UNAVAILABLE"), JSON.stringify(m.j));
  const t = await post("/api/mobile/ask", { query: "hi" }, authHeaders());
  check("test-only auth is IMPOSSIBLE in production", t.status === 503, `status=${t.status} (headers ignored)`);
  check("no leakage in prodsim errors", noLeak(m.j) && noLeak(t.j));
}

console.log(`\n${fails === 0 ? "ALL PASS" : fails + " FAILED"} (${MODE} mode)`);
process.exit(fails ? 1 : 0);
