// Frontend contract for the /api/ask Research Layer v2 response.
export type MavenAnswerType =
  | "greeting" | "basic_concept" | "market_mechanism" | "current_market_research"
  | "stock_comparison" | "macro_sector_impact" | "unsafe_advice" | "out_of_scope" | "unsupported_live_data";

export type MavenBlock = { type: "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"; title: string; body: string };

export type MavenChart = {
  type: "line" | "bar" | "area" | "stacked_bar" | "comparison_table" | "sector_heatmap" | "flow" | "flow_chart" | "valuation_chart" | "market_breadth_gauge";
  title: string;
  description?: string;
  data?: Record<string, unknown>[];
  xKey?: string;
  yKeys?: string[];
  dataSource?: string;
};

export type MavenSource = {
  name: string; title?: string; url?: string; date?: string; recency?: string; snippet?: string; type?: string;
  confidence?: "verified" | "retrieved" | "analysis_only" | "unavailable";
  domain?: string;
};

export type MavenKeyData = { label: string; value: string; change?: string };
export type MavenIntroSection = { title: string; body: string };

export type MavenEvidenceDepth = "light" | "standard" | "deep";
export type MavenCoverageStatus = "strong" | "partial" | "thin" | "unavailable";
export type MavenEvidenceSummary = {
  sourceCount?: number;
  verifiedSourceCount?: number;
  retrievedSourceCount?: number;
  officialSourceCount?: number;
  analysisOnlySourceCount?: number;
  unavailableSourceCount?: number;
  evidenceDepth?: MavenEvidenceDepth;
  sourceBudget?: number;
  coverageStatus?: MavenCoverageStatus;
  latestPeriodFound?: string;
  latestAnnualPeriodFound?: string;
};

export type MavenChecklistStatus = "found" | "missing" | "not_required";
export type MavenChecklistItem = {
  item: string; label: string; status: MavenChecklistStatus;
  latestPeriod?: string; sourceUrl?: string; sourceDate?: string;
  confidence?: "verified" | "retrieved" | "analysis_only" | "unavailable"; limitation?: string;
};

export type MavenAskResponse = {
  type?: MavenAnswerType;
  answerType?: MavenAnswerType;
  headline: string;
  summary: string;
  keyData?: MavenKeyData[];
  charts?: MavenChart[];
  blocks: MavenBlock[];
  sources: MavenSource[];
  followUps: string[];
  disclaimer?: string;
  disclaimerLevel?: "none" | "light" | "standard" | "strong";
  limitations?: string[];
  introSections?: MavenIntroSection[];
  evidence?: MavenEvidenceSummary;
  latestDataChecklist?: MavenChecklistItem[];
};