import { NextResponse } from "next/server";
import { routeAnswerType, greetingTimeOfDay } from "@/lib/maven/answerTypeRouter";
import { resolveStockEntity } from "@/lib/maven/stockResolver";
import { classifyIntent } from "@/lib/maven/intentClassifier";
import { planResearch } from "@/lib/maven/researchPlanner";
import { buildContextPack } from "@/lib/maven/contextPackBuilder";
import { generateAnswer } from "@/lib/maven/mavenAnswerGenerator";
import { validateAnswer } from "@/lib/maven/answerValidator";
import { scoreAnswer } from "@/lib/maven/answerQualityScorer";
import type { MavenAnswer } from "@/lib/maven/types";

export const dynamic = "force-dynamic";

const GREETING_FOLLOWUPS = [
  "Summarize today's Indian market",
  "Why is Bank Nifty moving today?",
  "Why is Reliance moving today?",
  "Compare HDFC Bank and ICICI Bank",
  "How do FII flows affect Indian markets?",
  "What sectors benefit from softer crude?",
];

function greeting(query: string): MavenAnswer {
  const tod = greetingTimeOfDay(query);
  const headline = tod ? `Good ${tod} — Maven is ready.` : "Maven is ready.";
  return {
    type: "greeting", disclaimerLevel: "light",
    headline,
    summary: "Maven helps you understand Indian markets by connecting price action, flows, macro data, company news, and sector mechanisms into clear research-style answers.",
    keyData: [], charts: [], blocks: [], sources: [],
    introSections: [
      { title: "What Maven explains", body: "Ask about Nifty, Bank Nifty, Indian sectors, FII/DII flows, RBI policy, crude, rupee, G-Sec yields, or NSE/BSE-listed companies." },
      { title: "How Maven thinks", body: "Maven does not just summarize market moves. It builds a mechanism chain: what happened, what caused it, which variables changed, which sectors or stocks are affected, and what risks could reverse the view." },
      { title: "What Maven can research", body: "For stocks, Maven can look at price action, sector context, company announcements, fundamentals where available, source-backed catalysts, peer comparison, and clean limitations when data is incomplete." },
      { title: "Boundary", body: "Maven explains market context and mechanisms. It does not give buy/sell/hold calls, price targets, or assured-return predictions." },
    ],
    followUps: GREETING_FOLLOWUPS,
    disclaimer: "Educational market context only. Not investment advice.",
  };
}

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

function clarify(query: string, cands: { symbol: string; name: string }[]): MavenAnswer {
  return {
    type: "single_stock_research", disclaimerLevel: "light",
    headline: "Which company did you mean?",
    summary: `Several NSE-listed companies match that name. Pick one and Maven will research it.`,
    keyData: [], charts: [], blocks: [], sources: [],
    introSections: cands.slice(0, 5).map((c) => ({ title: c.name, body: `NSE: ${c.symbol}` })),
    followUps: cands.slice(0, 5).map((c) => `Why is ${c.name} moving today?`),
    disclaimer: "Educational market context only. Not investment advice.",
  };
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400 });

  const { answerType, disclaimerLevel } = routeAnswerType(query);
  if (answerType === "greeting") return NextResponse.json(greeting(query));
  if (answerType === "unsafe_advice") return NextResponse.json(REFUSAL);
  if (answerType === "out_of_scope") return NextResponse.json(outOfScope(query));

  // Ambiguous company name (e.g. multiple entities share a brand) -> ask, never guess.
  if (answerType !== "stock_comparison") {
    const amb = resolveStockEntity(query);
    if (amb.status === "ambiguous" && amb.candidates && amb.candidates.length > 1) {
      return NextResponse.json(clarify(query, amb.candidates.map((c) => ({ symbol: c.symbol, name: c.companyName }))));
    }
  }

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
  fixed.limitations = pack.limitations;
  return NextResponse.json(fixed);
}