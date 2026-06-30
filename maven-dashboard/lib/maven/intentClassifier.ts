import type { Intent } from "./types";
import { isAdviceRequest } from "../guard";

// Fast, deterministic intent classification (no token cost). Heuristic order matters.
export function classifyIntent(query: string): Intent {
  const s = (query || "").toLowerCase();
  if (!s.trim()) return "out_of_scope";
  if (isAdviceRequest(query)) return "unsafe_advice";

  const NAMES = /(hdfc|icici|sbi|axis|kotak|reliance|ril|tcs|infosys|infy|wipro|hcl|itc|lt|larsen|adani|tata|bajaj|maruti|sun pharma|cipla)/g;
  const names = (s.match(NAMES) || []).length;
  if (/\b(vs|versus|compare|against|better than)\b/.test(s) || names >= 2) return "stock_comparison";

  if (/summari|today'?s? market|market wrap|how (is|was|did) the market|market today|wrap up/.test(s)) return "market_summary";
  if (/(nifty|sensex|bank ?nifty|midcap|smallcap|index)\b/.test(s) && /(mov|up|down|fall|rise|gain|drop|today|why|lead|rally)/.test(s)) return "index_movement";
  if (/(cpi|wpi|\biip\b|\bpmi\b|\bgdp\b|\bfed\b|monsoon|fiscal|current account|inflation|deficit)/.test(s)) return "macro_impact";
  if (/(sector|banks?|financials|it sector|pharma|auto|fmcg|metal|realty|energy|defence|railway|crude|oil|rupee|usd ?inr|yield|g-?sec|rbi|repo|fii|dii|flow)/.test(s)) return "sector_impact";
  if (/^(what is|what's|whats|explain|define|meaning of|how does|how do)\b/.test(s)) return "term_explanation";
  if (/(india|indian|nse|bse|sebi|stock|share|market|equit)/.test(s)) return "sector_impact";
  return "out_of_scope";
}