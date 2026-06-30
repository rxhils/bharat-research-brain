import type { ContextPack, MavenAnswer } from "./types";

export const FILLER_PATTERNS = [
  /what maven does/i, /educational purpose/i, /educational insight/i, /here is the market context/i,
  /there are many factors/i, /investors should monitor/i, /always consult/i, /maven is your india-first/i,
  /in conclusion/i, /it is important to note/i,
];

const HYPE = /\b(strong buy|buy now|sell now|target price|price target|multibagger|sure[-\s]?shot|guaranteed)\b/i;

export function scoreAnswer(a: MavenAnswer, pack: ContextPack): { score: number; reasons: string[] } {
  let score = 0;
  const reasons: string[] = [];
  const text = [a.headline, a.summary, ...a.blocks.map((b) => b.title + " " + b.body)].join(" ");
  const low = text.toLowerCase();

  if (/\d/.test(text)) score += 12; else reasons.push("no specific numbers");

  const realSrc = a.sources.filter((s) => s.confidence === "retrieved" || s.confidence === "verified").length;
  if (realSrc > 0) score += 14; else { score += 6; reasons.push("analysis-only sources"); }

  if ((pack.mechanism?.chain || "").includes("->") || a.blocks.some((b) => /->|→/.test(b.body))) score += 16; else reasons.push("shallow mechanism");

  if (/(nifty|sensex|bank|rbi|fii|dii|rupee|crude|g-?sec|india|sebi|nse|bse)/i.test(text)) score += 14; else reasons.push("weak India framing");

  const hasRisk = a.blocks.some((b) => b.type === "RISK");
  const hasTake = a.blocks.some((b) => b.type === "TAKEAWAY");
  if (hasRisk && hasTake) score += 12; else reasons.push("missing RISK/TAKEAWAY");

  if (a.keyData.length > 0) score += 10; else reasons.push("no keyData");
  if (a.charts.length > 0) score += 8; else reasons.push("no charts");
  if (a.summary.length > 40) score += 6;

  if (FILLER_PATTERNS.some((r) => r.test(low))) { score -= 18; reasons.push("generic filler"); }
  if (HYPE.test(low)) { score -= 25; reasons.push("advice/hype leakage"); }

  return { score: Math.max(0, Math.min(100, score)), reasons };
}