// Shared types for the Maven Research + Answer-Quality + Stock layers.
export type Intent =
  | "market_summary" | "index_movement" | "sector_impact" | "stock_comparison"
  | "macro_impact" | "single_stock" | "term_explanation" | "unsafe_advice" | "out_of_scope";

export type AnswerType =
  | "greeting" | "basic_concept" | "market_mechanism" | "current_market_research"
  | "stock_comparison" | "single_stock_research" | "macro_sector_impact" | "unsafe_advice" | "out_of_scope" | "unsupported_live_data";

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

export type SourceResult = {
  title: string; url: string; snippet: string; source: string; published?: string;
  provider?: string;                 // "searxng" | "tavily" | "serper" | ...
  confidence?: Confidence;           // verified (official) | retrieved (search/news) | analysis_only
  freshness?: Freshness;
  domain?: string;
  date?: string;
  sourceRank?: number;               // 1 = NSE/BSE/RBI/SEBI, higher = less official
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
};

export type ContextPack = {
  question: string; intent: Intent; topic: string;
  answerType: AnswerType; disclaimerLevel: DisclaimerLevel;
  marketData: MarketData; extractedFacts: string[]; sourceSnippets: SourceResult[];
  chartData: ChartSpec[]; limitations: string[];
  knowledge: KnowledgeEntry | null; mechanism: { chain: string; flow: ChartSpec | null } | null;
  evidenceHint?: { evidenceDepth?: EvidenceDepth; sourceBudget?: number };
};

export type MavenBlock = { type: "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"; title: string; body: string };
export type MavenKeyData = { label: string; value: string; change?: string };
export type MavenSource = { name: string; title?: string; url?: string; date?: string; snippet?: string; type?: string; confidence: Confidence; domain?: string };
export type MavenIntroSection = { title: string; body: string };

export type MavenAnswer = {
  type?: AnswerType;
  disclaimerLevel?: DisclaimerLevel;
  headline: string; summary: string;
  keyData: MavenKeyData[]; charts: ChartSpec[]; blocks: MavenBlock[];
  sources: MavenSource[]; followUps: string[]; disclaimer: string;
  limitations?: string[];
  introSections?: MavenIntroSection[];
  evidence?: MavenEvidenceSummary;
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