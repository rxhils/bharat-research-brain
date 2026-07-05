// Shared types for the Maven Research + Answer-Quality + Stock layers.
export type Intent =
  | "market_summary" | "index_movement" | "sector_impact" | "stock_comparison"
  | "macro_impact" | "single_stock" | "term_explanation" | "unsafe_advice" | "out_of_scope";

export type AnswerType =
  | "greeting" | "basic_concept" | "market_mechanism" | "current_market_research"
  | "stock_comparison" | "single_stock_research" | "macro_sector_impact" | "unsafe_advice" | "out_of_scope" | "unsupported_live_data"
  | "deep_research_report" | "comparison_research_report";

export type DisclaimerLevel = "none" | "light" | "standard" | "strong";
export type Confidence = "verified" | "retrieved" | "analysis_only" | "unavailable";
export type Freshness = "live" | "latest_available" | "delayed" | "stale" | "unavailable";
export type DataConfidence = "verified" | "retrieved" | "estimated" | "unavailable";

export type MarketDataPoint = {
  key: string; label: string; value: number | string | null; unit?: string;
  change?: number | null; changePct?: number | null; timestamp?: string;
  source: string; sourceUrl?: string;
  freshness: Freshness; confidence: DataConfidence; limitation?: string;
};

export type Quote = { label: string; symbol: string; price: number | null; changePct: number | null; spark?: number[] };
export type SectorPerf = { name: string; changePct: number };

export type FiiDiiFlows = {
  date?: string; fiiCashNet: number | null; diiCashNet: number | null;
  fiiIndexFuturesNet?: number | null; fiiStockFuturesNet?: number | null;
  context?: string; source: string; sourceUrl?: string;
  freshness: Freshness; confidence: DataConfidence; limitation?: string;
};
export type GSecYield = {
  date?: string; yield10Y: number | null; changeBps?: number | null;
  source: string; sourceUrl?: string; freshness: Freshness; confidence: DataConfidence; limitation?: string;
};
export type MacroSnapshot = { points: MarketDataPoint[]; limitation?: string };

export type Announcement = {
  title: string; date?: string; source: string; sourceUrl?: string;
  type: "exchange_announcement" | "quarterly_result" | "investor_presentation" | "corporate_action" | "management_commentary" | "news_fallback";
  snippet?: string; confidence: DataConfidence;
};
export type CompanyAnnouncements = { symbol: string; announcements: Announcement[]; limitation?: string };

export type CompanySnapshot = {
  symbol: string; companyName?: string; sector?: string; industry?: string;
  price: number | null; change: number | null; changePct: number | null;
  marketCap: number | null; pe: number | null; pb: number | null; roe: number | null; roce: number | null;
  dividendYield: number | null; eps: number | null; bookValue: number | null; debtToEquity: number | null;
  revenueGrowth: number | null; profitGrowth: number | null; operatingMargin: number | null; netMargin: number | null;
  fiftyTwoWeekHigh: number | null; fiftyTwoWeekLow: number | null; resultDate: string | null;
  source: string; sourceUrl?: string; freshness: Freshness; confidence: DataConfidence;
  unavailableFields: string[]; limitation?: string;
};

export type ResultContext = {
  resultDate: string | null; revenue: number | null; ebitda: number | null; pat: number | null; margin: number | null;
  yoyRevenueGrowth: number | null; yoyProfitGrowth: number | null; qoqRevenueGrowth: number | null; qoqProfitGrowth: number | null;
  keyCommentary?: string; source: string; sourceUrl?: string; confidence: DataConfidence; unavailableFields: string[]; limitation?: string;
};
export type ShareholdingContext = {
  date: string | null; promoterHolding: number | null; fiiHolding: number | null; diiHolding: number | null;
  publicHolding: number | null; pledgedHolding: number | null; source: string; sourceUrl?: string; confidence: DataConfidence; limitation?: string;
};

export type DocumentType = "quarterly_result" | "investor_presentation" | "annual_report" | "shareholding_pattern" | "exchange_announcement" | "news" | "other";
export type SourceTier = "exchange" | "investor_relations" | "filing" | "regulator" | "media" | "data_page" | "generic";

