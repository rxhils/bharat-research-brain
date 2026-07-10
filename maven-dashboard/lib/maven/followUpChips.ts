// Answer-type-aware follow-up chips. Deterministic sets per answer type so chips always teach
// the user what Maven can actually do next (summaries, sectors, flows, filings, charts) instead
// of generic filler. Also filters generic/unsafe chips out of any generated answer.

import type { AnswerType, MavenAnswer } from "./types";

const MARKET_CHIPS = [
  "Which individual stocks drove this?",
  "Which sectors drove the move?",
  "Give me a bullet-point recap",
  "What changed for Bank Nifty?",
];

const LEADERBOARD_CHIPS = [
  "Why did these stocks move?",
  "Show top losers too",
  "Most active stocks today",
  "Summarize this in bullets",
];

const STOCK_CHIPS = [
  "Show latest filings",
  "Summarize this in bullets",
  "Compare with closest peer",
  "What are the key risks?",
];

const MACRO_CHIPS = [
  "Show sector winners and losers",
  "What does this mean for banks?",
  "Explain the rupee impact",
  "Give me a chart view",
];

const SOURCE_CHIPS = [
  "Show only sources",
  "What data was missing?",
  "Which claims are official-source backed?",
];

const COMPARISON_CHIPS = [
  "Show this in a chart",
  "Summarize this in bullets",
  "What are the key risks for both?",
  "Which metrics differ most?",
];

const CONCEPT_CHIPS = [
  "Give me an Indian market example",
  "Why does this matter for investors?",
  "Explain this simply",
];

// Chips Maven must never suggest: content-free or advice-shaped.
const GENERIC_OR_UNSAFE = /^(tell me more|more|what is the market\??|how can i invest\??|what should i buy\??|any tips\??|ok|thanks?)$/i;

export function chipsForAnswerType(answerType: AnswerType | undefined, sourceHeavy = false): string[] {
  if (sourceHeavy) return SOURCE_CHIPS;
  switch (answerType) {
    case "single_stock_research":
    case "deep_research_report":
      return STOCK_CHIPS;
    case "stock_comparison":
    case "comparison_research_report":
      return COMPARISON_CHIPS;
    case "stock_leaderboard":
      return LEADERBOARD_CHIPS;
    case "macro_sector_impact":
      return MACRO_CHIPS;
    case "basic_concept":
      return CONCEPT_CHIPS;
    case "current_market_research":
    case "market_mechanism":
    default:
      return MARKET_CHIPS;
  }
}

/**
 * Enforce chip quality on a finished answer: drop generic/unsafe chips, dedupe, and top up
 * from the answer-type set so the user always gets >= 3 useful next steps.
 */
export function enforceFollowUpChips(answer: MavenAnswer): MavenAnswer {
  const sourceHeavy = (answer.evidence?.officialSourceCount ?? 0) >= 3 || (answer.sources?.length ?? 0) >= 6;
  const pool = chipsForAnswerType(answer.type, false);
  const kept = (answer.followUps ?? [])
    .filter((f) => typeof f === "string" && f.trim() && !GENERIC_OR_UNSAFE.test(f.trim()))
    .slice(0, 4);
  const merged = [...kept];
  for (const c of [...pool, ...(sourceHeavy ? ["Show only sources"] : [])]) {
    if (merged.length >= 4) break;
    if (!merged.some((m) => m.toLowerCase() === c.toLowerCase())) merged.push(c);
  }
  return { ...answer, followUps: merged.slice(0, 4) };
}
