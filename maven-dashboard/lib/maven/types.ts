// Shared types for the Maven Research + Answer-Quality layers.
export type Intent =
  | "market_summary" | "index_movement" | "sector_impact" | "stock_comparison"
  | "macro_impact" | "term_explanation" | "unsafe_advice" | "out_of_scope";

export type AnswerType =
  | "greeting" | "basic_concept" | "market_mechanism" | "current_market_research"
  | "stock_comparison" | "macro_sector_impact" | "unsafe_advice" | "out_of_scope" | "unsupported_live_data";

export type DisclaimerLevel = "none" | "light" | "standard" | "strong";
export type Confidence = "verified" | "retrieved" | "analysis_only" | "unavailable";

export type Quote = { label: string; symbol: string; price: number | null; changePct: number | null; spark?: number[] };
export type SectorPerf = { name: string; changePct: number };
export type Flows = { fiiCr: number | null; diiCr: number | null; asOf: string } | null;

export type SourceResult = { title: string; url: string; snippet: string; source: string; published?: string };

export type ResearchPlan = {
  intent: Intent; topic: string; requiresLiveData: boolean;
  requiredData: string[]; searchQueries: string[]; requiredCharts: string[];
};

export type MarketData = {
  indices?: Quote[]; sectors?: SectorPerf[]; stocks?: Quote[];
  crude?: Quote | null; usdinr?: Quote | null;
  gsec?: { yieldPct: number | null; asOf: string } | null; flows?: Flows;
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
};