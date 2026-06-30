import type { ContextPack, MavenAnswer, MavenBlock } from "./types";
import { sanitizeVisibleText, FORBIDDEN_VISIBLE_TERMS } from "../maven-visibility";

const HYPE = /\b(strong buy|buy now|sell now|target price|price target|multibagger|sure[-\s]?shot|guaranteed|low risk high return)\b/i;
const INDIA = /(nifty|sensex|bank|rbi|fii|dii|rupee|crude|g-?sec|india|sector|repo|inflation|yield|nse|bse)/i;

export function validateAnswer(a: MavenAnswer, pack: ContextPack): { valid: boolean; issues: string[]; fixed: MavenAnswer } {
  const issues: string[] = [];
  const scrub = (s: string) => sanitizeVisibleText(s || "");

  let blocks: MavenBlock[] = a.blocks.map((b) => ({ ...b, title: scrub(b.title), body: scrub(b.body) }));
  const fixed: MavenAnswer = {
    ...a,
    headline: scrub(a.headline),
    summary: scrub(a.summary),
    keyData: a.keyData.map((d) => ({ ...d, label: scrub(d.label), value: scrub(d.value) })),
    blocks,
    followUps: a.followUps.map(scrub),
  };

  const allText = [fixed.headline, fixed.summary, ...fixed.blocks.map((b) => b.title + " " + b.body)].join(" ");

  // provider/infra leakage
  const leaks = FORBIDDEN_VISIBLE_TERMS.filter((t) => allText.toLowerCase().includes(t.toLowerCase()));
  if (leaks.length) issues.push("leak:" + leaks.join(","));   // already scrubbed above, but flag

  // advisory / hype
  if (HYPE.test(allText)) { issues.push("hype/recommendation language"); fixed.summary = fixed.summary.replace(HYPE, "constructive setup"); }

  // structure: >=1 RISK, ends with TAKEAWAY
  if (!fixed.blocks.some((b) => b.type === "RISK")) { issues.push("missing RISK"); fixed.blocks.push({ type: "RISK", title: "What to watch", body: "Watch market breadth, the FII vs DII balance, and the RBI rate/liquidity stance." }); }
  if (fixed.blocks[fixed.blocks.length - 1]?.type !== "TAKEAWAY") { issues.push("missing/misplaced TAKEAWAY"); fixed.blocks = fixed.blocks.filter((b) => b.type !== "TAKEAWAY"); fixed.blocks.push({ type: "TAKEAWAY", title: "India context", body: "Read this through India-specific drivers. " + a.disclaimer }); }

  // sources exist
  if (!fixed.sources?.length) { issues.push("no sources"); fixed.sources = [{ name: "Maven analysis", recency: "current" }]; }

  // charts when numerical data available
  const hasNumbers = !!(pack.marketData.indices?.some((q) => q.price != null) || pack.marketData.sectors?.length || pack.marketData.stocks?.length);
  if (hasNumbers && (!fixed.charts || fixed.charts.length === 0)) { issues.push("missing charts for numeric data"); fixed.charts = pack.chartData; }

  // India-first
  if (!INDIA.test(allText)) issues.push("weak India grounding");

  if (!fixed.disclaimer) fixed.disclaimer = "Market mechanism explanation, not investment advice.";

  return { valid: issues.filter((i) => !i.startsWith("leak")).length === 0, issues, fixed };
}