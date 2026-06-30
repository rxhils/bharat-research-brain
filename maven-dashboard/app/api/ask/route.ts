import { NextResponse } from "next/server";
import { classifyIntent } from "@/lib/maven/intentClassifier";
import { planResearch } from "@/lib/maven/researchPlanner";
import { buildContextPack } from "@/lib/maven/contextPackBuilder";
import { generateAnswer } from "@/lib/maven/mavenAnswerGenerator";
import { validateAnswer } from "@/lib/maven/answerValidator";
import type { MavenAnswer } from "@/lib/maven/types";

export const dynamic = "force-dynamic";

const REFUSAL: MavenAnswer = {
  headline: "I can explain the setup, but I cannot tell you to buy or sell",
  summary: "Maven gives educational market context, not advice - no buy/sell/hold calls, price targets or tips. Ask why something is moving and Maven will explain the drivers and risks.",
  keyData: [],
  charts: [],
  blocks: [
    { type: "POINT", title: "What Maven can do", body: "Explain why a stock or sector is moving, the macro and flows behind it, and the risks on both sides." },
    { type: "RISK", title: "Why no call", body: "A recommendation depends on your goals, risk tolerance and horizon, which Maven does not know." },
    { type: "TAKEAWAY", title: "India context", body: "Ask 'why is X moving' or 'what should I watch on X'. Market mechanism explanation, not investment advice." },
  ],
  sources: [{ name: "Maven policy", recency: "current" }],
  followUps: ["Why is this moving?", "What are the risks here?", "Explain the macro backdrop"],
  disclaimer: "Market mechanism explanation, not investment advice.",
};

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400 });

  const intent = classifyIntent(query);
  if (intent === "unsafe_advice") return NextResponse.json(REFUSAL);

  const plan = planResearch(query, intent);
  const pack = await buildContextPack(query, plan);
  const answer = await generateAnswer(pack);
  const { fixed } = validateAnswer(answer, pack);
  return NextResponse.json(fixed);
}