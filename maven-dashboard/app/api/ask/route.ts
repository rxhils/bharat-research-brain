import { NextResponse } from "next/server";
import { answerQuestion, MAX_QUERY_CHARS } from "@/lib/maven/answerQuestion";
import { checkApiGuard } from "@/lib/maven/apiGuard";
import { apiLog, newRequestId } from "@/lib/maven/apiLog";

export const dynamic = "force-dynamic";

// Thin HTTP wrapper over the shared Maven brain (lib/maven/answerQuestion.ts).
// Identity + quota live in the guard: authenticated users meter durable daily usage via
// usage_events under their own JWT; anonymous (web guest mode, evals) stays allowed but
// burst-limited. Web keeps its legacy { error } failure shape for the existing UI; every
// response carries X-Request-Id. The brain itself is identity-free and unchanged.
export async function POST(req: Request) {
  const requestId = newRequestId();
  const t0 = Date.now();

  const guard = await checkApiGuard(req, "/api/ask", requestId);
  if (!guard.ok) {
    const headers: Record<string, string> = { "X-Request-Id": requestId };
    if (guard.retryAfterSeconds != null) headers["Retry-After"] = String(guard.retryAfterSeconds);
    return NextResponse.json(
      { error: guard.message, ...(guard.retryAfterSeconds != null ? { retryAfterSeconds: guard.retryAfterSeconds } : {}) },
      { status: guard.status, headers },
    );
  }

  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query.slice(0, MAX_QUERY_CHARS) : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400, headers: { "X-Request-Id": requestId } });

  const answer = await answerQuestion(query, body?.conversationContext);
  apiLog({ evt: "complete", requestId, route: "/api/ask", authenticated: guard.identity.kind === "user", answerType: (answer as any)?.type, latencyMs: Date.now() - t0 });
  return NextResponse.json(answer, { headers: { "X-Request-Id": requestId } });
}
