import type { ContextPack, ResearchPlan, MarketData, ChartSpec, AnswerType, DisclaimerLevel, SourceResult, CompanySnapshot, MetricEvidence, CompanyFact } from "./types";
import { validateMetricEvidence } from "./metricFreshnessValidator";
import { parseAllFiscalTokens, getLatestCompletedIndianFiscalYear } from "./reportingPeriods";
import { extractCompanyMetrics, crossVerifyMetrics } from "./companyMetricExtractor";
import { getFreshCompanyFacts, saveCompanyFacts } from "./companyFactStore";
import { buildLatestDataChecklist } from "./latestDataChecklist";
import { getIndexPerformance, getSectorPerformance, getStockPrice, getCrudePrice, getUSDINR, getGSecYield, getFIIDIIFlows, getIndiaMacroSnapshot, getCompanySnapshot, getCompanyAnnouncements, getLatestResultContext, getShareholdingContext } from "./dataTools";
import { searchSources } from "./sourceSearch";
import { lookupKnowledge } from "./indiaMarketKnowledge";
import { buildMechanism } from "./mechanismBuilder";
import { extractSymbols, nameForSymbol } from "./stockResolver";
import { extractCatalyst } from "./stockCatalystExtractor";
import { planStockSources } from "./stockSourcePlanner";

const pct = (n: number | null) => (n == null ? "n/a" : (n >= 0 ? "+" : "") + n.toFixed(2) + "%");
const round = (n: number | null): number | null => (n == null ? null : Math.round(n * 100) / 100);
const fmtPct = (n: number | null) => (n == null ? "-" : n + "%");

