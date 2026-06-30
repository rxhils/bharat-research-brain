// Shared types for the Maven Research Layer.
export type Intent =
  | "market_summary" | "index_movement" | "sector_impact" | "stock_comparison"
  | "macro_impact" | "term_explanation" | "unsafe_advice" | "out_of_scope";

export type Quote = { label: string; symbol: string; price: number | null; changePct: number | null; spark?: number[] };
export type SectorPerf = { name: string; changePct: number };
export type Flows = { fiiCr: number | null; diiCr: number | null; asOf: string } | null;
export type SourceResult = { title: string; url: string; snippet: string; source: string; published?: string };

export type ResearchPlan = {
  intent: Intent;
  topic: string;
  requiresLiveData: boolean;
  requiredData: string[];
  searchQueries: string[];
  requiredCharts: string[];
};

export type MarketData = {
  indices?: Quote[];
  sectors?: SectorPerf[];
  stocks?: Quote[];
  crude?: Quote | null;
  usdinr?: Quote | null;
  gsec?: { yieldPct: number | null; asOf: string } | null;
  flows?: Flows;
};

export type ChartSpec = {
  type: "line" | "bar" | "stacked_bar" | "comparison_table" | "area";
  title: string;
  description?: string;
  dataSource: string;
  xKey?: string;
  yKeys?: string[];
  data?: Record<string, unknown>[];
};

export type ContextPack = {
  question: string;
  intent: Intent;
  topic: string;
  marketData: MarketData;
  extractedFacts: string[];
  sourceSnippets: SourceResult[];
  chartData: ChartSpec[];
  limitations: string[];
};

export type MavenBlock = { type: "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"; title: string; body: string };
export type MavenKeyData = { label: string; value: string; change?: string };
export type MavenSource = { name: string; url?: string; recency: string };

export type MavenAnswer = {
  headline: string;
  summary: string;
  keyData: MavenKeyData[];
  charts: ChartSpec[];
  blocks: MavenBlock[];
  sources: MavenSource[];
  followUps: string[];
  disclaimer: string;
};