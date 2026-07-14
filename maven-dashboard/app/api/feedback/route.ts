// Maven Self-Learning Improvement Loop v1 - feedback ingest endpoint.
//
// POST /api/feedback  { query, response?, conversationContext?, feedback, expectedBehavior?, notes? }
// -> classifies the failure, logs a MavenLearningEvent, returns { id, failureTypes, severity }.
//
// Safety: never expose stack traces / internal errors / secrets to the client.

import { NextResponse } from "next/server";
import { classifyFailure } from "@/lib/maven/learningFailureClassifier";
import { logLearningEvent } from "@/lib/maven/learningStore";
import { checkApiGuard } from "@/lib/maven/apiGuard";

export const runtime = "nodejs"; // learningStore uses node:fs

export async function POST(req: Request) {
  try {
    // Public POST endpoint -> burst-guard it like the ask routes (Phase 2).
    const guard = await checkApiGuard(req, "/api/feedback");
    if (!guard.ok) {
      return NextResponse.json(
        { error: guard.message, ...(guard.retryAfterSeconds != null ? { retryAfterSeconds: guard.retryAfterSeconds } : {}) },
        { status: guard.status },
      );
    }

    const body: any = await req.json().catch(() => ({}));
    const query = typeof body?.query === "string" ? body.query.trim() : "";
    if (!query) return NextResponse.json({ error: "query is required" }, { status: 400 });

    const response = body?.response;
    const feedback = body?.feedback;
    const cls = classifyFailure({ query, response, feedback });

    const sources = Array.isArray(response?.sources) ? response.sources : undefined;
    const event = await logLearningEvent({
      userQuery: query,
      answerType: response?.type ?? response?.answerType,
      headline: typeof response?.headline === "string" ? response.headline : undefined,
      summary: typeof response?.summary === "string" ? response.summary : undefined,
      resolvedSymbols: Array.isArray(response?.resolvedSymbols) ? response.resolvedSymbols : undefined,
      sourceCount: typeof response?.sourceCount === "number" ? response.sourceCount : sources?.length,
      clickableSourceCount: sources?.filter((s: any) => /^https?:\/\//i.test(String(s?.url ?? ""))).length,
      chartCount: Array.isArray(response?.charts) ? response.charts.length : undefined,
      limitations: Array.isArray(response?.limitations) ? response.limitations : undefined,
      userFeedback: feedback,
      failureTypes: cls.failureTypes,
      failureExplanation: cls.explanation,
      expectedBehavior: typeof body?.expectedBehavior === "string" ? body.expectedBehavior : undefined,
      severity: cls.severity,
    });

    return NextResponse.json({
      id: event.id,
      failureTypes: event.failureTypes,
      severity: event.severity,
    });
  } catch {
    return NextResponse.json({ error: "feedback could not be logged" }, { status: 500 });
  }
}
