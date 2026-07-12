import { NextResponse } from "next/server";
import { answerQuestion, MAX_QUERY_CHARS } from "@/lib/maven/answerQuestion";

export const dynamic = "force-dynamic";

// Mobile-safe wrapper over the SAME Maven brain as /api/ask (lib/maven/answerQuestion.ts).
// It adds no answer logic - it only: parses the request, rate-limits, calls answerQuestion(),
// wraps the result in a versioned envelope, and returns clean errors (never backend/provider text).

// --- simple in-memory rate limit (PLACEHOLDER) -----------------------------------------------
// Blunts abuse from a single client. NOTE: an in-memory Map resets on serverless cold start and
// is not shared across instances - swap for a durable store (Upstash/Supabase) keyed by the
// verified user id before real production load. Kept intentionally minimal for v1.
const RATE_LIMIT = 40; // requests per window
const RATE_WINDOW_MS = 60 * 60_000; // 1 hour
const hits = new Map<string, { count: number; windowStart: number }>();

function rateLimited(id: string): boolean {
  const now = Date.now();
  const rec = hits.get(id);
  if (!rec || now - rec.windowStart > RATE_WINDOW_MS) {
    hits.set(id, { count: 1, windowStart: now });
    return false;
  }
  rec.count += 1;
  return rec.count > RATE_LIMIT;
}

// Identity for rate-limiting. Once auth lands this becomes the verified user id; until then it is
// a best-effort client IP from proxy headers. userId is deliberately NOT read from the body - a
// client could spoof it to bypass the limit or impersonate another user.
function clientId(req: Request): string {
  const fwd = req.headers.get("x-forwarded-for") ?? "";
  return fwd.split(",")[0].trim() || req.headers.get("x-real-ip") || "anon";
}

export async function POST(req: Request) {
  try {
    // TODO(auth): verify a Google ID token from the Authorization header and derive userId from it
    //   const userId = await verifyGoogleIdToken(req.headers.get("authorization"));
    //   if (!userId) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    //   ...then rate-limit + persist history by that verified userId. NEVER trust body.userId.
    const id = clientId(req);
    if (rateLimited(id)) {
      return NextResponse.json({ error: "rate limit exceeded, please try again later" }, { status: 429 });
    }

    const body = await req.json().catch(() => ({}));
    const query = typeof body?.query === "string" ? body.query.slice(0, MAX_QUERY_CHARS) : "";
    if (!query.trim()) return NextResponse.json({ error: "query is required" }, { status: 400 });

    const answer = await answerQuestion(query, body?.conversationContext);
    return NextResponse.json({ schemaVersion: 1, answer });
  } catch {
    // Never surface backend/provider/model/stack errors to the mobile client.
    return NextResponse.json({ error: "temporarily unavailable" }, { status: 503 });
  }
}
