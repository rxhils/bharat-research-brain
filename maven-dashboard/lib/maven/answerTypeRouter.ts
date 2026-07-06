import type { AnswerType, DisclaimerLevel } from "./types";
import { isAdviceRequest } from "../guard";
import { resolveStock } from "./stockResolver";
import { normalizeForClassification } from "./queryNormalizer";

// Matches messages made ONLY of greeting words/phrases, incl. compounds like "hi good morning".
const GREETING = /^\s*(?:(?:hi+|hello+|hey+|yo+|hiya|namaste|sup|gm|good\s+(?:morning|afternoon|evening|night))[\s,!.]*)+$/i;
const GREETING_TIME = /good\s+(morning|afternoon|evening|night)/i;
// Requests to introduce/explain Maven itself - these don't need "Indian markets" in the text.
const INTRO_REQUEST = /\bwhat can (you|maven) do\b|\bwho are you\b|\bhow do(?:es)? (?:you|maven) work\b|\bwhat do you do\b|\bwhat is maven\b|\bintroduce yourself\b|\bhelp me get started\b|\bget started\b/i;
const OUT = /(polymarket|prediction market|crypto|bitcoin|ethereum|\bbtc\b|\beth\b|dogecoin|\bsolana\b|us stock|u\.s\. stock|nasdaq|dow jones|s&p ?500|tesla|nvidia|forex|gambl|bett?ing|casino|sportsbook|premier league|football|us market|u\.s\. market|american market|wall street|global market|world market|european market|asian market|uk market|china market|hong kong market|japan market)/i;
const FNO = /(f&o|f and o|futures|options|leverage|margin trade|intraday tip|call option|put option|derivative strateg)/i;
const COMPARE = /\b(vs|versus|compare|against|better than)\b/i;
const CONCEPT = /^(what is|what's|whats|define|meaning of|explain (what|the)\b|how does .* work)/i;
const CURRENT = /(today|now|this week|currently|latest|right now|moving|movement|summari|market summary|wrap|leading|rally|fell|surg|why is|why are|why did|what should i watch)/i;
const MACRO = /(crude|oil|rupee|usd ?\/? ?inr|yield|g-?sec|\brbi\b|repo|\bfii\b|\bdii\b|monsoon|metal|inflation|\bcpi\b|sector|bank|\bit\b|pharma|auto|fmcg|realty|energy)/i;
const INDIA = /\b(india|indian|nifty|sensex|nse|bse|sebi|stocks?|shares?|equit\w*|market)\b/i;

// Explicitly non-Indian subject (US/crypto/global...) with no India anchor. Exported so the
// follow-up detector can refuse to claim these even mid-conversation.
export function isExplicitlyOutOfScope(query: string): boolean {
  const ln = normalizeForClassification((query || "").trim());
  return OUT.test(ln) && !/\b(india|indian|nifty|sensex|nse|bse|sebi)\b/i.test(ln);
}

export function routeAnswerType(query: string): { answerType: AnswerType; disclaimerLevel: DisclaimerLevel } {
  const s = (query || "").trim();
  const l = s.toLowerCase();
  if (!s) return { answerType: "out_of_scope", disclaimerLevel: "light" };
  if (GREETING.test(s) || INTRO_REQUEST.test(l)) return { answerType: "greeting", disclaimerLevel: "light" };
  if (isAdviceRequest(s) || FNO.test(l) || /\b(price target|target price|stock to buy|stocks? to buy|which stock|multibagger|guaranteed return)\b/i.test(l)) return { answerType: "unsafe_advice", disclaimerLevel: "strong" };
  const ln = normalizeForClassification(s);
  if (isExplicitlyOutOfScope(s)) return { answerType: "out_of_scope", disclaimerLevel: "light" };
  if (COMPARE.test(ln)) return { answerType: "stock_comparison", disclaimerLevel: "standard" };
  if (resolveStock(s)) return { answerType: "single_stock_research", disclaimerLevel: "standard" };
  if (CONCEPT.test(ln)) return { answerType: "basic_concept", disclaimerLevel: "light" };
  if (CURRENT.test(ln)) return { answerType: "current_market_research", disclaimerLevel: "standard" };
  if (MACRO.test(ln)) return { answerType: "macro_sector_impact", disclaimerLevel: "light" };
  if (INDIA.test(ln)) return { answerType: "market_mechanism", disclaimerLevel: "light" };
  return { answerType: "out_of_scope", disclaimerLevel: "light" };
}

export function greetingTimeOfDay(query: string): "morning" | "afternoon" | "evening" | "night" | null {
  const m = (query || "").toLowerCase().match(GREETING_TIME);
  return (m ? m[1] : null) as "morning" | "afternoon" | "evening" | "night" | null;
}

export function disclaimerText(level: DisclaimerLevel): string {
  switch (level) {
    case "none": return "";
    case "light": return "Educational market context.";
    case "standard": return "Educational market context, not investment advice.";
    case "strong": return "Maven explains mechanisms only - no buy/sell/hold advice, price targets or tips. Consider your own goals and risk profile.";
  }
}