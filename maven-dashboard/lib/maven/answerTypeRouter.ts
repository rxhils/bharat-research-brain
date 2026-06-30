import type { AnswerType, DisclaimerLevel } from "./types";
import { isAdviceRequest } from "../guard";

const GREETING = /^\s*(hi+|hello+|hey+|yo+|hiya|namaste|sup|good (morning|afternoon|evening))\b[\s!.,]*$/i;
const OUT = /(polymarket|prediction market|crypto|bitcoin|ethereum|\bbtc\b|\beth\b|dogecoin|\bsolana\b|us stock|u\.s\. stock|nasdaq|dow jones|s&p ?500|tesla|nvidia|forex|gambl|bett?ing|casino|sportsbook|premier league|football)/i;
const FNO = /(f&o|f and o|futures|options|leverage|margin trade|intraday tip|call option|put option|derivative strateg)/i;
const COMPARE = /\b(vs|versus|compare|against|better than)\b/i;
const CONCEPT = /^(what is|what's|whats|define|meaning of|explain (what|the)\b|how does .* work)/i;
const CURRENT = /(today|now|this week|currently|latest|right now|moving|movement|summari|wrap|leading|rally|fell|surg|why is|why are|why did|what should i watch)/i;
const MACRO = /(crude|oil|rupee|usd ?\/? ?inr|yield|g-?sec|\brbi\b|repo|\bfii\b|\bdii\b|monsoon|metal|inflation|\bcpi\b|sector|bank|\bit\b|pharma|auto|fmcg|realty|energy)/i;
const INDIA = /(india|indian|nifty|sensex|\bnse\b|\bbse\b|sebi|stock|share|market|equit)/i;

export function routeAnswerType(query: string): { answerType: AnswerType; disclaimerLevel: DisclaimerLevel } {
  const s = (query || "").trim();
  const l = s.toLowerCase();
  if (!s) return { answerType: "out_of_scope", disclaimerLevel: "light" };
  if (GREETING.test(s)) return { answerType: "greeting", disclaimerLevel: "none" };
  if (isAdviceRequest(s) || FNO.test(l)) return { answerType: "unsafe_advice", disclaimerLevel: "strong" };
  if (OUT.test(l) && !INDIA.test(l)) return { answerType: "out_of_scope", disclaimerLevel: "light" };
  if (COMPARE.test(l) && INDIA.test(l)) return { answerType: "stock_comparison", disclaimerLevel: "standard" };
  if (CONCEPT.test(l)) return { answerType: "basic_concept", disclaimerLevel: "light" };
  if (CURRENT.test(l)) return { answerType: "current_market_research", disclaimerLevel: "standard" };
  if (MACRO.test(l)) return { answerType: "macro_sector_impact", disclaimerLevel: "light" };
  if (INDIA.test(l)) return { answerType: "market_mechanism", disclaimerLevel: "light" };
  return { answerType: "out_of_scope", disclaimerLevel: "light" };
}

export function disclaimerText(level: DisclaimerLevel): string {
  switch (level) {
    case "none": return "";
    case "light": return "Educational market context.";
    case "standard": return "Educational market context, not investment advice.";
    case "strong": return "Maven explains mechanisms only - no buy/sell/hold advice, price targets or tips. Consider your own goals and risk profile.";
  }
}