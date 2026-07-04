import type { ContextPack, MavenAnswer, MavenBlock, MavenKeyData, MavenSource, MavenEvidenceSummary } from "./types";
import { SYSTEM_PROMPT, RETRIEVAL_PACK } from "../india-context";
import { deepseekJSON } from "../deepseek";
import { disclaimerText } from "./answerTypeRouter";
import { getCurrentIndianFiscalYear, getLatestCompletedIndianFiscalYear, getExpectedLatestQuarter, formatFiscalPeriod, parseAllFiscalTokens, compareFiscalPeriods } from "./reportingPeriods";

const arrowize = (chain: string) => chain.replace(/->/g, "→");
const SOURCE_CAP = 20; // enough for a deep (22-budget) research pack without an unbounded payload

export function realSources(pack: ContextPack): MavenSource[] {
  const out: MavenSource[] = pack.sourceSnippets.slice(0, SOURCE_CAP).map((s) => ({
    name: s.source, title: s.title, url: s.url, date: s.date ?? s.published, snippet: s.snippet,
    domain: s.domain ?? s.source,
    type: (s.sourceRank ?? 9) <= 3 ? "official" : "news",
    confidence: s.confidence ?? "retrieved",
  }));
  const hasMarket = !!(pack.marketData.indices?.some((q) => q.price != null) || pack.marketData.sectors?.length || pack.marketData.stocks?.length || pack.marketData.crude?.price != null || pack.marketData.usdinr?.price != null);
  if (hasMarket) out.push({ name: "NSE/BSE market data (via Yahoo Finance)", type: "market_data", confidence: "retrieved" });
  out.push({ name: "Maven analysis", type: "analysis", confidence: "analysis_only" });
  return out;
}

// Evidence summary is derived from the exact sources array shown to the user, so counts always
// match what the UI renders. Only produced when there is something to report.
export function buildEvidence(pack: ContextPack, sources: MavenSource[]): MavenEvidenceSummary | undefined {
  const sourceCount = sources.length;
  if (sourceCount === 0 && !pack.evidenceHint) return undefined;
  const verifiedSourceCount = sources.filter((s) => s.confidence === "verified").length;
  const retrievedSourceCount = sources.filter((s) => s.confidence === "retrieved").length;
  const analysisOnlySourceCount = sources.filter((s) => s.confidence === "analysis_only").length;
  const officialSourceCount = sources.filter((s) => s.type === "official").length;
  const unavailableSourceCount = pack.sourceSnippets.filter((s) => s.extractionStatus === "failed").length;
  const evidenceDepth = pack.evidenceHint?.evidenceDepth;
  const sourceBudget = pack.evidenceHint?.sourceBudget;

  let coverageStatus: MavenEvidenceSummary["coverageStatus"];
  const substantive = sourceCount - analysisOnlySourceCount - (sources.some((s) => s.type === "market_data") ? 1 : 0);
  if (sourceBudget) {
    const ratio = Math.max(0, substantive) / sourceBudget;
    coverageStatus = ratio >= 0.7 ? "strong" : ratio >= 0.35 ? "partial" : substantive > 0 ? "thin" : "unavailable";
  } else {
    coverageStatus = substantive >= 3 ? "strong" : substantive > 0 ? "partial" : "unavailable";
  }

  // latest fiscal period visible in retrieved source text (freshness cue for the UI)
  let latest: { fy: number; quarter?: 1 | 2 | 3 | 4 } | null = null;
  for (const s of pack.sourceSnippets) {
    for (const p of parseAllFiscalTokens(`${s.title} ${s.snippet}`)) {
      if (p.fy > getCurrentIndianFiscalYear() + 1) continue; // ignore far-future projections (e.g. FY30 targets)
      if (!latest || compareFiscalPeriods(p, latest) > 0) latest = p;
    }
  }

  return { sourceCount, verifiedSourceCount, retrievedSourceCount, officialSourceCount, analysisOnlySourceCount, unavailableSourceCount, evidenceDepth, sourceBudget, coverageStatus, latestPeriodFound: latest ? formatFiscalPeriod(latest) : undefined, latestAnnualPeriodFound: pack.latestAnnualPeriodFound };
}

