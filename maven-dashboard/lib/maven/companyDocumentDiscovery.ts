import type { DiscoveredDocument, StockDepth } from "./types";
import { searchSources } from "./sourceSearch";
import { getExpectedLatestQuarter, formatFiscalPeriod, getCurrentIndianFiscalYear } from "./reportingPeriods";

// Thin, document-focused layer over the existing search/rank pipeline (sourceSearch.ts already
// owns query execution, official-domain priority, ranking and dedup - this module only adds
// document-typed queries and classifies the results as candidate company documents).

function docQueries(companyName: string): string[] {
  const expQ = formatFiscalPeriod(getExpectedLatestQuarter());
  const curFY = `FY${getCurrentIndianFiscalYear()}`;
  return [
    `${companyName} latest quarterly results ${expQ}`,
    `${companyName} investor presentation latest`,
    `${companyName} annual report latest`,
    `${companyName} shareholding pattern latest`,
    `${companyName} investor relations results ${curFY}`,
    `site:nseindia.com ${companyName} announcement`,
    `site:bseindia.com ${companyName} corporate announcement`,
  ];
}

export async function discoverCompanyDocuments(companyName: string, depth: StockDepth): Promise<DiscoveredDocument[]> {
  const budget = depth === "deep" ? 20 : depth === "standard" ? 12 : 6;
  const sources = await searchSources(docQueries(companyName), { budget });
  return sources
    .filter((s) => s.docType && s.docType !== "other")
    .map((s): DiscoveredDocument => ({
      title: s.title, url: s.url, domain: s.domain ?? "", docType: s.docType!,
      confidence: s.confidence === "verified" ? "verified" : s.confidence === "analysis_only" ? "analysis_only" : "retrieved",
      sourceRank: s.sourceRank ?? 9, sourceQualityScore: s.sourceQualityScore ?? 0,
    }))
    .sort((a, b) => a.sourceRank - b.sourceRank);
}
