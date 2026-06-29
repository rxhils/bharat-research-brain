import { NextResponse } from "next/server";
import { answerFor } from "@/lib/mock-chat";
import { deepseekAnswer } from "@/lib/deepseek";
import { isAdviceRequest, refusalAnswer } from "@/lib/guard";
import { sanitizeAnswer } from "@/lib/maven-visibility";

// Maven answer engine. Advice/buy-sell asks are refused deterministically before reasoning.
// Every response is scrubbed of any provider/infra/preview terms before it leaves the server.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  const subject = typeof body?.subject === "string" ? body.subject : undefined;
  if (isAdviceRequest(query)) return NextResponse.json(sanitizeAnswer(refusalAnswer(query)));
  const live = await deepseekAnswer(query, subject);
  return NextResponse.json(sanitizeAnswer(live ?? answerFor(query, subject)));
}