import type { ContextPack, ResearchPlan, MarketData, ChartSpec, AnswerType, DisclaimerLevel, SourceResult } from "./types";
import { getIndexPerformance, getSectorPerformance, getStockPrice, getCrudePrice, getUSDINR, getGSecYield, getFIIDIIFlows, getIndiaMacroSnapshot, getCompanySnapshot, getCompanyAnnouncements } from "./dataTools";
import { searchSources } from "./sourceSearch";
import { lookupKnowledge } from "./indiaMarketKnowledge";
import { buildMechanism } from "./mechanismBuilder";
import { extractSymbols } from "./stockResolver";
import { extractCatalyst } from "./stockCatalystExtractor";

const pct = (n: number | null) => (n == null ? "n/a" : (n >= 0 ? "+" : "") + n.toFixed(2) + "%");
const round = (n: number | null): number | null => (n == null ? null : Math.round(n * 100) / 100);

export async function buildContextPack(query: string, plan: ResearchPlan, answerType: AnswerType, disclaimerLevel: DisclaimerLevel): Promise<ContextPack> {
  const md: MarketData = {};
  const facts: string[] = [];
  const limitations: string[] = [];
  const charts: ChartSpec[] = [];
  const extraSources: SourceResult[] = [];
  const need = new Set(plan.requiredData);
  const syms = extractSymbols(query);

  const jobs: Promise<void>[] = [];
  if (need.has("indices")) jobs.push(getIndexPerformance().then((d) => { md.indices = d; }));
  if (need.has("sectors")) jobs.push(getSectorPerformance().then((d) => { md.sectors = d; }));
  if (need.has("crude")) jobs.push(getCrudePrice().then((d) => { md.crude = d; }));
  if (need.has("usdinr")) jobs.push(getUSDINR().then((d) => { md.usdinr = d; }));
  if (need.has("gsec")) jobs.push(getGSecYield().then((d) => { md.gsecYield = d; }));
  if (need.has("fiidii")) jobs.push(getFIIDIIFlows().then((d) => { md.fiiDiiFlows = d; }));
  if (need.has("macro")) jobs.push(getIndiaMacroSnapshot().then((d) => { md.macroSnapshot = d; }));
  if (need.has("stock") || need.has("stocks")) { if (syms.length) jobs.push(Promise.all(syms.map((s) => getStockPrice(s))).then((d) => { md.stocks = d; })); }
  if (need.has("snapshots") && syms.length) jobs.push(Promise.all(syms.map((s) => getCompanySnapshot(s))).then((d) => { md.stockSnapshots = d; }));
  if (need.has("announcements") && syms.length) jobs.push(Promise.all(syms.map((s) => getCompanyAnnouncements(s))).then((d) => { md.announcements = d; }));

  const sourcesP = searchSources(plan.searchQueries);
  await Promise.all(jobs);
  const sourceSnippets = await sourcesP;

  // ---- facts (every number attributed) ----
  for (const q of md.indices ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today). [source: NSE/BSE via Yahoo Finance]`);
  if (md.sectors?.length) { const t = md.sectors[0], b = md.sectors[md.sectors.length - 1]; facts.push(`Top sector ${t.name} (${pct(t.changePct)}); weakest ${b.name} (${pct(b.changePct)}). [source: NSE via Yahoo Finance]`); }
  for (const q of md.stocks ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today). [source: Yahoo Finance]`);
  if (md.crude?.price != null) facts.push(`Brent crude at ${md.crude.price.toFixed(2)} (${pct(md.crude.changePct)}). [source: Yahoo Finance]`);
  if (md.usdinr?.price != null) facts.push(`USD/INR at ${md.usdinr.price.toFixed(2)} (${pct(md.usdinr.changePct)}). [source: Yahoo Finance]`);
  if (md.gsecYield?.yield10Y != null) facts.push(`10Y G-Sec yield ~${md.gsecYield.yield10Y}% (latest available). [source: ${md.gsecYield.source}]`);
  if (md.fiiDiiFlows?.context) facts.push(`FII/DII (latest available): ${md.fiiDiiFlows.context} [source: ${md.fiiDiiFlows.source}]`);
  for (const p of md.macroSnapshot?.points ?? []) if (p.value != null) facts.push(`${p.label}: ${p.value}${p.unit ? p.unit : ""} (${p.freshness === "live" ? "live" : "latest available"}). [source: ${p.source}]`);
  for (const snap of md.stockSnapshots ?? []) for (const p of snap.points) if (p.value != null && p.key !== "price") facts.push(`${snap.symbol} ${p.label}: ${p.value}${p.unit ? p.unit : ""}. [source: ${p.source}]`);

  const knowledge = lookupKnowledge(query) || lookupKnowledge(plan.topic);
  const mechanism = buildMechanism(query, plan.topic);
  for (const f of knowledge?.facts ?? []) facts.push(`[directional] ${f.text}.`);

  // ---- single-stock catalyst + relative move + stock chart ----
  if (answerType === "single_stock_research") {
    const st = md.stocks?.[0];
    const nifty = md.indices?.find((i) => i.label === "Nifty 50");
    if (st?.changePct != null && nifty?.changePct != null) facts.push(`${st.label} moved ${pct(st.changePct)} today vs Nifty ${pct(nifty.changePct)} (relative ${pct(st.changePct - nifty.changePct)}). [source: Yahoo Finance]`);
    const annItems = (md.announcements ?? []).flatMap((a) => a.announcements.map((x) => ({ title: x.title, snippet: x.snippet })));
    for (const a of md.announcements ?? []) for (const an of a.announcements.slice(0, 2)) facts.push(`${a.symbol} news: ${an.title}. [source: ${an.source}]`);
    const catalyst = extractCatalyst([...annItems, ...sourceSnippets.map((s) => ({ title: s.title, snippet: s.snippet }))]);
    if (catalyst.primaryCatalyst !== "no_clear_catalyst") {
      facts.push(`Likely catalyst: ${catalyst.primaryCatalyst}${catalyst.secondaryCatalysts.length ? " (also " + catalyst.secondaryCatalysts.join(", ") + ")" : ""} [confidence: ${catalyst.confidence}].`);
      charts.push({ type: "comparison_table", title: "Possible catalysts", dataSource: "catalyst", data: [{ primary: catalyst.primaryCatalyst, secondary: catalyst.secondaryCatalysts.join(", ") || "-", confidence: catalyst.confidence }] });
    } else {
      facts.push("No single company-specific catalyst was identified from available sources; the move appears more likely linked to broader sector/market context.");
    }
    if (st?.spark?.length) charts.push({ type: "line", title: `${st.label} (intraday)`, dataSource: "stock", xKey: "i", yKeys: ["price"], data: st.spark.map((p, i) => ({ i, price: round(p) })) });
  }

  // ---- limitations (clean, user-facing) ----
  if (md.gsecYield?.limitation) limitations.push(md.gsecYield.limitation);
  if (md.fiiDiiFlows?.limitation) limitations.push(md.fiiDiiFlows.limitation);
  if (md.macroSnapshot?.limitation) limitations.push(md.macroSnapshot.limitation);
  for (const snap of md.stockSnapshots ?? []) if (snap.limitation) limitations.push(`${snap.symbol}: ${snap.limitation}`);
  for (const ca of md.announcements ?? []) if (ca.limitation) limitations.push(ca.limitation);
  if (plan.requiresLiveData && (md.indices?.every((q) => q.price == null) ?? false)) limitations.push("Current live market data is unavailable for this query.");

  // ---- feed source chips ----
  const pushSrc = (title: string, url?: string, snippet?: string, source?: string, published?: string) => { if (url) extraSources.push({ title, url, snippet: snippet ?? "", source: source ?? title, published }); };
  if (md.gsecYield?.yield10Y != null) pushSrc("10Y G-Sec yield", md.gsecYield.sourceUrl, "", md.gsecYield.source, md.gsecYield.date);
  if (md.fiiDiiFlows?.context) pushSrc("FII/DII context", md.fiiDiiFlows.sourceUrl, md.fiiDiiFlows.context, md.fiiDiiFlows.source, md.fiiDiiFlows.date);
  for (const p of md.macroSnapshot?.points ?? []) if (p.value != null && p.sourceUrl) pushSrc(p.label, p.sourceUrl, "", p.source);
  for (const ca of md.announcements ?? []) for (const an of ca.announcements.slice(0, 3)) pushSrc(an.title, an.sourceUrl, an.snippet, an.source, an.date);
  const allSources = dedupeSources([...sourceSnippets, ...extraSources]);

  // ---- charts (only when real data exists) ----
  if (md.indices?.some((q) => q.price != null)) charts.push({ type: "bar", title: "Index moves today", dataSource: "indices", xKey: "name", yKeys: ["changePct"], data: md.indices.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: round(q.changePct) })) });
  if (md.sectors?.length) charts.push({ type: "bar", title: "Sector performance", dataSource: "sectors", xKey: "name", yKeys: ["changePct"], data: md.sectors.map((s) => ({ name: s.name, changePct: round(s.changePct) })) });
  if (md.crude?.spark?.length) charts.push({ type: "line", title: "Brent crude (intraday)", dataSource: "crude", xKey: "i", yKeys: ["price"], data: md.crude.spark.map((p, i) => ({ i, price: round(p) })) });
  if (md.usdinr?.spark?.length) charts.push({ type: "line", title: "USD/INR (intraday)", dataSource: "usdinr", xKey: "i", yKeys: ["price"], data: md.usdinr.spark.map((p, i) => ({ i, price: round(p) })) });
  if (md.stockSnapshots?.length) {
    const rows = md.stockSnapshots.map((s) => {
      const get = (k: string) => { const p = s.points.find((x) => x.key === k); return p ? p.value : null; };
      return { name: s.symbol, price: get("price"), PE: get("pe"), PB: get("pb"), ROE: get("roe") };
    });
    if (rows.some((r) => r.price != null || r.PE != null)) charts.push({ type: "comparison_table", title: "Valuation comparison", dataSource: "snapshots", data: rows as Record<string, unknown>[] });
  } else if (md.stocks?.length && md.stocks.length > 1) {
    charts.push({ type: "comparison_table", title: "Stock comparison", dataSource: "stocks", data: md.stocks.map((q) => ({ name: q.label, price: q.price, changePct: round(q.changePct) })) });
  }
  if (mechanism.flow) charts.push(mechanism.flow);

  return { question: query, intent: plan.intent, topic: plan.topic, answerType, disclaimerLevel, marketData: md, extractedFacts: facts, sourceSnippets: allSources, chartData: charts, limitations, knowledge, mechanism };
}

function dedupeSources(list: SourceResult[]): SourceResult[] {
  const seen = new Set<string>();
  return list.filter((s) => s.url && !seen.has(s.url) && seen.add(s.url)).slice(0, 8);
}