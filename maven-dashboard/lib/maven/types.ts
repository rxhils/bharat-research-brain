// Shared types for the Maven Research + Answer-Quality layers.
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

// Standard, source-attributed market datum. Every important number carries provenance.
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
  type: "exchange_announcement" | "results" | "corporate_action" | "investor_presentation" | "news_fallback";
  snippet?: string; confidence: DataConfidence;
};
export type CompanyAnnouncements = { symbol: string; announcements: Announcement[]; limitation?: string };
export type CompanySnapshot = { symbol: string; sector?: string; points: MarketDataPoint[]; limitation?: string };

export type SourceResult = { title: string; url: string; snippet: string; source: string; published?: string };

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

export type ContextPack = {
  question: string; intent: Intent; topic: string;
  answerType: AnswerType; disclaimerLevel: DisclaimerLevel;
  marketData: MarketData; extractedFacts: string[]; sourceSnippets: SourceResult[];
  chartData: ChartSpec[]; limitations: string[];
  knowledge: KnowledgeEntry | null; mechanism: { chain: string; flow: ChartSpec | null } | null;
};

export type MavenBlock = { type: "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"; title: string; body: string };
export type MavenKeyData = { label: string; value: string; change?: string };
export type MavenSource = { name: string; title?: string; url?: string; date?: string; snippet?: string; type?: string; confidence: Confidence };

export type MavenAnswer = {
  type?: AnswerType;
  disclaimerLevel?: DisclaimerLevel;
  headline: string; summary: string;
  keyData: MavenKeyData[]; charts: ChartSpec[]; blocks: MavenBlock[];
  sources: MavenSource[]; followUps: string[]; disclaimer: string;
  limitations?: string[];
};
export type ResolvedStock = { companyName: string; symbol: string; exchange: string; sector: string; confidence: "high" | "medium" | "low" };
export type Catalyst = { primaryCatalyst: string; secondaryCatalysts: string[]; confidence: "low" | "medium" | "high"; evidence: string[] };
