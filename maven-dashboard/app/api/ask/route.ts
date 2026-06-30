import { NextResponse } from "next/server";
import { routeAnswerType } from "@/lib/maven/answerTypeRouter";
import { classifyIntent } from "@/lib/maven/intentClassifier";
import { planResearch } from "@/lib/maven/researchPlanner";
import { buildContextPack } from "@/lib/maven/contextPackBuilder";
import { generateAnswer } from "@/lib/maven/mavenAnswerGenerator";
import { validateAnswer } from "@/lib/maven/answerValidator";
import { scoreAnswer } from "@/lib/maven/answerQualityScorer";
import type { MavenAnswer } from "@/lib/maven/types";

export const dynamic = "force-dynamic";

const GREETING: MavenAnswer = {
  type: "greeting", disclaimerLevel: "none",
  headline: "Welcome to Maven.",
  summary: "Ask about Indian markets, sectors, flows, RBI policy, crude, rupee, or NSE/BSE stocks. Maven explains the mechanism with data, sources, and charts where useful.",
  keyData: [], charts: [], blocks: [], sources: [],
  followUps: ["Summarize today's Indian market", "Why is Bank Nifty moving?", "How does crude affect Indian sectors?"],
  disclaimer: "",
};

const REFUSAL: MavenAnswer = {
  type: "unsafe_advice", disclaimerLevel: "strong",
  headline: "I can explain the setup, but I cannot tell you to buy or sell",
  summary: "Maven explains market mechanisms, not recommendations - no buy/sell/hold calls, price targets, or F&O/leverage strategies. Ask why something is moving and Maven will break down the drivers and risks.",
  keyData: [], charts: [],
  blocks: [
    { type: "POINT", title: "What Maven can do", body: "Explain why a stock, sector or index is moving, the macro and flows behind it, and the risks on both sides." },
    { type: "RISK", title: "Why no call", body: "A recommendation depends on your goals, horizon and risk tolerance, which Maven does not know." },
    { type: "TAKEAWAY", title: "India context", body: "Ask 'why is X moving' or 'what should I watch on X'. Maven explains mechanisms only - no buy/sell/hold advice, price targets or tips." },
  ],
  sources: [{ name: "Maven policy", type: "policy", confidence: "analysis_only" }],
  followUps: ["Why is this moving?", "What are the risks here?", "Explain the macro backdrop"],
  disclaimer: "Maven explains mechanisms only - no buy/sell/hold advice, price targets or tips.",
};

function outOfScope(query: string): MavenAnswer {
  const l = query.toLowerCase();
  let followUps = ["How would this affect Indian equities?", "Which Indian sectors are sensitive to global risk?", "How does this move the rupee or crude?"];
  if (/polymarket|election|odds|prediction/.test(l)) followUps = ["How would election odds affect Indian equities?", "How do event probabilities differ from market pricing?", "Which Indian sectors are sensitive to political risk?"];
  else if (/crypto|bitcoin|ethereum|\bbtc\b|\beth\b/.test(l)) followUps = ["How does global risk appetite affect Indian equities?", "Do crypto swings move Indian fintech or exchanges?", "How does the dollar affect the rupee and FII flows?"];
  return {
    type: "out_of_scope", disclaimerLevel: "light",
    headline: "Maven focuses on Indian markets",
    summary: "Maven focuses on Indian markets. I can help if you want to understand how this affects Indian equities, sectors, the rupee, crude, rates, or macro.",
    keyData: [], charts: [], blocks: [], sources: [{ name: "Maven", type: "policy", confidence: "analysis_only" }],
    followUps, disclaimer: "Educational market context.",
  };
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400 });

  const { answerType, disclaimerLevel } = routeAnswerType(query);
  if (answerType === "greeting") return NextResponse.json(GREETING);
  if (answerType === "unsafe_advice") return NextResponse.json(REFUSAL);
  if (answerType === "out_of_scope") return NextResponse.json(outOfScope(query));

  const intent = classifyIntent(query);
  const plan = planResearch(query, intent);
  const pack = await buildContextPack(query, plan, answerType, disclaimerLevel);

  let { fixed } = validateAnswer(await generateAnswer(pack), pack);
  const first = scoreAnswer(fixed, pack).score;
  if (first < 80) {
    try {
      const v2 = validateAnswer(await generateAnswer(pack, true), pack);
      if (scoreAnswer(v2.fixed, pack).score > first) fixed = v2.fixed;
    } catch { /* keep first */ }
  }
  fixed.type = answerType;
  fixed.disclaimerLevel = disclaimerLevel;
  return NextResponse.json(fixed);
}