function keyDataFrom(pack: ContextPack): MavenKeyData[] {
  const k: MavenKeyData[] = [];
  const push = (label: string, q?: { price: number | null; changePct: number | null } | null) => {
    if (q && q.price != null) k.push({ label, value: q.price.toFixed(2), change: q.changePct != null ? (q.changePct >= 0 ? "+" : "") + q.changePct.toFixed(2) + "%" : undefined });
  };
  for (const q of pack.marketData.stocks ?? []) push(q.label, q);
  for (const q of pack.marketData.indices ?? []) push(q.label, q);
  push("Brent crude", pack.marketData.crude);
  push("USD/INR", pack.marketData.usdinr);
  return k.slice(0, 6);
}

function fundBits(pack: ContextPack): string[] {
  const s = pack.marketData.stockSnapshots?.[0]; const bits: string[] = [];
  if (!s) return bits;
  if (s.marketCap != null) bits.push(`mkt cap ₹${s.marketCap.toLocaleString("en-IN")} Cr`);
  if (s.pe != null) bits.push(`P/E ${s.pe}`);
  if (s.pb != null) bits.push(`P/B ${s.pb}`);
  if (s.roe != null) bits.push(`ROE ${s.roe}%`);
  if (s.dividendYield != null) bits.push(`div yield ${s.dividendYield}%`);
  return bits;
}

function synthesizeStock(pack: ContextPack, liveFacts: string[], disc: string): MavenAnswer {
  const kb = pack.knowledge;
  const moveFact = liveFacts.find((f) => f.includes("moved") && f.includes("vs Nifty")) || liveFacts.find((f) => /at \d/.test(f)) || "";
  const catFact = pack.extractedFacts.find((f) => f.startsWith("Likely catalyst"));
  const noCat = pack.extractedFacts.find((f) => f.startsWith("No company-specific"));
  const newsFacts = pack.extractedFacts.filter((f) => f.startsWith("News: ")).slice(0, 2);
  const st = pack.marketData.stocks?.[0];
  const dir = st?.changePct == null ? "the move" : st.changePct >= 0 ? "the gain" : "the fall";
  const fb = fundBits(pack);

  const blocks: MavenBlock[] = [];
  blocks.push({ type: "DATA", title: "Price and relative move", body: moveFact || `${pack.topic} price data from the latest session.` });
  blocks.push({ type: "POINT", title: "Company-specific catalyst", body: catFact ? (catFact + (newsFacts.length ? " " + newsFacts.join(" ") : "")) : (noCat || "No company-specific catalyst was identified from available sources; the move appears more likely linked to broader sector, flow, or market context.") });
  if (fb.length) blocks.push({ type: "POINT", title: "Fundamental context", body: fb.join(", ") + "." });
  blocks.push({ type: "POINT", title: "Sector and macro context", body: arrowize(pack.mechanism?.chain || "driver → channel → variable → impact → risk") + (kb ? ". " + kb.summary : "") });
  blocks.push({ type: "RISK", title: "What is not confirmed", body: "Company-specific confirmation from open sources is limited; treat the catalyst as tentative and cross-check the official filing." + (pack.limitations.length ? " " + pack.limitations.join(" ") : "") });
  blocks.push({ type: "TAKEAWAY", title: "Maven view", body: `Read ${dir} in ${pack.topic} through its own drivers plus sector and flow context - mechanism, not a recommendation.` + (disc ? " " + disc : "") });

  const stockSources = realSources(pack);
  return {
    headline: `${pack.topic}: what's driving ${dir}`,
    summary: (moveFact || `${pack.topic} in focus.`) + (catFact ? " " + catFact : ""),
    keyData: keyDataFrom(pack), charts: pack.chartData, blocks, sources: stockSources,
    followUps: [`What are the key drivers for ${pack.topic}?`, `How does ${pack.topic}'s sector look today?`, `What would change this view?`],
    disclaimer: disc,
    evidence: buildEvidence(pack, stockSources),
    latestDataChecklist: pack.latestDataChecklist,
  };
}

