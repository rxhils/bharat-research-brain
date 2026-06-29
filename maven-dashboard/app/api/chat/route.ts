import { NextResponse } from "next/server";
import { answerFor } from "@/lib/mock-chat";
import { deepseekAnswer } from "@/lib/deepseek";
import { isAdviceRequest, refusalAnswer } from "@/lib/guard";

// Live DeepSeek when DEEPSEEK_API_KEY is set (server-side); otherwise a structured
// preview answer. Advice/buy-sell asks are refused deterministically before the model.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  const subject = typeof body?.subject === "string" ? body.subject : undefined;
  if (isAdviceRequest(query)) return NextResponse.json(refusalAnswer(query));
  const live = await deepseekAnswer(query, subject);
  return NextResponse.json(live ?? answerFor(query, subject));
}