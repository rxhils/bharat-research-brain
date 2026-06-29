import { NextResponse } from "next/server";
import { answerFor } from "@/lib/mock-chat";
import { deepseekAnswer } from "@/lib/deepseek";

// Live DeepSeek when DEEPSEEK_API_KEY is set (server-side); otherwise a structured
// preview answer so the chat always works.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  const subject = typeof body?.subject === "string" ? body.subject : undefined;
  const live = await deepseekAnswer(query, subject);
  return NextResponse.json(live ?? answerFor(query, subject));
}