export async function buildContextPack(query: string, plan: ResearchPlan, answerType: AnswerType, disclaimerLevel: DisclaimerLevel): Promise<ContextPack> {
  const md: MarketData = {};
  const facts: string[] = [];
  const limitations: string[] = [];
  const charts: ChartSpec[] = [];
  const extraSources: SourceResult[] = [];
  const need = new Set(plan.requiredData);
  const syms = extractSymbols(query);
  const nameOf = (s: string) => nameForSymbol(s) || s;
  const singleStock = answerType === "single_stock_research";

  const jobs: Promise<void>[] = [];
  if (need.has("indices")) jobs.push(getIndexPerformance().then((d) => { md.indices = d; }));
  if (need.has("sectors")) jobs.push(getSectorPerformance().then((d) => { md.sectors = d; }));
  if (need.has("crude")) jobs.push(getCrudePrice().then((d) => { md.crude = d; }));
  if (need.has("usdinr")) jobs.push(getUSDINR().then((d) => { md.usdinr = d; }));
  if (need.has("gsec")) jobs.push(getGSecYield().then((d) => { md.gsecYield = d; }));
  if (need.has("fiidii")) jobs.push(getFIIDIIFlows().then((d) => { md.fiiDiiFlows = d; }));
  if (need.has("macro")) jobs.push(getIndiaMacroSnapshot().then((d) => { md.macroSnapshot = d; }));
  if ((need.has("stock") || need.has("stocks")) && syms.length) jobs.push(Promise.all(syms.map((s) => getStockPrice(s))).then((d) => { md.stocks = d; }));
  if (need.has("snapshots") && syms.length) jobs.push(Promise.all(syms.map((s) => getCompanySnapshot(s, nameOf(s)))).then((d) => { md.stockSnapshots = d; }));
  if (need.has("announcements") && syms.length) jobs.push(Promise.all(syms.map((s) => getCompanyAnnouncements(s, nameOf(s)))).then((d) => { md.announcements = d; }));
  if (singleStock && syms[0]) {
    jobs.push(getLatestResultContext(syms[0], nameOf(syms[0])).then((d) => { md.results = [d]; }));
    jobs.push(getShareholdingContext(syms[0], nameOf(syms[0])).then((d) => { md.shareholding = [d]; }));
  }

  // For stock questions, deepen source retrieval via the depth-based planner (light/standard/deep budget).
  const isStock = singleStock || answerType === "stock_comparison";
  const stockPlan = isStock ? planStockSources(query, syms[0] ? nameOf(syms[0]) : plan.topic, answerType) : null;
  const sourceQueries = stockPlan ? [...stockPlan.officialQueries, ...stockPlan.searchQueries, ...plan.searchQueries] : plan.searchQueries;
  const sourcesP = searchSources(sourceQueries, stockPlan ? { budget: stockPlan.sourceBudget } : undefined);
  await Promise.all(jobs);
  const sourceSnippets = await sourcesP;

  // ---- facts (attributed) ----
  for (const q of md.indices ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today). [source: NSE/BSE via Yahoo Finance]`);
  if (md.sectors?.length) { const t = md.sectors[0], b = md.sectors[md.sectors.length - 1]; facts.push(`Top sector ${t.name} (${pct(t.changePct)}); weakest ${b.name} (${pct(b.changePct)}). [source: NSE via Yahoo Finance]`); }
  for (const q of md.stocks ?? []) if (q.price != null) facts.push(`${q.label} at ${q.price.toFixed(2)} (${pct(q.changePct)} today). [source: Yahoo Finance]`);
  if (md.crude?.price != null) facts.push(`Brent crude at ${md.crude.price.toFixed(2)} (${pct(md.crude.changePct)}). [source: Yahoo Finance]`);
  if (md.usdinr?.price != null) facts.push(`USD/INR at ${md.usdinr.price.toFixed(2)} (${pct(md.usdinr.changePct)}). [source: Yahoo Finance]`);
  if (md.gsecYield?.yield10Y != null) facts.push(`10Y G-Sec yield ~${md.gsecYield.yield10Y}% (latest available). [source: ${md.gsecYield.source}]`);
  if (md.fiiDiiFlows?.context) facts.push(`FII/DII (latest available): ${md.fiiDiiFlows.context} [source: ${md.fiiDiiFlows.source}]`);
  for (const p of md.macroSnapshot?.points ?? []) if (p.value != null) facts.push(`${p.label}: ${p.value}${p.unit ? p.unit : ""} (${p.freshness === "live" ? "live" : "latest available"}). [source: ${p.source}]`);
  for (const s of md.stockSnapshots ?? []) {
    const parts: string[] = [];
    if (s.marketCap != null) parts.push(`mkt cap ₹${s.marketCap.toLocaleString("en-IN")} Cr`);
    if (s.pe != null) parts.push(`P/E ${s.pe}`);
    if (s.pb != null) parts.push(`P/B ${s.pb}`);
    if (s.roe != null) parts.push(`ROE ${s.roe}%`);
    if (s.dividendYield != null) parts.push(`div yield ${s.dividendYield}%`);
    if (parts.length) facts.push(`${s.symbol} fundamentals: ${parts.join(", ")}. [source: ${s.source}]`);
  }
  for (const rc of md.results ?? []) {
    const bits: string[] = [];
    if (rc.yoyRevenueGrowth != null) bits.push(`revenue ${rc.yoyRevenueGrowth >= 0 ? "+" : ""}${rc.yoyRevenueGrowth}% YoY`);
    if (rc.yoyProfitGrowth != null) bits.push(`profit ${rc.yoyProfitGrowth >= 0 ? "+" : ""}${rc.yoyProfitGrowth}% YoY`);
    if (bits.length || rc.keyCommentary) facts.push(`Latest results: ${bits.join(", ")}${bits.length && rc.keyCommentary ? ". " : ""}${rc.keyCommentary ?? ""} [source: ${rc.source}]`);
  }
  for (const sh of md.shareholding ?? []) {
    const bits: string[] = [];
    if (sh.promoterHolding != null) bits.push(`promoter ${sh.promoterHolding}%`);
    if (sh.fiiHolding != null) bits.push(`FII ${sh.fiiHolding}%`);
    if (sh.diiHolding != null) bits.push(`DII ${sh.diiHolding}%`);
    if (bits.length) facts.push(`Shareholding: ${bits.join(", ")}. [source: ${sh.source}]`);
  }

  const knowledge = lookupKnowledge(query) || lookupKnowledge(plan.topic);
  const mechanism = buildMechanism(query, plan.topic);
  for (const f of knowledge?.facts ?? []) facts.push(`[directional] ${f.text}.`);

  // ---- single-stock catalyst + relative move + stock/result/shareholding charts ----
  if (singleStock) {
    const st = md.stocks?.[0]; const nifty = md.indices?.find((i) => i.label === "Nifty 50");
    if (st?.changePct != null && nifty?.changePct != null) facts.push(`${st.label} moved ${pct(st.changePct)} today vs Nifty ${pct(nifty.changePct)} (relative ${pct(st.changePct - nifty.changePct)}). [source: Yahoo Finance]`);
    const annList = (md.announcements ?? []).flatMap((a) => a.announcements);
    for (const an of annList.slice(0, 3)) facts.push(`News: ${an.title}. [source: ${an.source}]`);
    const catalyst = extractCatalyst(annList.map((a) => ({ type: a.type, title: a.title, snippet: a.snippet })), sourceSnippets.map((s) => ({ title: s.title, snippet: s.snippet })));
    if (catalyst.primaryCatalyst !== "no_clear_catalyst") {
      facts.push(`Likely catalyst: ${catalyst.primaryCatalyst}${catalyst.secondaryCatalysts.length ? " (also " + catalyst.secondaryCatalysts.join(", ") + ")" : ""} [confidence: ${catalyst.confidence}].`);
      charts.push({ type: "comparison_table", title: "Catalyst", dataSource: "catalyst", data: [{ catalyst: catalyst.primaryCatalyst, also: catalyst.secondaryCatalysts.join(", ") || "-", confidence: catalyst.confidence }] });
    } else {
      facts.push("No company-specific catalyst was identified from available sources; the move appears more likely linked to broader sector, flow, or market context.");
    }
    if (st?.spark?.length) charts.push({ type: "line", title: `${st.label} (intraday)`, dataSource: "stock", xKey: "i", yKeys: ["price"], data: st.spark.map((p, i) => ({ i, price: round(p) })) });
    const rc = md.results?.[0];
    if (rc && (rc.yoyRevenueGrowth != null || rc.yoyProfitGrowth != null)) charts.push({ type: "comparison_table", title: "Latest results (YoY)", dataSource: "results", data: [{ revenueYoY: fmtPct(rc.yoyRevenueGrowth), profitYoY: fmtPct(rc.yoyProfitGrowth) }] });
    const sh = md.shareholding?.[0];
    if (sh && (sh.promoterHolding != null || sh.fiiHolding != null)) charts.push({ type: "comparison_table", title: "Shareholding", dataSource: "shareholding", data: [{ promoter: fmtPct(sh.promoterHolding), FII: fmtPct(sh.fiiHolding), DII: fmtPct(sh.diiHolding), public: fmtPct(sh.publicHolding) }] });
  }

  // ---- limitations ----
  if (md.gsecYield?.limitation) limitations.push(md.gsecYield.limitation);
  if (md.fiiDiiFlows?.limitation) limitations.push(md.fiiDiiFlows.limitation);
  if (md.macroSnapshot?.limitation) limitations.push(md.macroSnapshot.limitation);
  for (const s of md.stockSnapshots ?? []) if (s.limitation) limitations.push(`${s.symbol}: ${s.limitation}`);
  for (const rc of md.results ?? []) if (rc.limitation) limitations.push(rc.limitation);
  for (const sh of md.shareholding ?? []) if (sh.limitation) limitations.push(sh.limitation);
  for (const ca of md.announcements ?? []) if (ca.limitation) limitations.push(ca.limitation);
  if (plan.requiresLiveData && (md.indices?.every((q) => q.price == null) ?? false)) limitations.push("Current live market data is unavailable for this query.");

  // ---- source chips ----
  const pushSrc = (title: string, url?: string, snippet?: string, source?: string, published?: string) => { if (url) extraSources.push({ title, url, snippet: snippet ?? "", source: source ?? title, published }); };
  if (md.gsecYield?.yield10Y != null) pushSrc("10Y G-Sec yield", md.gsecYield.sourceUrl, "", md.gsecYield.source, md.gsecYield.date);
  if (md.fiiDiiFlows?.context) pushSrc("FII/DII context", md.fiiDiiFlows.sourceUrl, md.fiiDiiFlows.context, md.fiiDiiFlows.source, md.fiiDiiFlows.date);
  for (const p of md.macroSnapshot?.points ?? []) if (p.value != null && p.sourceUrl) pushSrc(p.label, p.sourceUrl, "", p.source);
  for (const ca of md.announcements ?? []) for (const an of ca.announcements.slice(0, 3)) pushSrc(an.title, an.sourceUrl, an.snippet, an.source, an.date);
  const allSources = dedupeSources([...sourceSnippets, ...extraSources]).sort((a, b) => (a.sourceRank ?? 9) - (b.sourceRank ?? 9));
  // Clean, user-safe limitation only - never expose search/scraper/provider internals.
  if (plan.searchQueries.length && allSources.length === 0 && (answerType === "single_stock_research" || answerType === "current_market_research"))
    limitations.push("Some source pages were unavailable; Maven used available official and retrieved context.");

  // ---- market charts ----
  if (md.indices?.some((q) => q.price != null)) charts.push({ type: "bar", title: "Index moves today", dataSource: "indices", xKey: "name", yKeys: ["changePct"], data: md.indices.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: round(q.changePct) })) });
  if (md.sectors?.length) charts.push({ type: "bar", title: "Sector performance", dataSource: "sectors", xKey: "name", yKeys: ["changePct"], data: md.sectors.map((s) => ({ name: s.name, changePct: round(s.changePct) })) });
  if (md.crude?.spark?.length) charts.push({ type: "line", title: "Brent crude (intraday)", dataSource: "crude", xKey: "i", yKeys: ["price"], data: md.crude.spark.map((p, i) => ({ i, price: round(p) })) });
  if (md.usdinr?.spark?.length) charts.push({ type: "line", title: "USD/INR (intraday)", dataSource: "usdinr", xKey: "i", yKeys: ["price"], data: md.usdinr.spark.map((p, i) => ({ i, price: round(p) })) });
  const cmp = comparisonRows(md.stockSnapshots ?? []);
  if (cmp.length) charts.push({ type: "comparison_table", title: singleStock ? "Key metrics" : "Valuation comparison", dataSource: "snapshots", data: cmp });
  if (mechanism.flow) charts.push(mechanism.flow);

  // ---- verified company data engine: document-extracted + tool-derived metrics, cross-source
  // verification, freshness lock, fact-cache backfill, latest-data checklist ----
  let metricEvidence: MetricEvidence[] | undefined;
  let latestAnnualPeriodFound: string | undefined;
  let sourceQualitySummary: ContextPack["sourceQualitySummary"];
  if (isStock) {
    const companyName = syms[0] ? nameOf(syms[0]) : plan.topic;
    const raw: MetricEvidence[] = [];
    for (const s of md.stockSnapshots ?? []) {
      const add = (metric: MetricEvidence["metric"], label: string, value: number | null, unit?: string) => {
        if (value != null) raw.push({ metric, label: `${s.symbol} ${label}`, value, unit, sourceName: s.source, sourceUrl: s.sourceUrl, sourceDate: s.resultDate ?? undefined, period: s.resultDate ?? undefined, confidence: s.confidence === "verified" ? "verified" : "retrieved", freshness: "unverified", allowedVisible: false });
      };
      add("pe", "P/E", s.pe); add("pb", "P/B", s.pb); add("roe", "ROE", s.roe, "%");
      add("margin", "net margin", s.netMargin, "%"); add("revenueGrowth", "revenue growth", s.revenueGrowth, "%");
    }
    for (const rc of md.results ?? []) {
      if (rc.yoyRevenueGrowth != null) raw.push({ metric: "revenueGrowth", label: "revenue growth YoY", value: rc.yoyRevenueGrowth, unit: "%", period: rc.resultDate ?? undefined, sourceName: rc.source, sourceUrl: rc.sourceUrl, sourceDate: rc.resultDate ?? undefined, confidence: rc.confidence === "verified" ? "verified" : "retrieved", freshness: "unverified", allowedVisible: false });
      if (rc.yoyProfitGrowth != null) raw.push({ metric: "pat", label: "profit growth YoY", value: rc.yoyProfitGrowth, unit: "%", period: rc.resultDate ?? undefined, sourceName: rc.source, sourceUrl: rc.sourceUrl, sourceDate: rc.resultDate ?? undefined, confidence: rc.confidence === "verified" ? "verified" : "retrieved", freshness: "unverified", allowedVisible: false });
    }
    for (const sh of md.shareholding ?? []) {
      if (sh.promoterHolding != null) raw.push({ metric: "shareholding", label: "promoter holding", value: sh.promoterHolding, unit: "%", period: sh.date ?? undefined, sourceName: sh.source, sourceUrl: sh.sourceUrl, sourceDate: sh.date ?? undefined, confidence: sh.confidence === "verified" ? "verified" : "retrieved", freshness: "unverified", allowedVisible: false });
    }
    // NEW: metrics extracted from actual retrieved/extracted document text (not just tool snapshots)
    raw.push(...extractCompanyMetrics(allSources, companyName));

    const crossVerified = crossVerifyMetrics(raw);
    metricEvidence = validateMetricEvidence(crossVerified, query);

    // backfill: fill still-missing metric slots from the warm-instance fact cache (repeat/related
    // questions on the same stock within TTL) - only adds what the current pass didn't already find
    if (syms[0]) {
      const haveMetrics = new Set(metricEvidence.filter((m) => m.allowedVisible).map((m) => `${m.metric}|${m.period ?? ""}`));
      const cached = getFreshCompanyFacts(syms[0]).filter((f) => !haveMetrics.has(`${f.metric}|${f.period ?? ""}`));
      for (const f of cached) metricEvidence.push({ metric: f.metric, label: `${companyName} ${f.metric}`, value: f.value, unit: f.unit, period: f.period, sourceId: f.sourceId, sourceUrl: f.sourceUrl, sourceDate: f.sourceDate, confidence: f.confidence, freshness: f.freshness, allowedVisible: true });
      // save this pass's visible facts for future warm-instance reuse
      const facts: CompanyFact[] = metricEvidence.filter((m) => m.allowedVisible).map((m) => ({ symbol: syms[0], companyName, metric: m.metric, value: m.value, unit: m.unit, period: m.period, sourceId: m.sourceId, sourceUrl: m.sourceUrl, sourceDate: m.sourceDate, confidence: m.confidence, freshness: m.freshness, lastCheckedAt: Date.now() }));
      if (facts.length) saveCompanyFacts(syms[0], facts);
    }

    for (const m of metricEvidence) if (!m.allowedVisible && m.limitation) limitations.push(m.limitation);
    // clean freshness note (task: user-facing, never technical)
    const hasFiscalEvidence = allSources.some((s) => parseAllFiscalTokens(`${s.title} ${s.snippet}`).length > 0) || metricEvidence.some((m) => m.allowedVisible && m.metric !== "price");
    limitations.push(hasFiscalEvidence
      ? "Financial metrics shown are the latest available from official/retrieved sources."
      : "Current financial metrics were not verified from available sources; Maven limits this answer to price action, sector context, and source-backed catalysts.");

    // latest ANNUAL (no-quarter) fiscal period seen in source text, for the checklist/evidence UI
    const cutoff = getLatestCompletedIndianFiscalYear() + 2; // ignore far-future projections
    const annualFy = allSources.flatMap((s) => parseAllFiscalTokens(`${s.title} ${s.snippet}`)).filter((p) => !p.quarter && p.fy <= cutoff).map((p) => p.fy);
    if (annualFy.length) latestAnnualPeriodFound = `FY${Math.max(...annualFy)}`;

    // source quality summary (official/IR/media/generic mix + avg score)
    if (allSources.length) {
      const officialCount = allSources.filter((s) => s.sourceTier === "exchange" || s.sourceTier === "regulator").length;
      const investorRelationsCount = allSources.filter((s) => s.sourceTier === "investor_relations" || s.sourceTier === "filing").length;
      const mediaCount = allSources.filter((s) => s.sourceTier === "media").length;
      const genericCount = allSources.length - officialCount - investorRelationsCount - mediaCount;
      const avgScore = Math.round(allSources.reduce((a, s) => a + (s.sourceQualityScore ?? 0), 0) / allSources.length);
      sourceQualitySummary = { officialCount, investorRelationsCount, mediaCount, genericCount, avgScore };
    }
  }

  const latestDataChecklist = isStock ? buildLatestDataChecklist(md, allSources, metricEvidence ?? []) : undefined;

  return {
    question: query, intent: plan.intent, topic: plan.topic, answerType, disclaimerLevel, marketData: md,
    extractedFacts: facts, sourceSnippets: allSources, chartData: charts, limitations, knowledge, mechanism,
    evidenceHint: stockPlan ? { evidenceDepth: stockPlan.depth, sourceBudget: stockPlan.sourceBudget } : undefined,
    metricEvidence, latestDataChecklist, latestAnnualPeriodFound, sourceQualitySummary,
  };
}

function comparisonRows(snaps: CompanySnapshot[]): Record<string, unknown>[] {
  if (!snaps.length) return [];
  const has = (k: keyof CompanySnapshot) => snaps.some((s) => s[k] != null);
  const cols: [string, keyof CompanySnapshot][] = [];
  if (has("changePct")) cols.push(["change%", "changePct"]);
  if (has("marketCap")) cols.push(["mktCap(Cr)", "marketCap"]);
  if (has("pe")) cols.push(["P/E", "pe"]);
  if (has("pb")) cols.push(["P/B", "pb"]);
  if (has("roe")) cols.push(["ROE%", "roe"]);
  if (has("dividendYield")) cols.push(["Div%", "dividendYield"]);
  if (cols.length === 0) return [];
  return snaps.map((s) => {
    const row: Record<string, unknown> = { name: s.symbol };
    for (const [label, key] of cols) row[label] = s[key];
    return row;
  });
}

function dedupeSources(list: SourceResult[]): SourceResult[] {
  const seen = new Set<string>();
  return list.filter((s) => s.url && !seen.has(s.url) && seen.add(s.url)).slice(0, 8);
}