import { NextResponse } from "next/server";
import { routeAnswerType, greetingTimeOfDay } from "@/lib/maven/answerTypeRouter";
import { resolveStockEntity } from "@/lib/maven/stockResolver";
import { classifyIntent } from "@/lib/maven/intentClassifier";
import { planResearch } from "@/lib/maven/researchPlanner";
import { buildContextPack } from "@/lib/maven/contextPackBuilder";
import { generateAnswer } from "@/lib/maven/mavenAnswerGenerator";
import { validateAnswer } from "@/lib/maven/answerValidator";
import { scoreAnswer } from "@/lib/maven/answerQualityScorer";
import { detectReportMode } from "@/lib/maven/reportModeDetector";
import { generateDeepResearchReport } from "@/lib/maven/deepResearchReportGenerator";
import { buildConversationState, findTurnWith } from "@/lib/maven/conversationState";
import { detectFollowUpIntent, looksLikeBareFollowUp } from "@/lib/maven/followUpIntentDetector";
import { rewriteContextualQuery } from "@/lib/maven/contextualQueryRewriter";
import { routeAnswerMode, isTransformationMode } from "@/lib/maven/answerModeRouter";
import {
  transformToBulletSummary, transformToShortAnswer, transformToTable,
  transformToSourceList, transformToChartFirst, transformToSimpleExplanation,
} from "@/lib/maven/answerTransformer";
import { enforceFollowUpChips } from "@/lib/maven/followUpChips";
import type { MavenConversationTurn } from "@/lib/maven/conversationState";
import type { AnswerType, DisclaimerLevel, MavenAnswer, MavenAnswerMode } from "@/lib/maven/types";
import { containsAdviceAssertion } from "@/lib/guard";

export const dynamic = "force-dynamic";

const MAX_QUERY_CHARS = 2000; // hard input cap - a question is never this long, an abuse payload is

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

