import type { ContextPack, MavenAnswer, MavenBlock, MavenReportSection, MetricEvidence, MavenSource, ChartSpec } from "./types";
import { disclaimerText } from "./answerTypeRouter";
import { sanitizeStaleMetrics } from "./staleMetricSanitizer";
import { realSources, buildEvidence } from "./mavenAnswerGenerator";

// Deterministic report assembly - same reliability guarantee as the rest of the freshness-locked
// pipeline (no LLM call, so no hallucination surface for a compliance-sensitive report). Every
// section is built ONLY from ContextPack facts/metricEvidence/sources, then re-run through the
// exact same stale-metric/unsourced-approximation scrubber used for normal answers.

const arrowize = (chain: string) => chain.replace(/->/g, "→");
const pctS = (n: number | null | undefined) => (n == null ? "unavailable" : (n >= 0 ? "+" : "") + n.toFixed(2) + "%");

function metricsFor(evidence: MetricEvidence[] | undefined, metrics: MetricEvidence["metric"][]): MetricEvidence[] {
  return (evidence ?? []).filter((m) => m.allowedVisible && metrics.includes(m.metric));
}
function metricLine(m: MetricEvidence): string {
  return `${m.label}${m.period ? ` (${m.period})` : ""}: ${m.value}${m.unit ?? ""}`;
}

// Reuses the exact stale-metric/unsourced-approximation scrubber from the normal answer path by
// wrapping a section's prose as a minimal MavenAnswer - no separate/duplicated sanitizer logic.
function sectionSanitize(section: MavenReportSection, query: string, sourceText: string): MavenReportSection {
  const wrapper: MavenAnswer = { headline: "", summary: section.summary, keyData: [], charts: [], blocks: section.blocks ?? [], sources: [], followUps: [], disclaimer: "", limitations: section.limitations ?? [] };
  const { fixed } = sanitizeStaleMetrics(wrapper, query, sourceText);
  return { ...section, summary: fixed.summary, blocks: fixed.blocks, limitations: fixed.limitations };
}

