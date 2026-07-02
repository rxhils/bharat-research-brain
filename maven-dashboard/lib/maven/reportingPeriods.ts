// Indian fiscal calendar utilities for the freshness lock.
// FY26 = Apr 2025 - Mar 2026. Quarters: Q1 Apr-Jun, Q2 Jul-Sep, Q3 Oct-Dec, Q4 Jan-Mar.
// "fy" is the 2-digit fiscal year number (FY26 -> 26).

export type FiscalPeriod = { fy: number; quarter?: 1 | 2 | 3 | 4 };

export function getCurrentIndianFiscalYear(date = new Date()): number {
  const y = date.getFullYear() - 2000;
  return date.getMonth() >= 3 ? y + 1 : y; // Apr onwards belongs to next FY
}

export function getLatestCompletedIndianFiscalYear(date = new Date()): number {
  return getCurrentIndianFiscalYear(date) - 1;
}

// The most recent quarter whose results should already be reported (~45-day filing lag).
export function getExpectedLatestQuarter(date = new Date()): FiscalPeriod {
  const lagged = new Date(date.getTime() - 45 * 24 * 60 * 60 * 1000);
  const m = lagged.getMonth(); // 0=Jan
  const fy = getCurrentIndianFiscalYear(lagged);
  // month -> quarter just ENDED before `lagged`
  if (m >= 3 && m < 6) return { fy: fy - 1, quarter: 4 };   // Apr-Jun: last full quarter is Q4 of prior FY
  if (m >= 6 && m < 9) return { fy, quarter: 1 };            // Jul-Sep: Q1 ended
  if (m >= 9) return { fy, quarter: 2 };                     // Oct-Dec: Q2 ended
  return { fy, quarter: 3 };                                 // Jan-Mar: Q3 ended
}

const FY_RE = /\bQ([1-4])\s*[-\s]?FY\s*[']?(\d{2,4})\b|\bFY\s*[']?(\d{2,4})\b/gi;

function normFy(raw: string): number {
  const n = parseInt(raw, 10);
  return n >= 2000 ? n - 2000 : n;
}

export function parseFiscalPeriod(text: string): FiscalPeriod | null {
  FY_RE.lastIndex = 0;
  const m = FY_RE.exec(text || "");
  if (!m) return null;
  if (m[1] && m[2]) return { fy: normFy(m[2]), quarter: parseInt(m[1], 10) as FiscalPeriod["quarter"] };
  if (m[3]) return { fy: normFy(m[3]) };
  return null;
}

export function parseAllFiscalTokens(text: string): FiscalPeriod[] {
  const out: FiscalPeriod[] = [];
  FY_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = FY_RE.exec(text || "")) !== null) {
    if (m[1] && m[2]) out.push({ fy: normFy(m[2]), quarter: parseInt(m[1], 10) as FiscalPeriod["quarter"] });
    else if (m[3]) out.push({ fy: normFy(m[3]) });
  }
  return out;
}

export function formatFiscalPeriod(p: FiscalPeriod): string {
  return p.quarter ? `Q${p.quarter}FY${p.fy}` : `FY${p.fy}`;
}

// >0 if a is later than b
export function compareFiscalPeriods(a: FiscalPeriod, b: FiscalPeriod): number {
  if (a.fy !== b.fy) return a.fy - b.fy;
  return (a.quarter ?? 0) - (b.quarter ?? 0);
}

// A period is stale for a "current" question when it predates the latest completed FY.
export function isPeriodStale(period: FiscalPeriod, date = new Date()): boolean {
  return period.fy < getLatestCompletedIndianFiscalYear(date);
}

// True only when the user explicitly asks for an old period / history.
export function detectHistoricalRequest(query: string, date = new Date()): boolean {
  const q = (query || "").toLowerCase();
  if (/\bhistorical\b|\b(last|past)\s+\d+\s+(years?|quarters?)\b|\bold results?\b|\bprevious annual report\b|\bsince\s+20\d\d\b|\btrend\b.*\byears?\b|\bin\s+20(1\d|2[0-4])\b/.test(q)) return true;
  const latestCompleted = getLatestCompletedIndianFiscalYear(date);
  return parseAllFiscalTokens(q).some((p) => p.fy < latestCompleted);
}
