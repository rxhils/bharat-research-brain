import type { ContextPack, ResearchPlan, MarketData, ChartSpec, AnswerType, DisclaimerLevel } from "./types";
import { getIndexPerformance, getSectorPerformance, getStockPrice, getCrudePrice, getUSDINR, getGSecYield, getFIIDIIFlows } from "./dataTools";
import { searchSources } from "./sourceSearch";
import { lookupKnowledge } from "./indiaMarketKnowledge";
import { buildMechanism } from "./mechanismBuilder";

const pct = (n: number | null) => (n == null ? "n/a" : (n >= 0 ? "+" : "") + n.toFixed(2) + "%");
const round = (n: number | null): number | null => (n == null ? null : Math.round(n * 100) / 100);

export async function buildContextPack(query: string, plan: ResearchPlan, answerType: AnswerType, disclaimerLevel: DisclaimerLevel): Promise<ContextPack> {
  const md: MarketData = {};
  const facts: string[] = [];
  const limitations: string[] = [];
  const charts: ChartSpec[] = [];
  const need = new Set(plan.requiredData);

  const jobs: Promise<void>[] = [];
  if (need.has("indices")) jobs.push(getIndexPerformance().then((d) => { md.indices = d; }));
  if (need.has("sectors")) jobs.push(getSectorPerformance().then((d) => { md.sectors = d; }));
  if (need.has("crude")) jobs.push(getCrudePrice().then((d) => { md.crude = d; }));
  if (need.has("usdinr")) jobs.push(getUSDINR().then((d) => { md.usdinr = d; }));
  if (need.has("gsec")) jobs.push(getGSecYield().then((d) => { md.gsec = d; }));
  if (need.has("fiidii")) jobs.push(getFIIDIIFlows().then((d) => { md.flows = d; }));
  if (need.has("stocks")) {
    const syms = extractSymbols(query);
    if (syms.length) jobs.push(Promise.all(syms.map((s) => getStockPrice(s))).then((d) => { md.stocks = d; }));
  }
  const sourcesP = searchSources(plan.searchQueries);
  await Promise.all(jobs);
  const sourceSnippets = await sourcesP;

  for (const q of md.indices ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today).`);
  if (md.sectors?.length) { const t = md.sectors[0], b = md.sectors[md.sectors.length - 1]; facts.push(`Top sector ${t.name} (${pct(t.changePct)}); weakest ${b.name} (${pct(b.changePct)}).`); }
  for (const q of md.stocks ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today).`);
  if (md.crude?.price != null) facts.push(`Brent crude at ${md.crude.price.toFixed(2)} (${pct(md.crude.changePct)}).`);
  if (md.usdinr?.price != null) facts.push(`USD/INR at ${md.usdinr.price.toFixed(2)} (${pct(md.usdinr.changePct)}).`);

  const knowledge = lookupKnowledge(query) || lookupKnowledge(plan.topic);
  const mechanism = buildMechanism(query, plan.topic);
  for (const f of knowledge?.facts ?? []) facts.push(`[directional] ${f.text}.`);

  if (need.has("gsec") && (!md.gsec || md.gsec.yieldPct == null)) limitations.push("10Y G-Sec yield feed not wired.");
  if (need.has("fiidii") && (!md.flows || md.flows.fiiCr == null)) limitations.push("FII/DII flows are end-of-day; a live feed is not wired.");
  if (plan.searchQueries.length && sourceSnippets.length === 0) limitations.push("No external news source configured for this query.");
  if (plan.requiresLiveData && (md.indices?.every((q) => q.price == null) ?? false)) limitations.push("Current live market data is unavailable for this query.");

  if (md.indices?.some((q) => q.price != null)) charts.push({ type: "bar", title: "Index moves today", dataSource: "indices", xKey: "name", yKeys: ["changePct"], data: md.indices.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: round(q.changePct) })) });
  if (md.sectors?.length) charts.push({ type: "bar", title: "Sector performance", dataSource: "sectors", xKey: "name", yKeys: ["changePct"], data: md.sectors.map((s) => ({ name: s.name, changePct: round(s.changePct) })) });
  if (md.stocks?.length) charts.push({ type: "comparison_table", title: "Stock comparison", dataSource: "stocks", data: md.stocks.map((q) => ({ name: q.label, price: q.price, changePct: round(q.changePct) })) });
  if (md.crude?.spark?.length) charts.push({ type: "line", title: "Brent crude (intraday)", dataSource: "crude", xKey: "i", yKeys: ["price"], data: md.crude.spark.map((p, i) => ({ i, price: round(p) })) });
  if (md.usdinr?.spark?.length) charts.push({ type: "line", title: "USD/INR (intraday)", dataSource: "usdinr", xKey: "i", yKeys: ["price"], data: md.usdinr.spark.map((p, i) => ({ i, price: round(p) })) });
  if (mechanism.flow) charts.push(mechanism.flow);

  return { question: query, intent: plan.intent, topic: plan.topic, answerType, disclaimerLevel, marketData: md, extractedFacts: facts, sourceSnippets, chartData: charts, limitations, knowledge, mechanism };
}

function extractSymbols(q: string): string[] {
  const map: Record<string, string> = { hdfc: "HDFCBANK", icici: "ICICIBANK", sbi: "SBIN", axis: "AXISBANK", kotak: "KOTAKBANK", reliance: "RELIANCE", ril: "RELIANCE", tcs: "TCS", infosys: "INFY", infy: "INFY", wipro: "WIPRO", itc: "ITC" };
  const s = q.toLowerCase(); const out: string[] = [];
  for (const k of Object.keys(map)) if (new RegExp("\\b" + k + "\\b").test(s) && !out.includes(map[k])) out.push(map[k]);
  return out.slice(0, 3);
}