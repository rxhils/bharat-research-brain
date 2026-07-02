import type { ChecklistItem, MarketData, MetricEvidence, SourceResult } from "./types";

// Declares what Maven attempted to find for a company query and whether it found it. Derived
// entirely from data already collected elsewhere in the pipeline - never refetches - so this is
// cheap and always in sync with what the answer can actually cite.

function item(item: string, label: string, found: boolean, extra?: Partial<ChecklistItem>): ChecklistItem {
  return { item, label, status: found ? "found" : "missing", ...extra };
}

export function buildLatestDataChecklist(md: MarketData, sources: SourceResult[], metrics: MetricEvidence[]): ChecklistItem[] {
  const stock = md.stocks?.[0];
  const snap = md.stockSnapshots?.[0];
  const results = md.results?.[0];
  const shareholding = md.shareholding?.[0];
  const announcements = (md.announcements ?? []).flatMap((a) => a.announcements);
  const hasDoc = (t: SourceResult["docType"]) => sources.some((s) => s.docType === t);
  const visibleMetric = (keys: MetricEvidence["metric"][]) => metrics.some((m) => m.allowedVisible && keys.includes(m.metric));

  const out: ChecklistItem[] = [];
  out.push(item("price", "Latest price", stock?.price != null, stock?.price != null ? { confidence: "verified" } : { limitation: "Live price unavailable from current sources." }));
  out.push(item("dailyMove", "Latest daily move", stock?.changePct != null, stock?.changePct != null ? { confidence: "verified" } : undefined));
  out.push(item("announcement", "Latest exchange/company announcement", announcements.length > 0, announcements.length > 0 ? { sourceUrl: announcements[0].sourceUrl, sourceDate: announcements[0].date, confidence: announcements[0].confidence === "verified" ? "verified" : "retrieved" } : { limitation: "No recent company announcement found from current sources." }));
  const hasResult = !!results && (results.yoyRevenueGrowth != null || results.yoyProfitGrowth != null);
  out.push(item("quarterlyResult", "Latest quarterly result", hasResult, hasResult ? { latestPeriod: results?.resultDate ?? undefined, sourceUrl: results?.sourceUrl, confidence: results?.confidence === "verified" ? "verified" : "retrieved" } : { limitation: "Latest quarterly result details unavailable from current sources." }));
  out.push(item("investorPresentation", "Latest investor presentation", hasDoc("investor_presentation"), hasDoc("investor_presentation") ? undefined : { limitation: "No investor presentation found from current sources." }));
  out.push(item("annualReport", "Latest annual report", hasDoc("annual_report"), hasDoc("annual_report") ? undefined : { limitation: "No annual report found from current sources." }));
  const hasShareholding = !!shareholding && shareholding.promoterHolding != null;
  out.push(item("shareholding", "Latest shareholding pattern", hasShareholding, hasShareholding ? { latestPeriod: shareholding?.date ?? undefined, sourceUrl: shareholding?.sourceUrl, confidence: shareholding?.confidence === "verified" ? "verified" : "retrieved" } : { limitation: "Latest shareholding pattern unavailable from current sources." }));
  out.push(item("news", "Latest company news/catalyst", announcements.length > 0 || sources.length > 0, undefined));
  const hasValuation = !!snap && (snap.pe != null || snap.pb != null);
  out.push(item("valuation", "Latest valuation metrics", hasValuation, hasValuation ? { confidence: snap?.confidence === "verified" ? "verified" : "retrieved" } : { limitation: "Detailed valuation metrics unavailable from current sources." }));
  const hasFinancials = visibleMetric(["revenue", "revenueGrowth", "ebitda", "pat", "margin"]);
  out.push(item("financialMetrics", "Latest financial metrics", hasFinancials, hasFinancials ? undefined : { limitation: "Latest sourced financial metrics were not available from current sources." }));
  const hasMacro = !!(md.sectors?.length || md.gsecYield || md.fiiDiiFlows);
  out.push(item("sectorMacro", "Latest sector/macro context", hasMacro));
  return out;
}
