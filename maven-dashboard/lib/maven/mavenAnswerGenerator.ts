import type { ContextPack, MavenAnswer, MavenBlock, MavenKeyData, MavenSource } from "./types";
import { SYSTEM_PROMPT, RETRIEVAL_PACK } from "../india-context";
import { deepseekJSON } from "../deepseek";

const DISCLAIMER = "Market mechanism explanation, not investment advice.";

const MECHANISM: Record<string, string> = {
  Banks: "Banks track G-Sec yields and system liquidity: softer yields lift treasury gains and ease funding costs, while RBI stance and deposit growth set the medium-term path.",
  IT: "Indian IT earns most revenue in USD, so a weaker rupee supports margins, but global (US/Europe) demand and deal wins dominate over currency.",
  "crude oil": "India imports most of its oil, so softer crude eases the import bill, current-account deficit and inflation, helping OMCs, paints, aviation and logistics.",
  rupee: "The rupee moves with crude, the dollar, rate differentials and flows; weakness pressures importers and inflation but can help exporters like IT and pharma.",
  "RBI policy": "RBI's stance, liquidity actions (OMO/CRR) and inflation language drive bank funding costs and the rupee more than the headline repo number.",
};

function mechanismFor(topic: string): string {
  for (const k of Object.keys(MECHANISM)) if (topic.toLowerCase().includes(k.toLowerCase())) return MECHANISM[k];
  return "The move is best read through India-specific drivers: index leadership, sector rotation, institutional flows (FII vs DII), and the rate/liquidity backdrop.";
}

function realSources(pack: ContextPack): MavenSource[] {
  const out: MavenSource[] = pack.sourceSnippets.slice(0, 5).map((s) => ({ name: s.source, url: s.url, recency: s.published || "recent" }));
  const hasMarket = !!(pack.marketData.indices?.some((q) => q.price != null) || pack.marketData.sectors?.length || pack.marketData.stocks?.length || pack.marketData.crude?.price != null);
  if (hasMarket) out.push({ name: "NSE/BSE market data (via Yahoo Finance)", recency: "live" });
  out.push({ name: "Maven analysis", recency: "current" });
  return out;
}

function keyDataFrom(pack: ContextPack): MavenKeyData[] {
  const k: MavenKeyData[] = [];
  const push = (label: string, q?: { price: number | null; changePct: number | null } | null) => {
    if (q && q.price != null) k.push({ label, value: q.price.toFixed(2), change: q.changePct != null ? (q.changePct >= 0 ? "+" : "") + q.changePct.toFixed(2) + "%" : undefined });
  };
  for (const q of pack.marketData.indices ?? []) push(q.label, q);
  for (const q of pack.marketData.stocks ?? []) push(q.label, q);
  push("Brent crude", pack.marketData.crude);
  push("USD/INR", pack.marketData.usdinr);
  return k.slice(0, 6);
}

// Deterministic, data-grounded synthesis - used when the model is unavailable. Still researched
// (built from live fetched facts), never fabricated.
function synthesize(pack: ContextPack): MavenAnswer {
  const blocks: MavenBlock[] = [];
  if (pack.extractedFacts.length) blocks.push({ type: "DATA", title: "Market setup", body: pack.extractedFacts.slice(0, 4).join(" ") });
  blocks.push({ type: "POINT", title: "Mechanism", body: mechanismFor(pack.topic) });
  if (pack.marketData.crude?.price != null || pack.marketData.usdinr?.price != null) {
    blocks.push({ type: "MACRO", title: "External setup", body: "Crude and the rupee shape India's import bill, inflation and foreign-flow appetite; track them alongside US yields." });
  }
  blocks.push({ type: "RISK", title: "What can reverse it", body: "Watch breadth (is the average stock participating?), the FII vs DII balance, and any shift in the RBI rate/liquidity stance." });
  blocks.push({ type: "TAKEAWAY", title: "India context", body: "Read this through flows and sector rotation, not a single headline number. " + DISCLAIMER });
  const limitNote = pack.limitations.length ? " " + pack.limitations.join(" ") : "";
  return {
    headline: headlineFor(pack),
    summary: (pack.extractedFacts[0] || "Maven read the India market across indices, sectors, flows and macro.") + limitNote,
    keyData: keyDataFrom(pack),
    charts: pack.chartData,
    blocks,
    sources: realSources(pack),
    followUps: followUpsFor(pack),
    disclaimer: DISCLAIMER,
  };
}

function headlineFor(pack: ContextPack): string {
  const nifty = pack.marketData.indices?.find((q) => q.label === "Nifty 50");
  if (pack.intent === "market_summary" && nifty?.changePct != null) return `Indian market: Nifty ${nifty.changePct >= 0 ? "up" : "down"} ${Math.abs(nifty.changePct).toFixed(2)}%, led by sector rotation`;
  return `${pack.topic}: the India market read`;
}

function followUpsFor(pack: ContextPack): string[] {
  const t = pack.topic;
  return [`What is driving ${t} specifically?`, `How do FII/DII flows affect this?`, `What would change this view?`].slice(0, 3);
}

export async function generateAnswer(pack: ContextPack): Promise<MavenAnswer> {
  const system =
    SYSTEM_PROMPT + "\n\n" + RETRIEVAL_PACK +
    "\n\nRESEARCH MODE: You are given a research context pack (live facts + source snippets). Answer ONLY from it. Do not state any number or claim that is not in the facts or sources. If something needed is missing, say so using the limitations. Output JSON: {headline, summary, keyData:[{label,value,change}], blocks:[{type,title,body}], followUps:[]}. Block types: DATA, POINT, MACRO, CONTEXT, RISK, TAKEAWAY; include >=1 RISK and end with TAKEAWAY. Do not output charts or sources (the system attaches them).";
  const user = JSON.stringify({
    question: pack.question,
    intent: pack.intent,
    topic: pack.topic,
    facts: pack.extractedFacts,
    sources: pack.sourceSnippets.map((s) => ({ title: s.title, snippet: s.snippet, source: s.source })),
    marketData: pack.marketData,
    limitations: pack.limitations,
  });

  const out = await deepseekJSON(system, user, 1400);
  if (out && typeof out.headline === "string" && Array.isArray(out.blocks)) {
    const types = ["DATA", "POINT", "MACRO", "CONTEXT", "RISK", "TAKEAWAY"];
    const blocks: MavenBlock[] = out.blocks.filter((b: any) => b && b.title).map((b: any) => ({ type: (types.includes(String(b.type).toUpperCase()) ? String(b.type).toUpperCase() : "POINT") as MavenBlock["type"], title: String(b.title), body: String(b.body ?? "") }));
    return {
      headline: String(out.headline),
      summary: String(out.summary ?? ""),
      keyData: Array.isArray(out.keyData) ? out.keyData.map((d: any) => ({ label: String(d.label ?? ""), value: String(d.value ?? ""), change: d.change != null ? String(d.change) : undefined })) : keyDataFrom(pack),
      charts: pack.chartData,                 // backend supplies real chart data
      blocks,
      sources: realSources(pack),             // backend supplies real sources (no fabrication)
      followUps: Array.isArray(out.followUps) ? out.followUps.map((f: any) => String(f)).slice(0, 4) : followUpsFor(pack),
      disclaimer: DISCLAIMER,
    };
  }
  // model unavailable -> data-grounded deterministic synthesis
  return synthesize(pack);
}