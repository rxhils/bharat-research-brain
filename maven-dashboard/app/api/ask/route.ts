import { NextResponse } from "next/server";
import { answerQuestion, MAX_QUERY_CHARS } from "@/lib/maven/answerQuestion";

export const dynamic = "force-dynamic";

// Thin HTTP wrapper over the shared Maven brain (lib/maven/answerQuestion.ts). Behavior is
// identical to the previous inline handler - the full pipeline moved into answerQuestion()
// unchanged; only the NextResponse.json() wrapping stays here.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query.slice(0, MAX_QUERY_CHARS) : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400 });
  return NextResponse.json(await answerQuestion(query, body?.conversationContext));
}
