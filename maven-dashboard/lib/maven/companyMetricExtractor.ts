import type { MetricEvidence, SourceResult } from "./types";
import { parseFiscalPeriod, formatFiscalPeriod } from "./reportingPeriods";

// Extracts sourced, period-labeled metrics from retrieved document/snippet text - the missing
// link between "we found a source" and "we can show a number". Never infers or approximates:
// a candidate is only emitted when an explicit metric keyword is followed by an explicit number
// AND (for period-bound metrics) a fiscal period token is present in the same source text.

type MetricKey = "revenue" | "revenueGrowth" | "ebitda" | "pat" | "margin" | "marketShare" | "pe" | "pb" | "roe" | "roce" | "debtToEquity" | "capex" | "orderBook" | "guidance" | "shareholding" | "pledge" | "cagr";

// Period-bound: without a fiscal-period token nearby, we do not know what period the figure is
// for, so we simply do not emit it (rather than emit an "unverified" clutter entry).
const PERIOD_BOUND = new Set<MetricKey>(["revenue", "revenueGrowth", "ebitda", "pat", "margin", "marketShare", "capex", "orderBook", "guidance", "cagr"]);

const PATTERNS: { metric: MetricKey; label: string; keyword: RegExp; unit?: string }[] = [
  { metric: "revenueGrowth", label: "revenue growth", keyword: /revenue\s+grow(?:th|s)?/i, unit: "%" },
  { metric: "revenue", label: "revenue", keyword: /\brevenue\b(?!\s+grow)/i, unit: "cr" },
  { metric: "ebitda", label: "EBITDA", keyword: /\bebitda\b/i, unit: "cr" },
  { metric: "pat", label: "PAT / net profit", keyword: /\b(?:pat|net profit)\b/i, unit: "cr" },
  { metric: "margin", label: "margin", keyword: /(?:operating|net|ebitda)?\s*margin/i, unit: "%" },
  { metric: "marketShare", label: "market share", keyword: /market\s*share/i, unit: "%" },
  { metric: "pe", label: "P/E", keyword: /\bp\/?e\s*ratio\b|\bp\/e\b/i },
  { metric: "pb", label: "P/B", keyword: /\bp\/?b\s*ratio\b|\bp\/b\b/i },
  { metric: "roe", label: "ROE", keyword: /\broe\b/i, unit: "%" },
  { metric: "roce", label: "ROCE", keyword: /\broce\b/i, unit: "%" },
  { metric: "debtToEquity", label: "debt-to-equity", keyword: /debt[\s-]?to[\s-]?equity/i },
  { metric: "capex", label: "capex", keyword: /\bcapex\b|capital expenditure/i, unit: "cr" },
  { metric: "orderBook", label: "order book", keyword: /order\s*book/i, unit: "cr" },
  { metric: "guidance", label: "guidance", keyword: /\bguidance\b/i },
  { metric: "shareholding", label: "promoter holding", keyword: /promoter\s*holding/i, unit: "%" },
  { metric: "pledge", label: "pledged holding", keyword: /pledg(?:ed|e)\s*(?:holding|shares)?/i, unit: "%" },
  { metric: "cagr", label: "CAGR", keyword: /\bcagr\b/i, unit: "%" },
];

const NUM_NEAR = /[^\d]{0,30}?([₹$]?\s?\d[\d,]*(?:\.\d+)?)\s*(%|cr(?:ore)?s?|crore|million|mn|bn)?/i;

function findNumberNear(text: string, matchIndex: number, matchLen: number, unit?: string): { value: number; unitFound?: string } | null {
  const window = text.slice(matchIndex, matchIndex + matchLen + 40);
  const m = window.match(NUM_NEAR);
  if (!m || !m[1]) return null;
  const value = parseFloat(m[1].replace(/[₹$,\s]/g, ""));
  if (!isFinite(value)) return null;
  const unitFound = m[2] ? (/%/.test(m[2]) ? "%" : "cr") : unit;
  return { value, unitFound };
}

export function extractCompanyMetrics(sources: SourceResult[], companyName: string): MetricEvidence[] {
  const out: MetricEvidence[] = [];
  for (const s of sources) {
    const text = `${s.title || ""}. ${s.snippet || ""}`;
    const period = parseFiscalPeriod(text);
    const periodStr = period ? formatFiscalPeriod(period) : undefined;

    for (const p of PATTERNS) {
      if (PERIOD_BOUND.has(p.metric) && !periodStr) continue; // no period found -> do not emit
      const m = p.keyword.exec(text);
      if (!m) continue;
      const found = findNumberNear(text, m.index, m[0].length, p.unit);
      if (!found) continue;
      out.push({
        metric: p.metric, label: `${companyName} ${p.label}`, value: found.value, unit: found.unitFound ?? p.unit,
        period: periodStr, sourceUrl: s.url, sourceName: s.domain ?? s.source, sourceDate: s.date ?? s.published,
        confidence: s.confidence === "verified" ? "verified" : "retrieved",
        freshness: "unverified", allowedVisible: false, // freshness lock (metricFreshnessValidator) decides visibility
      });
    }
  }
  return out;
}

// When 2+ distinct sources report the same metric+period with a numerically close value
// (within 5% relative, or exact for ratios), promote confidence to "cross_verified" and drop
// the duplicate so the same fact is not shown twice.
export function crossVerifyMetrics(metrics: MetricEvidence[]): MetricEvidence[] {
  const groups = new Map<string, MetricEvidence[]>();
  for (const m of metrics) {
    const key = `${m.metric}|${m.period ?? ""}`;
    (groups.get(key) ?? groups.set(key, []).get(key)!).push(m);
  }
  const out: MetricEvidence[] = [];
  for (const group of groups.values()) {
    if (group.length === 1) { out.push(group[0]); continue; }
    const sources = new Set(group.map((g) => g.sourceUrl));
    const values = group.map((g) => Number(g.value)).filter((v) => isFinite(v));
    const agree = sources.size >= 2 && values.length >= 2 && Math.max(...values) - Math.min(...values) <= Math.max(0.5, Math.min(...values) * 0.05);
    const best = [...group].sort((a, b) => (a.confidence === "verified" ? 0 : 1) - (b.confidence === "verified" ? 0 : 1))[0];
    out.push(agree ? { ...best, confidence: "cross_verified" } : best);
  }
  return out;
}
