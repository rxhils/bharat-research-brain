import type { SourceTier } from "./types";

// Single source of truth for domain -> quality score/tier/official-ness. sourceSearch.ts's
// ranker delegates here so classification logic is never duplicated across modules.
const REGULATOR = /(^|\.)(nseindia\.com|bseindia\.com|rbi\.org\.in|sebi\.gov\.in)$/i;
const MEDIA = /(thehindubusinessline|businessline|livemint|mint\.|economictimes|business-standard|moneycontrol|reuters|bloomberg|cnbctv18|financialexpress|ndtvprofit|thehindu)\./i;
const FILING_PATH = /(investor-presentation|investor-relations|annual-report|quarterly|financial-result|results|shareholding|regulation-filings|corporate-announcement)/i;
const DATA_PAGE = /(screener|tickertape|trendlyne|marketscreener|stockanalysis)\./i;

function hostOf(url: string): string { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; } }
function pathOf(url: string): string { try { return new URL(url).pathname.toLowerCase(); } catch { return ""; } }

export function scoreSource(url: string): { sourceQualityScore: number; sourceTier: SourceTier; official: boolean } {
  const host = hostOf(url);
  const path = pathOf(url);

  if (REGULATOR.test(host)) return { sourceQualityScore: 100, sourceTier: /rbi\.org\.in|sebi\.gov\.in/.test(host) ? "regulator" : "exchange", official: true };
  if (/(^|\.)(investor|ir)\./i.test(host) || /investor|shareholding-pattern/.test(path)) return { sourceQualityScore: 90, sourceTier: "investor_relations", official: true };
  if (FILING_PATH.test(path) || (/\.pdf($|\?)/i.test(path) && !MEDIA.test(host))) return { sourceQualityScore: 85, sourceTier: "filing", official: true };
  if (MEDIA.test(host)) return { sourceQualityScore: 75, sourceTier: "media", official: false };
  if (DATA_PAGE.test(host)) return { sourceQualityScore: 60, sourceTier: "data_page", official: false };
  return { sourceQualityScore: 30, sourceTier: "generic", official: false };
}
