import type { MavenAnswer } from "./types";
import { detectHistoricalRequest, getLatestCompletedIndianFiscalYear, parseAllFiscalTokens, formatFiscalPeriod } from "./reportingPeriods";

// Visible-text freshness lock for stock/company answers. Runs AFTER generation (covers both the
// model path and deterministic synthesis) and scrubs whole sentences that state:
//  - a stale fiscal-period metric (FY older than latest completed) not present in source evidence
//  - an approximate company metric (~20%, 10-12%, "roughly X") not present in source evidence
// Sentences whose figures DO appear in the retrieved source text are kept - they are evidence-
// backed - and stale-but-sourced periods are labeled via a limitation instead of being deleted.
// Rule: no source + no period = no metric; old period + current question = blocked.

const APPROX_RE = /(~\s?\d[\d.,]*\s*%?|\b(approx(?:imately)?|roughly|around|estimated)\s+[₹$]?\d[\d.,]*|\b\d{1,3}\s*[–—-]\s*\d{1,3}\s*%)/gi;
// Approx figures only matter when the sentence is about a company metric, not e.g. index levels.
const METRIC_WORDS = /\b(revenue|margin|market share|marketshare|capex|profit|pat|ebitda|order book|guidance|growth|cagr|volume share|units|shareholding|pledge|debt|roe|roce|p\/e|p\/b|valuation)\b/i;

const REMOVED_NOTE = "Some figures were removed because they were outdated or not backed by a dated source; Maven only shows period-labeled, source-backed metrics.";

function splitSentences(text: string): string[] {
  return (text || "").split(/(?<=[.!?])\s+/);
}

function tokensIn(text: string): Set<string> {
  return new Set(parseAllFiscalTokens(text).map(formatFiscalPeriod));
}

export function sanitizeStaleMetrics(a: MavenAnswer, query: string, sourceText: string, date = new Date()): { fixed: MavenAnswer; removedCount: number; staleSourcedCount: number } {
  if (detectHistoricalRequest(query, date)) return { fixed: a, removedCount: 0, staleSourcedCount: 0 };

  const latestCompleted = getLatestCompletedIndianFiscalYear(date);
  const allowedTokens = tokensIn(sourceText);
  const srcLower = (sourceText || "").toLowerCase();
  let removedCount = 0;
  let staleSourcedCount = 0;

  const cleanText = (text: string): string => {
    const kept = splitSentences(text).filter((sentence) => {
      // stale fiscal tokens (e.g. FY24 when latest completed is FY26)
      for (const p of parseAllFiscalTokens(sentence)) {
        if (p.fy < latestCompleted) {
          if (allowedTokens.has(formatFiscalPeriod(p))) { staleSourcedCount++; continue; } // sourced -> keep, labeled below
          removedCount++; return false;
        }
      }
      // unsourced approximate company metrics
      if (METRIC_WORDS.test(sentence)) {
        APPROX_RE.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = APPROX_RE.exec(sentence)) !== null) {
          const frag = m[0].replace(/\s+/g, " ").trim().toLowerCase();
          if (!srcLower.includes(frag.replace(/^~\s?/, "")) && !srcLower.includes(frag)) { removedCount++; return false; }
        }
      }
      return true;
    });
    return kept.join(" ").trim();
  };

  const fixed: MavenAnswer = {
    ...a,
    headline: cleanText(a.headline) || a.headline.replace(APPROX_RE, "").trim() || "Latest company view",
    summary: cleanText(a.summary),
    blocks: a.blocks
      .map((b) => ({ ...b, body: cleanText(b.body) }))
      .filter((b) => b.body.length > 0 || b.type === "TAKEAWAY"),
  };

  const limitations = [...(a.limitations ?? [])];
  if (removedCount > 0 && !limitations.includes(REMOVED_NOTE)) limitations.push(REMOVED_NOTE);
  if (staleSourcedCount > 0) limitations.push("Some period-labeled figures come from the latest available sources and may predate the current fiscal year; they are shown as latest available, not current.");
  if (limitations.length) fixed.limitations = limitations;

  return { fixed, removedCount, staleSourcedCount };
}
