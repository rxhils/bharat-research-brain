import type { ContextPack, MavenAnswer, MavenBlock, MavenSource } from "./types";
import { sanitizeVisibleText, FORBIDDEN_VISIBLE_TERMS } from "../maven-visibility";
import { FILLER_PATTERNS } from "./answerQualityScorer";
import { disclaimerText } from "./answerTypeRouter";

const HYPE = /\b(strong buy|buy now|sell now|target price|price target|multibagger|sure[-\s]?shot|guaranteed|low risk high return)\b/i;
const INDIA = /(nifty|sensex|bank|rbi|fii|dii|rupee|crude|g-?sec|india|sector|repo|inflation|yield|nse|bse)/i;

function stripFiller(s: string): string {
  let out = s || "";
  for (const r of FILLER_PATTERNS) out = out.replace(new RegExp(r.source + "[^.]*\\.?", r.flags), "");
  return out.replace(/\s{2,}/g, " ").trim();
}

export function validateAnswer(a: MavenAnswer, pack: ContextPack): { valid: boolean; issues: string[]; fixed: MavenAnswer } {
  const issues: string[] = [];
  const clean = (s: string) => stripFiller(sanitizeVisibleText(s || ""));

  const fixed: MavenAnswer = {
    ...a,
    headline: clean(a.headline),
    summary: clean(a.summary),
    keyData: a.keyData.map((d) => ({ ...d, label: sanitizeVisibleText(d.label), value: sanitizeVisibleText(d.value) })),
    blocks: a.blocks.map((b) => ({ ...b, title: sanitizeVisibleText(b.title), body: clean(b.body) })).filter((b) => b.body || b.title),
    followUps: a.followUps.map((f) => sanitizeVisibleText(f)),
  };

  const allText = [fixed.headline, fixed.summary, ...fixed.blocks.map((b) => b.title + " " + b.body)].join(" ");
  if (FORBIDDEN_VISIBLE_TERMS.some((t) => allText.toLowerCase().includes(t.toLowerCase()))) issues.push("provider-leak(scrubbed)");
  if (FILLER_PATTERNS.some((r) => r.test(allText))) issues.push("filler(stripped)");
  if (HYPE.test(allText)) { issues.push("hype/advice"); fixed.summary = fixed.summary.replace(HYPE, "constructive setup"); }

  if (!fixed.blocks.some((b) => b.type === "RISK")) { issues.push("missing RISK"); fixed.blocks.push({ type: "RISK", title: "What to watch", body: "Watch market breadth, the FII vs DII balance, and the RBI rate/liquidity stance." }); }
  if (fixed.blocks[fixed.blocks.length - 1]?.type !== "TAKEAWAY") {
    issues.push("TAKEAWAY position");
    const take = fixed.blocks.find((b) => b.type === "TAKEAWAY");
    fixed.blocks = fixed.blocks.filter((b) => b.type !== "TAKEAWAY");
    fixed.blocks.push(take ?? { type: "TAKEAWAY", title: "India context", body: "Read this through India-specific drivers. " + (a.disclaimer || "") });
  }

  if (!fixed.sources?.length) { issues.push("no sources"); fixed.sources = [{ name: "Maven analysis", type: "analysis", confidence: "analysis_only" } as MavenSource]; }
  fixed.sources = fixed.sources.map((s) => ({ ...s, confidence: s.confidence ?? "analysis_only" }));

  const hasNumbers = !!(pack.marketData.indices?.some((q) => q.price != null) || pack.marketData.sectors?.length || pack.marketData.stocks?.length);
  if (hasNumbers && (!fixed.charts || fixed.charts.length === 0)) { issues.push("missing charts"); fixed.charts = pack.chartData; }

  fixed.disclaimer = disclaimerText(pack.disclaimerLevel);
  if (!INDIA.test(allText)) issues.push("weak India grounding");

  return { valid: issues.filter((i) => !i.includes("scrubbed") && !i.includes("stripped")).length === 0, issues, fixed };
}