function synthesize(pack: ContextPack): MavenAnswer {
  const disc = disclaimerText(pack.disclaimerLevel);
  const liveFacts = pack.extractedFacts.filter((f) => !f.startsWith("[directional]"));
  if (pack.answerType === "single_stock_research") return synthesizeStock(pack, liveFacts, disc);

  const kb = pack.knowledge;
  const dirFacts = pack.extractedFacts.filter((f) => f.startsWith("[directional]")).map((f) => f.replace("[directional] ", ""));
  const blocks: MavenBlock[] = [];
  if (liveFacts.length) blocks.push({ type: "DATA", title: "Market setup", body: liveFacts.slice(0, 4).join(" ") });
  blocks.push({ type: "POINT", title: "Mechanism", body: arrowize(pack.mechanism?.chain || "driver → channel → variable → impact → risk") + (kb ? ". " + kb.summary : "") });
  if (kb && (kb.winners.length || kb.losers.length)) blocks.push({ type: "POINT", title: "Winners and losers", body: "Helped: " + kb.winners.join("; ") + ". Pressured: " + kb.losers.join("; ") + "." });
  if (dirFacts.length) blocks.push({ type: "DATA", title: "Grounding (directional)", body: dirFacts.join(" ") });
  if (pack.marketData.crude?.price != null || pack.marketData.usdinr?.price != null) blocks.push({ type: "MACRO", title: "External setup", body: "Crude and the rupee shape India's import bill, inflation and foreign-flow appetite; read them alongside US yields." });
  blocks.push({ type: "RISK", title: "What can reverse it", body: kb && kb.key === "crude" ? "A crude fall driven by weak global demand is not purely positive - it can signal slowing growth that hurts cyclicals and exporters." : "Watch market breadth, the FII vs DII balance, and any shift in the RBI rate/liquidity stance." });
  blocks.push({ type: "TAKEAWAY", title: "India context", body: "Read this through India-specific drivers - flows, rates and sector rotation." + (disc ? " " + disc : "") });

  const limitNote = pack.limitations.length ? " " + pack.limitations.join(" ") : "";
  const head = kb ? capitalize(kb.topic) + ": the India read" : pack.topic + ": the India read";
  const marketSources = realSources(pack);
  return {
    headline: head,
    summary: (kb?.summary || liveFacts[0] || "Maven read this across India's indices, sectors, flows and macro.") + limitNote,
    keyData: keyDataFrom(pack), charts: pack.chartData, blocks, sources: marketSources,
    followUps: kb?.followUps?.slice(0, 3) || ["What is driving this specifically?", "How do FII/DII flows affect it?", "What would change this view?"],
    disclaimer: disc,
    evidence: buildEvidence(pack, marketSources),
    latestDataChecklist: pack.latestDataChecklist,
  };
}

function capitalize(s: string) { return s.charAt(0).toUpperCase() + s.slice(1); }

