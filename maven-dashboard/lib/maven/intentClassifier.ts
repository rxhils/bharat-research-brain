import type { Intent } from "./types";
import { isAdviceRequest } from "../guard";
import { resolveStock } from "./stockResolver";
import { normalizeForClassification } from "./queryNormalizer";

// Fast, deterministic intent classification (no token cost). Heuristic order matters.
export function classifyIntent(query: string): Intent {
  const s = (query || "").toLowerCase();
  if (!s.trim()) return "out_of_scope";
  if (isAdviceRequest(query)) return "unsafe_advice";

  const NAMES = /(hdfc|icici|sbi|axis|kotak|reliance|ril|tcs|infosys|infy|wipro|hcl|itc|larsen|adani|tata|bajaj|maruti|sun pharma|cipla|zomato|paytm|coal india|hindustan|airtel|bharti)/g;
  const names = (s.match(NAMES) || []).length;
  if (/\b(vs|versus|compare|against|better than)\b/.test(s) || names >= 2) return "stock_comparison";
  if (resolveStock(query)) return "single_stock";

  const n = normalizeForClassification(query);
  // Individual-stock leaderboard (top gainers/losers/most active) - must precede the market/index
  // heuristics so a stock-mover ask plans stock-mover data, not the index/sector snapshot.
  if (/\b(top|biggest|best|highest)\b[^.?!]{0,40}\b(gainers?|losers?|movers?|active|volume|stocks?|shares?)\b|\b(gainers?|losers?)\b[^.?!]{0,20}\b(today|now|this week|currently)\b|\bmost active\b|\bhighest volume\b|\bwhich stocks?\b[^.?!]{0,30}\b(moved?|gain|los|up|down|most)\b/.test(n)) return "top_stock_movers";
  if (/summari|market summary|today'?s? market|market wrap|how (is|was|did) the market|market today|wrap up/.test(n)) return "market_summary";
  if (/(nifty|sensex|bank ?nifty|midcap|smallcap|index)\b/.test(n) && /(mov|up|down|fall|rise|gain|drop|today|why|lead|rally)/.test(n)) return "index_movement";
  if (/(cpi|wpi|\biip\b|\bpmi\b|\bgdp\b|\bfed\b|monsoon|fiscal|current account|inflation|deficit)/.test(n)) return "macro_impact";
  if (/(sector|banks?|financials|it sector|pharma|auto|fmcg|metal|realty|energy|defence|railway|crude|oil|rupee|usd ?inr|yield|g-?sec|rbi|repo|fii|dii|flow)/.test(n)) return "sector_impact";
  if (/^(what is|what's|whats|explain|define|meaning of|how does|how do)\b/.test(n)) return "term_explanation";
  if (/(india|indian|nse|bse|sebi|stock|share|market|equit)/.test(n)) return "sector_impact";
  return "out_of_scope";
}