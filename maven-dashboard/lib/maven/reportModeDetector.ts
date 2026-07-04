import type { AnswerType } from "./types";

// Detects an explicit request for an institutional-style report instead of a normal short
// chat answer. Deliberately phrase-based (not just "any single-stock question") so ordinary
// questions like "Explain HDFC Bank today" keep the existing short-card behavior.
export type ReportType = "company_deep_research" | "stock_comparison_report" | "sector_report" | "macro_report" | "none";
export type ReportModeResult = { reportMode: boolean; reportType: ReportType; depth: "standard" | "deep" };

const REPORT_PHRASES = /\b(full research report|full report|deep research|deep dive|deeply|in detail|full view|detailed analysis|investment thesis|business breakdown|risks? in detail|complete report|complete (?:view|picture|analysis)|research note|institutional[- ]?style report|everything about)\b/i;

export function detectReportMode(query: string, answerType: AnswerType): ReportModeResult {
  const q = (query || "").trim();
  if (!REPORT_PHRASES.test(q)) return { reportMode: false, reportType: "none", depth: "standard" };

  // A report request always wants the deepest available coverage - there is no "shallow report".
  if (answerType === "stock_comparison") return { reportMode: true, reportType: "stock_comparison_report", depth: "deep" };
  if (answerType === "single_stock_research") return { reportMode: true, reportType: "company_deep_research", depth: "deep" };
  // sector_report/macro_report are reserved for a future build - this task only wires up
  // company + comparison report generation, per scope.
  return { reportMode: false, reportType: "none", depth: "standard" };
}
