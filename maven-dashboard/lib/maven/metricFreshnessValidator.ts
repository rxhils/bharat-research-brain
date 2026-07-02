import type { MetricEvidence } from "./types";
import { detectHistoricalRequest, isPeriodStale, parseFiscalPeriod } from "./reportingPeriods";

// Applies the freshness lock to structured metrics before they can reach a visible answer:
//   no source + no period = not visible; old period + current question = not visible;
//   analysis-only numeric claim = not visible. Price/dailyMove from data tools are exempt from
//   the source-URL rule (they carry tool provenance) but still get freshness labels.

const TOOL_METRICS = new Set(["price", "dailyMove", "volume"]);

export function validateMetricEvidence(metrics: MetricEvidence[], query: string, date = new Date()): MetricEvidence[] {
  const historical = detectHistoricalRequest(query, date);
  return metrics.map((m) => {
    const out: MetricEvidence = { ...m };
    const isTool = TOOL_METRICS.has(m.metric);
    const hasSource = !!(m.sourceId || m.sourceUrl || m.sourceName) || isTool;
    const period = m.period ? parseFiscalPeriod(m.period) : null;

    if (!hasSource) { out.freshness = "unverified"; out.allowedVisible = false; out.limitation = `${m.label}: no source - not shown.`; return out; }
    if (m.confidence === "analysis_only" && m.value != null && !isTool) { out.freshness = "unverified"; out.allowedVisible = false; out.limitation = `${m.label}: numeric claim without source evidence - not shown.`; return out; }

    if (period && isPeriodStale(period, date)) {
      if (historical) { out.freshness = "historical_requested"; out.allowedVisible = true; return out; }
      out.freshness = "stale"; out.allowedVisible = false;
      out.limitation = `${m.label} (${m.period}) predates the latest completed fiscal year - not shown as current.`;
      return out;
    }

    // Sourced, non-stale. Tool metrics (live price/volume feeds) are current; the rest are the
    // latest available from their source (point-in-time values like P/E need no fiscal period).
    out.freshness = isTool || m.metric === "pe" || m.metric === "pb" ? "current" : "latest_available";
    out.allowedVisible = true;
    return out;
  });
}