// A follow-up-shaped request ("give me a bullet point summary") arrived with nothing to refer
// back to. Ask what to work on instead of showing the out-of-scope redirect.
function noContextCard(): MavenAnswer {
  return {
    type: "market_mechanism", disclaimerLevel: "light", answerMode: "clarification_answer",
    headline: "What should Maven work with?",
    summary: "There is no previous Maven answer in this conversation yet. Ask a market, sector, stock, or macro question first, and Maven can then summarize, tabulate, chart, or list sources for that answer.",
    keyData: [], charts: [], blocks: [], sources: [],
    followUps: GREETING_FOLLOWUPS.slice(0, 4),
    disclaimer: "Educational market context only. Not investment advice.",
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

/**
 * The existing research pipeline (ambiguity gate -> intent -> plan -> context pack -> report
 * mode / LLM generate -> validate -> score), factored out so both the normal path and the
 * research-backed follow-up path (rewritten queries) run the exact same flow.
 */
async function research(query: string, answerType: AnswerType, disclaimerLevel: DisclaimerLevel): Promise<MavenAnswer> {
  // Ambiguous company name (e.g. multiple entities share a brand) -> ask, never guess.
  if (answerType !== "stock_comparison") {
    const amb = resolveStockEntity(query);
    if (amb.status === "ambiguous" && amb.candidates && amb.candidates.length > 1) {
      return clarify(query, amb.candidates.map((c) => ({ symbol: c.symbol, name: c.companyName })));
    }
  }

  const intent = classifyIntent(query);
  const plan = planResearch(query, intent);
  const pack = await buildContextPack(query, plan, answerType, disclaimerLevel);

  // Deep Research Report Mode: explicit "full report / deep research / in detail" phrasing on a
  // company or comparison question. Reuses the exact same context pack (official-source-first
  // retrieval, freshness lock, evidence system) - only the final shaping differs, and the
  // deterministic assembler never calls the LLM, so there is no new hallucination surface.
  const report = detectReportMode(query, answerType);

  let fixed: MavenAnswer;
  if (report.reportMode) {
    fixed = validateAnswer(generateDeepResearchReport(pack, report.reportType as "company_deep_research" | "stock_comparison_report"), pack).fixed;
  } else {
    const first = validateAnswer(await generateAnswer(pack), pack);
    fixed = first.fixed;
    const firstScore = scoreAnswer(fixed, pack).score;
    if (firstScore < 80) {
      try {
        const v2 = validateAnswer(await generateAnswer(pack, true), pack);
        if (scoreAnswer(v2.fixed, pack).score > firstScore) fixed = v2.fixed;
      } catch { /* keep first */ }
    }
  }
  fixed.type = report.reportMode ? (report.reportType === "stock_comparison_report" ? "comparison_research_report" : "deep_research_report") : answerType;
  fixed.disclaimerLevel = disclaimerLevel;
  // merge pack limitations with any added by validation (e.g. freshness-lock removals)
  fixed.limitations = [...new Set([...pack.limitations, ...(fixed.limitations ?? [])])];
  return fixed;
}

function transformPrevious(mode: MavenAnswerMode, prev: MavenConversationTurn): MavenAnswer {
  switch (mode) {
    case "bullet_summary": return transformToBulletSummary(prev);
    case "short_answer": return transformToShortAnswer(prev);
    case "table": return transformToTable(prev);
    case "source_list": return transformToSourceList(prev);
    case "chart_first": return transformToChartFirst(prev);
    default: return transformToSimpleExplanation(prev);
  }
}

// Output-side advice net for the transformation path. conversationContext is CLIENT input: a
// crafted "previous answer" could carry a buy/sell assertion that a transformation would
// otherwise regurgitate under Maven's name. If any visible text asserts advice, fail closed
// to the standard refusal. (The research path has its own validator; this covers the only
// path that echoes client-supplied content.)
function transformedAnswerAssertsAdvice(a: MavenAnswer): boolean {
  const visible = [
    a.headline, a.summary,
    ...(a.bullets ?? []),
    ...(a.blocks ?? []).flatMap((b) => [b.title, b.body]),
    ...(a.keyData ?? []).flatMap((d) => [d.label, d.value, d.change ?? ""]),
    ...(a.charts ?? []).map((c) => JSON.stringify(c.data ?? [])),
    ...(a.limitations ?? []),
  ].join("\n");
  return containsAdviceAssertion(visible);
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const query = typeof body?.query === "string" ? body.query.slice(0, MAX_QUERY_CHARS) : "";
  if (!query.trim()) return NextResponse.json({ error: "empty query" }, { status: 400 });

  const convo = buildConversationState(body?.conversationContext);

  const { answerType, disclaimerLevel } = routeAnswerType(query);
  if (answerType === "greeting") return NextResponse.json(greeting(query));
  // Safety first, and BEFORE follow-up handling: a formatting request can never soften or
  // reformat its way past the advice refusal ("give me a stock to buy then summarize in bullets").
  if (answerType === "unsafe_advice") return NextResponse.json(REFUSAL);

  // Refusals are sticky: "summarize in bullets" right after an advice refusal reformats
  // nothing - the refusal stands. (The refusal itself is the only content to summarize.)
  const lastTurnType = convo.turns[convo.turns.length - 1]?.answerType;
  if (lastTurnType === "unsafe_advice" && looksLikeBareFollowUp(query)) return NextResponse.json(REFUSAL);

  // Conversation intelligence: is this a follow-up on the previous Maven answer?
  const followUp = detectFollowUpIntent(query, convo);
  if (followUp.isFollowUp && followUp.confidence !== "low" && convo.lastAnswer) {
    const mode = routeAnswerMode(query, followUp);
    if (isTransformationMode(mode)) {
      // Pure presentation change of the previous answer: no refetch, no new facts possible.
      // Chart/table/source transforms anchor on the most recent turn that HAS that data, so
      // "bullet summary" then "chart it" reaches the market answer, not the summary card.
      const anchor =
        mode === "chart_first" || mode === "table" ? findTurnWith(convo, "charts") ?? convo.lastAnswer
        : mode === "source_list" ? findTurnWith(convo, "sources") ?? convo.lastAnswer
        : convo.lastAnswer;
      const transformed = transformPrevious(mode, anchor);
      if (transformedAnswerAssertsAdvice(transformed)) return NextResponse.json(REFUSAL);
      return NextResponse.json(enforceFollowUpChips(transformed));
    }
    // Research-backed follow-up (entity/time/expand/clarification): rewrite to a standalone
    // query (internal only) and run the normal pipeline. The rewritten query goes through the
    // same routing gates, so advice and explicit non-India subjects still refuse/redirect.
    const { rewrittenQuery, usedContext } = rewriteContextualQuery(query, convo, followUp);
    const effective = usedContext ? rewrittenQuery : query;
    const routed = routeAnswerType(effective);
    if (routed.answerType === "unsafe_advice") return NextResponse.json(REFUSAL);
    if (routed.answerType !== "out_of_scope" && routed.answerType !== "greeting") {
      const answer = await research(effective, routed.answerType, routed.disclaimerLevel);
      answer.answerMode = mode;
      return NextResponse.json(enforceFollowUpChips(answer));
    }
    // fall through: rewritten query landed out of scope - handle the original query normally
  }

  if (answerType === "out_of_scope") {
    // Bare follow-up phrasing with no conversation context gets guidance, not the scope card.
    if (looksLikeBareFollowUp(query)) return NextResponse.json(noContextCard());
    return NextResponse.json(outOfScope(query));
  }

  return NextResponse.json(await research(query, answerType, disclaimerLevel));
}