export type SourceResult = {
  title: string; url: string; snippet: string; source: string; published?: string;
  provider?: string;                 // "searxng" | "tavily" | "serper" | ... | "google_news_rss"
  confidence?: Confidence;           // verified (official) | retrieved (search/news) | analysis_only
  freshness?: Freshness;
  domain?: string;
  domainHint?: string;                // true publisher domain when `url` is a redirector (e.g. Google News), used for tier classification
  date?: string;
  sourceRank?: number;               // 1 = NSE/BSE/RBI/SEBI, higher = less official
  sourceQualityScore?: number;       // 0-100
  sourceTier?: SourceTier;
  official?: boolean;
  docType?: DocumentType;
  extractionStatus?: "success" | "partial" | "failed";
};

export type ExtractedPage = {
  title: string; url: string; domain: string; text: string; date?: string;
  extractionStatus: "success" | "partial" | "failed";
};

export type ResearchPlan = {
  intent: Intent; topic: string; requiresLiveData: boolean;
  requiredData: string[]; searchQueries: string[]; requiredCharts: string[];
};

export type MarketData = {
  indices?: Quote[]; sectors?: SectorPerf[]; stocks?: Quote[];
  crude?: Quote | null; usdinr?: Quote | null;
  fiiDiiFlows?: FiiDiiFlows | null;
  gsecYield?: GSecYield | null;
  macroSnapshot?: MacroSnapshot | null;
  stockSnapshots?: CompanySnapshot[];
  announcements?: CompanyAnnouncements[];
  results?: ResultContext[];
  shareholding?: ShareholdingContext[];
};

export type ChartSpec = {
  type: "line" | "bar" | "stacked_bar" | "comparison_table" | "area" | "flow";
  title: string; description?: string; dataSource: string;
  xKey?: string; yKeys?: string[]; data?: Record<string, unknown>[];
};

export type KnowledgeFact = { text: string; confidence: "verified"; directional?: boolean };
export type KnowledgeEntry = {
  key: string; aliases: string[]; topic: string; summary: string;
  chain: string; winners: string[]; losers: string[];
  facts: KnowledgeFact[]; followUps: string[];
};

export type EvidenceDepth = "light" | "standard" | "deep";
export type CoverageStatus = "strong" | "partial" | "thin" | "unavailable";
export type MavenEvidenceSummary = {
  sourceCount?: number;
  verifiedSourceCount?: number;
  retrievedSourceCount?: number;
  officialSourceCount?: number;
  analysisOnlySourceCount?: number;
  unavailableSourceCount?: number;
  evidenceDepth?: EvidenceDepth;
  sourceBudget?: number;
  coverageStatus?: CoverageStatus;
  latestPeriodFound?: string; // e.g. "Q4FY26" - latest fiscal period seen in retrieved sources
  latestAnnualPeriodFound?: string; // e.g. "FY26" - latest annual (no-quarter) period seen
  metricEvidenceCount?: number; // metricEvidence entries that passed the freshness lock (allowedVisible)
  blockedMetricCount?: number;  // metricEvidence entries blocked (stale/unsourced/unverified)
};

// Freshness lock: every company financial metric must be evidence-backed, period-labeled and
// freshness-validated before it may appear in a visible answer.
export type MetricFreshness = "current" | "latest_available" | "stale" | "historical_requested" | "unverified";
export type MetricEvidence = {
  metric:
    | "price" | "dailyMove" | "volume" | "revenue" | "revenueGrowth" | "ebitda" | "pat" | "margin"
    | "marketShare" | "pe" | "pb" | "roe" | "roce" | "debtToEquity" | "capex" | "orderBook"
    | "guidance" | "shareholding" | "pledge" | "marketSize" | "cagr" | "other";
  label: string;
  value: string | number | null;
  unit?: string;
  period?: string;
  sourceId?: string;
  sourceName?: string;
  sourceUrl?: string;
  sourceDate?: string;
  confidence: "verified" | "retrieved" | "cross_verified" | "analysis_only" | "unavailable";
  freshness: MetricFreshness;
  allowedVisible: boolean;
  limitation?: string;
};

// Latest-data checklist: for company-specific queries, Maven declares what it attempted to find
// and whether it found it - shown to the user so "no data" is visibly a checked box, not a gap.
export type ChecklistStatus = "found" | "missing" | "not_required";
export type ChecklistItem = {
  item: string; label: string; status: ChecklistStatus;
  latestPeriod?: string; sourceId?: string; sourceUrl?: string; sourceDate?: string;
  confidence?: "verified" | "retrieved" | "analysis_only" | "unavailable"; limitation?: string;
};