function buildCompanySections(pack: ContextPack): MavenReportSection[] {
  const st = pack.marketData.stocks?.[0];
  const rc = pack.marketData.results?.[0];
  const sh = pack.marketData.shareholding?.[0];
  const snap = pack.marketData.stockSnapshots?.[0];
  const me = pack.metricEvidence ?? [];
  const sections: MavenReportSection[] = [];

  sections.push({
    id: "overview", title: "Business Overview", kind: "business_overview",
    summary: `Institutional-style research view on ${pack.topic}, built only from sourced facts - no model-memory business description.` + (pack.knowledge ? " " + pack.knowledge.summary : ""),
    blocks: [{ type: "CONTEXT", title: "Sector context", body: arrowize(pack.mechanism?.chain || "driver → channel → variable → impact → risk") }],
  });

  const moveFact = pack.extractedFacts.find((f) => f.includes("moved") && f.includes("vs Nifty"));
  sections.push({
    id: "price", title: "Latest Price Action", kind: "price_action",
    summary: moveFact || (st?.price != null ? `${st.label} at ${st.price.toFixed(2)} (${pctS(st.changePct)} today).` : "Live price data was unavailable from current sources."),
    charts: st?.spark?.length ? [{ type: "line", title: `${st.label} (intraday)`, dataSource: "stock", xKey: "i", yKeys: ["price"], data: st.spark.map((p, i) => ({ i, price: Math.round(p * 100) / 100 })) }] as ChartSpec[] : undefined,
    metrics: metricsFor(me, ["price", "dailyMove"]),
  });

  const resultBits: string[] = [];
  if (rc?.yoyRevenueGrowth != null) resultBits.push(`revenue ${pctS(rc.yoyRevenueGrowth)} YoY`);
  if (rc?.yoyProfitGrowth != null) resultBits.push(`profit ${pctS(rc.yoyProfitGrowth)} YoY`);
  const resultMetrics = metricsFor(me, ["revenue", "revenueGrowth", "ebitda", "pat", "margin"]);
  sections.push({
    id: "results", title: "Latest Results and Financials", kind: "latest_results",
    summary: resultBits.length ? `Latest reported period: ${resultBits.join(", ")}.` + (rc?.keyCommentary ? " " + rc.keyCommentary : "")
      : resultMetrics.length ? resultMetrics.map(metricLine).join("; ") + "."
      : "Latest sourced financial results were not available from official/retrieved sources - Maven does not show a current figure without a source.",
    metrics: resultMetrics,
    limitations: rc?.limitation ? [rc.limitation] : undefined,
  });

  const catFact = pack.extractedFacts.find((f) => f.startsWith("Likely catalyst"));
  const noCat = pack.extractedFacts.find((f) => f.startsWith("No company-specific"));
  const newsFacts = pack.extractedFacts.filter((f) => f.startsWith("News: ")).slice(0, 4);
  sections.push({
    id: "catalysts", title: "Company-Specific Catalysts", kind: "catalysts",
    summary: catFact || noCat || "No company-specific catalyst was identified from available sources.",
    blocks: newsFacts.length ? newsFacts.map((n): MavenBlock => ({ type: "DATA", title: "Reported", body: n })) : undefined,
  });

  const valMetrics = metricsFor(me, ["pe", "pb", "roe", "roce", "debtToEquity"]);
  sections.push({
    id: "valuation", title: "Valuation and Metrics", kind: "valuation",
    summary: valMetrics.length ? valMetrics.map(metricLine).join("; ") + "." : "Current valuation metrics were not verified from available sources.",
    metrics: valMetrics,
    charts: snap && (snap.pe != null || snap.pb != null || snap.roe != null) ? [{ type: "comparison_table", title: "Key metrics", dataSource: "snapshot", data: [{ symbol: snap.symbol, "P/E": snap.pe, "P/B": snap.pb, "ROE%": snap.roe }] }] as ChartSpec[] : undefined,
  });

  const shBits: string[] = [];
  if (sh?.promoterHolding != null) shBits.push(`promoter ${sh.promoterHolding}%`);
  if (sh?.fiiHolding != null) shBits.push(`FII ${sh.fiiHolding}%`);
  if (sh?.diiHolding != null) shBits.push(`DII ${sh.diiHolding}%`);
  const shMetrics = metricsFor(me, ["shareholding", "pledge"]);
  sections.push({
    id: "shareholding", title: "Shareholding and Ownership", kind: "shareholding",
    summary: shBits.length ? `Latest sourced shareholding: ${shBits.join(", ")}.` : shMetrics.length ? shMetrics.map(metricLine).join("; ") + "." : "Current shareholding pattern was not available from official/retrieved sources.",
    metrics: shMetrics,
    limitations: sh?.limitation ? [sh.limitation] : undefined,
  });

  sections.push({
    id: "sector_macro", title: "Sector and Macro Context", kind: "sector_macro",
    summary: arrowize(pack.mechanism?.chain || "driver → channel → variable → impact → risk") + (pack.knowledge ? ". " + pack.knowledge.summary : ""),
    charts: pack.chartData.filter((c) => c.dataSource === "sectors" || c.dataSource === "indices"),
  });

  sections.push({
    id: "risks", title: "Key Risks", kind: "risks",
    summary: "Company-specific confirmation from open sources is limited; treat catalysts and metrics as the latest available rather than assured as current, and cross-check the official filing.",
    blocks: [{ type: "RISK", title: "What is not confirmed", body: pack.limitations.length ? pack.limitations.join(" ") : "Watch market breadth, the FII vs DII balance, and any shift in the RBI rate/liquidity stance." }],
  });

  sections.push({
    id: "watch", title: "What To Watch Next", kind: "watch_items",
    summary: "Next scheduled catalysts to monitor: upcoming quarterly results, investor presentations, and shareholding filings as they are released.",
  });

  return sections;
}

