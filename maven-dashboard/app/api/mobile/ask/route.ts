import { NextResponse } from "next/server";
import { answerQuestion, MAX_QUERY_CHARS } from "@/lib/maven/answerQuestion";
import { checkMobileGuard, type GuardFail } from "@/lib/maven/apiGuard";
import { apiLog, newRequestId } from "@/lib/maven/apiLog";

export const dynamic = "force-dynamic";

// Mobile wrapper over the SAME Maven brain as /api/ask (lib/maven/answerQuestion.ts).
// Adds NO answer logic. Contract:
//   success: { schemaVersion: 1, answer: <MavenAnswer> }
//   failure: { schemaVersion: 1, error: { code, message, retryAfterSeconds? } }
//   codes:   INVALID_REQUEST | UNAUTHENTICATED | FORBIDDEN | RATE_LIMITED | SERVICE_UNAVAILABLE | INTERNAL_ERROR
// Every response carries X-Request-Id; 429s carry Retry-After. Identity is a verified Supabase
// access token (Authorization: Bearer) - client-supplied ids are never trusted. Durable shared
// rate limits are REQUIRED in production (fail-closed 503 when unconfigured). No provider/model/
// stack detail ever reaches the client; logging is structured and token/body-free (apiLog).

const ROUTE = "/api/mobile/ask";
const MAX_CONTEXT_TURNS = 10;        // sanitizer uses the last 3; reject absurd payloads early
const MAX_BODY_CHARS = 262_144;      // 256 KB raw JSON cap

function fail(requestId: string, status: number, code: string, message: string, retryAfterSeconds?: number) {
  const headers: Record<string, string> = { "X-Request-Id": requestId };
  if (retryAfterSeconds != null) headers["Retry-After"] = String(retryAfterSeconds);
  return NextResponse.json(
    { schemaVersion: 1, error: { code, message, ...(retryAfterSeconds != null ? { retryAfterSeconds } : {}) } },
    { status, headers },
  );
}

export async function POST(req: Request) {
  const requestId = newRequestId();
  const t0 = Date.now();
  apiLog({ evt: "request_start", requestId, route: ROUTE });

  try {
    // ---- strict body validation (INVALID_REQUEST on any malformed input) ----
    const raw = await req.text().catch(() => "");
    if (!raw || raw.length > MAX_BODY_CHARS) {
      apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: "invalid_request" });
      return fail(requestId, 400, "INVALID_REQUEST", "Request body is missing or too large.");
    }
    let body: any;
    try { body = JSON.parse(raw); } catch {
      apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: "invalid_request" });
      return fail(requestId, 400, "INVALID_REQUEST", "Request body must be valid JSON.");
    }
    const query = typeof body?.query === "string" ? body.query.trim() : "";
    if (!query || query.length > MAX_QUERY_CHARS) {
      apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: "invalid_request" });
      return fail(requestId, 400, "INVALID_REQUEST", `query is required (max ${MAX_QUERY_CHARS} characters).`);
    }
    const ctx = body?.conversationContext;
    if (ctx != null) {
      const turns = (ctx as any)?.turns;
      if (typeof ctx !== "object" || (turns != null && (!Array.isArray(turns) || turns.length > MAX_CONTEXT_TURNS))) {
        apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: "invalid_request" });
        return fail(requestId, 400, "INVALID_REQUEST", "conversationContext is malformed.");
      }
    }

    // ---- identity + durable quotas (fail-closed in production without a durable limiter) ----
    const guard = await checkMobileGuard(req, requestId, query);
    if (!guard.ok) {
      const g = guard as GuardFail;
      const cat = g.code === "RATE_LIMITED" ? "rate_limited" : g.code === "UNAUTHENTICATED" ? "unauthenticated" : "service_unavailable";
      apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: cat as any });
      return fail(requestId, g.status, g.code, g.message, g.retryAfterSeconds);
    }

    // ---- same brain, unchanged semantics ----
    try {
      const answer = await answerQuestion(query, ctx);
      apiLog({ evt: "complete", requestId, route: ROUTE, authenticated: true, answerType: (answer as any)?.type, latencyMs: Date.now() - t0 });
      return NextResponse.json({ schemaVersion: 1, answer }, { headers: { "X-Request-Id": requestId } });
    } finally {
      if (guard.release) await guard.release(); // free the deep-research concurrency slot
    }
  } catch {
    apiLog({ evt: "error", requestId, route: ROUTE, errorCategory: "internal", latencyMs: Date.now() - t0 });
    return fail(requestId, 500, "INTERNAL_ERROR", "Something went wrong. Please try again.");
  }
}