export type DiscoveredDocument = {
  title: string; url: string; domain: string; docType: DocumentType;
  confidence: "verified" | "retrieved" | "analysis_only"; sourceRank: number; sourceQualityScore: number;
};

export type CompanyFact = {
  symbol: string; companyName: string; metric: MetricEvidence["metric"]; value: string | number | null;
  unit?: string; period?: string; sourceId?: string; sourceUrl?: string; sourceDate?: string;
  confidence: MetricEvidence["confidence"]; freshness: MetricFreshness; lastCheckedAt: number;
};

export type SourceQualitySummary = { officialCount: number; investorRelationsCount: number; mediaCount: number; genericCount: number; avgScore: number };

export type ContextPack = {
  question: string; intent: Intent; topic: string;
  answerType: AnswerType; disclaimerLevel: DisclaimerLevel;
  marketData: MarketData; extractedFacts: string[]; sourceSnippets: SourceResult[];
  chartData: ChartSpec[]; limitations: string[];
  knowledge: KnowledgeEntry | null; mechanism: { chain: string; flow: ChartSpec | null } | null;
  evidenceHint?: { evidenceDepth?: EvidenceDepth; sourceBudget?: number };
  metricEvidence?: MetricEvidence[];
  latestDataChecklist?: ChecklistItem[];
  latestAnnualPeriodFound?: string;
  sourceQualitySummary?: SourceQualitySummary;
};

export type MavenBlock = { type: "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"; title: string; body: string };
export type MavenKeyData = { label: string; value: string; change?: string };
export type MavenSource = { name: string; title?: string; url?: string; date?: string; snippet?: string; type?: string; confidence: Confidence; domain?: string };
export type MavenIntroSection = { title: string; body: string };

// Deep Research Report Mode: a company/comparison report is a sequence of self-contained
// sections instead of one short chat card. Every section still runs through the same
// freshness lock / evidence rules as a normal answer - it is a different shape, not a
// different trust model.
export type MavenReportSectionKind =
  | "business_overview" | "price_action" | "latest_results" | "catalysts" | "financial_metrics"
  | "valuation" | "shareholding" | "peer_comparison" | "sector_macro" | "risks" | "watch_items" | "evidence";
export type MavenReportSection = {
  id: string; title: string; kind: MavenReportSectionKind;
  summary: string; blocks?: MavenBlock[]; charts?: ChartSpec[]; metrics?: MetricEvidence[]; sources?: MavenSource[]; limitations?: string[];
};

export type MavenAnswer = {
  type?: AnswerType;
  disclaimerLevel?: DisclaimerLevel;
  headline: string; summary: string;
  keyData: MavenKeyData[]; charts: ChartSpec[]; blocks: MavenBlock[];
  sources: MavenSource[]; followUps: string[]; disclaimer: string;
  limitations?: string[];
  introSections?: MavenIntroSection[];
  evidence?: MavenEvidenceSummary;
  latestDataChecklist?: ChecklistItem[];
  reportMode?: boolean;
  reportTitle?: string;
  reportSummary?: string;
  reportSections?: MavenReportSection[];
};

export type ResolvedStock = { companyName: string; symbol: string; exchange: string; sector: string; confidence: "high" | "medium" | "low" };

export type NseSecurity = {
  symbol: string; companyName: string; series?: string; isin?: string;
  faceValue?: number; dateOfListing?: string; paidUpValue?: number; marketLot?: number;
  segment: "equity" | "sme" | "etf" | "reit" | "invit" | "permitted" | "unknown";
  yahooSymbol?: string; bseCode?: string;
  aliases: string[]; oldSymbols: string[]; oldNames: string[];
  status: "active" | "suspended" | "delisted" | "unknown"; lastUpdated: string;
};

export type StockResolution = {
  status: "resolved" | "ambiguous" | "not_found";
  primary?: NseSecurity; candidates?: NseSecurity[];
  confidence: number; reason: string;
};

export type StockDepth = "light" | "standard" | "deep";
export type StockSourcePlan = {
  depth: StockDepth; sourceBudget: number;
  requiredSources: string[]; searchQueries: string[]; officialQueries: string[]; chartNeeds: string[];
};
export type Catalyst = { primaryCatalyst: string; secondaryCatalysts: string[]; confidence: "none" | "low" | "medium" | "high"; evidence: string[] };