export async function generateAnswer(pack: ContextPack, strict = false): Promise<MavenAnswer> {
  const single = pack.answerType === "single_stock_research";
  const isStock = single || pack.answerType === "stock_comparison";
  const curFY = getCurrentIndianFiscalYear();
  const system =
    SYSTEM_PROMPT + "\n\n" + RETRIEVAL_PACK +
    "\n\nRESEARCH MODE: Answer ONLY from the provided research context (live facts, knowledge grounding, sources). " +
    "State NO number that is not in the facts, knowledge, or sources - if you must generalise, say 'directionally'. " +
    (isStock ? `FRESHNESS LOCK: Today's Indian fiscal context is FY${curFY} (latest completed FY${getLatestCompletedIndianFiscalYear()}, expected latest reported quarter ${formatFiscalPeriod(getExpectedLatestQuarter())}). For company answers you must NOT use memory-based financial metrics (revenue growth, margins, market share, capex, order book, guidance, market size). Use ONLY figures present in the provided facts/sources/allowedMetrics, ALWAYS labeled with their reporting period (e.g. 'Q4FY26 revenue'). Never present FY${getLatestCompletedIndianFiscalYear() - 2}/FY${getLatestCompletedIndianFiscalYear() - 1} figures as current unless the user asked for history or they are explicitly the latest available AND labeled so. If a metric is not in the context, say it is unavailable - do not approximate (~, roughly, around, estimated, X-Y%). ` : "") +
    "Lead with the mechanism chain provided. Be specific and concise like a senior Indian equity analyst; NO filler. " +
    "Output JSON {headline, summary, keyData:[{label,value,change}], blocks:[{type,title,body}], followUps:[]}. " +
    "Block types DATA/POINT/MACRO/CONTEXT/RISK/TAKEAWAY; include >=1 RISK and end with TAKEAWAY. Do NOT output charts/sources/disclaimer." +
    (single ? " SINGLE-STOCK MODE: One company. Block order: DATA (Price and relative move vs Nifty/sector) -> POINT (Company-specific catalyst: cite the news/filing in facts/sources; if none, say the move is more likely sector/flow/market-linked and DO NOT invent one) -> POINT (Fundamental context: ONLY if P/E, P/B, ROE, mkt cap or results appear in facts - otherwise omit this block, do not force it) -> POINT (Sector and macro context via the mechanism chain) -> RISK (what is not confirmed) -> TAKEAWAY. Headline = one line on the likely driver." : "") +
    (strict ? " STRICTER PASS: increase specificity, make the mechanism chain explicit with arrows, remove every generic sentence, and ensure each claim ties to a provided fact/source." : "");
  const user = JSON.stringify({
    question: pack.question, intent: pack.intent, answerType: pack.answerType, topic: pack.topic,
    mechanismChain: pack.mechanism?.chain,
    knowledge: pack.knowledge ? { summary: pack.knowledge.summary, chain: pack.knowledge.chain, winners: pack.knowledge.winners, losers: pack.knowledge.losers, facts: pack.knowledge.facts.map((f) => f.text) } : null,
    facts: pack.extractedFacts,
    sources: pack.sourceSnippets.map((s) => ({ title: s.title, snippet: s.snippet, source: s.source, date: s.date ?? s.published })),
    allowedMetrics: pack.metricEvidence?.filter((m) => m.allowedVisible).map((m) => ({ label: m.label, value: m.value, unit: m.unit, period: m.period, source: m.sourceName, freshness: m.freshness })),
    marketData: pack.marketData, limitations: pack.limitations,
  });

  const out = await deepseekJSON(system, user, 1500);
  const disc = disclaimerText(pack.disclaimerLevel);
  if (out && typeof out.headline === "string" && Array.isArray(out.blocks)) {
    const sources = realSources(pack);
    const types = ["DATA", "POINT", "MACRO", "CONTEXT", "RISK", "TAKEAWAY"];
    const blocks: MavenBlock[] = out.blocks.filter((b: any) => b && b.title).map((b: any) => ({ type: (types.includes(String(b.type).toUpperCase()) ? String(b.type).toUpperCase() : "POINT") as MavenBlock["type"], title: String(b.title), body: String(b.body ?? "") }));
    return {
      headline: String(out.headline), summary: String(out.summary ?? ""),
      keyData: Array.isArray(out.keyData) ? out.keyData.map((d: any) => ({ label: String(d.label ?? ""), value: String(d.value ?? ""), change: d.change != null ? String(d.change) : undefined })) : keyDataFrom(pack),
      charts: pack.chartData, blocks, sources,
      followUps: Array.isArray(out.followUps) && out.followUps.length ? out.followUps.map((f: any) => String(f)).slice(0, 4) : (single ? [`What are the key drivers for ${pack.topic}?`, "What would change this view?"] : (pack.knowledge?.followUps?.slice(0, 3) || [])),
      disclaimer: disc,
      evidence: buildEvidence(pack, sources),
      latestDataChecklist: pack.latestDataChecklist,
    };
  }
  return synthesize(pack);
}