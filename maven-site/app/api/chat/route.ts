import { NextResponse } from "next/server";
import { answerFor } from "@/lib/mock-chat";
import { deepseekAnswer } from "@/lib/deepseek";
import { sanitizeAnswer } from "@/lib/guardrails";

// Live DeepSeek V4 Pro when DEEPSEEK_API_KEY is set (server-side); otherwise a
// structured preview answer so the UI always works. The guardrail layer runs on
// the final answer regardless of source: it neutralizes hype/guarantee language
// and ensures a risk + educational takeaway are always present.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  const subject = typeof body?.subject === "string" ? body.subject : undefined;
  const live = await deepseekAnswer(query, subject);
  return NextResponse.json(sanitizeAnswer(live ?? answerFor(query, subject)));
}