function buildComparisonSections(pack: ContextPack): MavenReportSection[] {
  const stocks = pack.marketData.stocks ?? [];
  const snaps = pack.marketData.stockSnapshots ?? [];
  const me = pack.metricEvidence ?? [];
  const names = snaps.map((s) => s.symbol).join(" vs ") || pack.topic;
  const sections: MavenReportSection[] = [];

  sections.push({
    id: "summary", title: "Comparison Summary", kind: "business_overview",
    summary: `Side-by-side institutional-style comparison of ${names || pack.topic}, built only from sourced facts.` + (pack.knowledge ? " " + pack.knowledge.summary : ""),
  });

  sections.push({
    id: "price", title: "Price and Relative Performance", kind: "price_action",
    summary: stocks.filter((s) => s.price != null).map((s) => `${s.label} ${pctS(s.changePct)} today`).join("; ") || "Live price data was unavailable from current sources.",
    charts: pack.chartData.filter((c) => c.dataSource === "indices"),
    metrics: metricsFor(me, ["price", "dailyMove"]),
  });

  sections.push({
    id: "business_mix", title: "Business Mix", kind: "business_overview",
    summary: snaps.map((s) => s.sector || s.industry).filter(Boolean).length
      ? snaps.map((s) => `${s.symbol}: ${s.industry || s.sector}`).join("; ") + "."
      : "Sector/industry classification was not available from current sources for one or both companies.",
  });

  const newsFacts = pack.extractedFacts.filter((f) => f.startsWith("News: ")).slice(0, 4);
  const resultMetrics = metricsFor(me, ["revenue", "revenueGrowth", "ebitda", "pat", "margin"]);
  sections.push({
    id: "results", title: "Latest Results", kind: "latest_results",
    summary: resultMetrics.length ? resultMetrics.map(metricLine).join("; ") + "." : "Latest sourced results were not available from official/retrieved sources for these companies.",
    blocks: newsFacts.length ? newsFacts.map((n): MavenBlock => ({ type: "DATA", title: "Reported", body: n })) : undefined,
    metrics: resultMetrics,
  });

  const valMetrics = metricsFor(me, ["pe", "pb", "roe"]);
  const cmpChart = pack.chartData.find((c) => c.dataSource === "snapshots");
  sections.push({
    id: "valuation", title: "Valuation Metrics", kind: "valuation",
    summary: valMetrics.length ? valMetrics.map(metricLine).join("; ") + "." : "Current valuation metrics were not verified from available sources.",
    metrics: valMetrics,
    charts: cmpChart ? [cmpChart] : undefined,
  });

  const qualityMetrics = metricsFor(me, ["roce", "debtToEquity"]);
  sections.push({
    id: "quality", title: "Balance Sheet / Quality Metrics", kind: "financial_metrics",
    summary: qualityMetrics.length ? qualityMetrics.map(metricLine).join("; ") + "." : "Balance-sheet quality metrics (ROCE, debt/equity) were not verified from available sources for these companies.",
    metrics: qualityMetrics,
  });

  sections.push({
    id: "sector_macro", title: "Sector and Macro Context", kind: "sector_macro",
    summary: arrowize(pack.mechanism?.chain || "driver → channel → variable → impact → risk") + (pack.knowledge ? ". " + pack.knowledge.summary : ""),
    charts: pack.chartData.filter((c) => c.dataSource === "sectors"),
  });

  sections.push({
    id: "risks", title: "Risks", kind: "risks",
    summary: "Comparative confirmation from open sources is limited for both names; treat metrics as the latest available rather than assured as current.",
    blocks: [{ type: "RISK", title: "What is not confirmed", body: pack.limitations.length ? pack.limitations.join(" ") : "Watch market breadth, sector rotation, and each company's own catalysts before drawing a conclusion." }],
  });

  return sections;
}

export function generateDeepResearchReport(pack: ContextPack, reportType: "company_deep_research" | "stock_comparison_report"): MavenAnswer {
  const disc = disclaimerText(pack.disclaimerLevel);
  const sourceText = [
    ...pack.sourceSnippets.map((s) => `${s.title} ${s.snippet} ${s.date ?? s.published ?? ""}`),
    ...pack.extractedFacts,
  ].join("\n");

  let sections = reportType === "stock_comparison_report" ? buildComparisonSections(pack) : buildCompanySections(pack);
  sections = sections.map((sec) => sectionSanitize(sec, pack.question, sourceText));

  const sources = realSources(pack);
  // Evidence and Limitations is always the closing section, built from the (already sanitized)
  // sources/limitations - added last so it reflects any limitations sectionSanitize appended.
  const allLimitations = [...new Set([...pack.limitations, ...sections.flatMap((s) => s.limitations ?? [])])];
  sections.push({
    id: "evidence", title: "Evidence and Limitations", kind: "evidence",
    summary: `This report is built from ${pack.sourceSnippets.length} reviewed source${pack.sourceSnippets.length === 1 ? "" : "s"}.`,
    sources: sources.filter((s) => s.type !== "analysis"),
    limitations: allLimitations,
  });

  const title = reportType === "stock_comparison_report" ? `${pack.topic}: Deep Research Comparison` : `${pack.topic}: Deep Research Report`;
  const summary = reportType === "stock_comparison_report"
    ? `Institutional-style comparison of ${pack.topic}, built from ${pack.sourceSnippets.length} sourced references. Educational research only - not a recommendation.`
    : `Institutional-style research view on ${pack.topic}, built from ${pack.sourceSnippets.length} sourced references. Educational research only - not a recommendation.`;

  const allCharts = sections.flatMap((s) => s.charts ?? []).slice(0, 8);

  return {
    headline: title, summary,
    keyData: [], charts: allCharts, blocks: [],
    sources, followUps: [
      reportType === "stock_comparison_report" ? `What is the single biggest risk between these two companies?` : `What would change the view on ${pack.topic}?`,
      "What is the latest reported quarter?",
      "What official filings support this?",
    ],
    disclaimer: disc,
    evidence: buildEvidence(pack, sources),
    latestDataChecklist: pack.latestDataChecklist,
    reportMode: true, reportTitle: title, reportSummary: summary, reportSections: sections,
  };
}
