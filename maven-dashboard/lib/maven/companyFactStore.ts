import type { CompanyFact } from "./types";

// In-memory TTL fact cache (v1) - same pattern as dataTools.ts's cached() helper, scoped to
// company financial facts so repeat questions in a short window skip re-search/re-extraction.
// Serverless note: this only helps within a warm function instance; a cold start starts empty,
// which is safe (facts are re-derived from sources, never invented) but not a durable cache.

const TTL_MS: Record<string, number> = {
  price: 2 * 60_000, dailyMove: 2 * 60_000, volume: 2 * 60_000,
  revenue: 18 * 3600_000, revenueGrowth: 18 * 3600_000, ebitda: 18 * 3600_000, pat: 18 * 3600_000, margin: 18 * 3600_000,
  marketShare: 18 * 3600_000, capex: 18 * 3600_000, orderBook: 18 * 3600_000, guidance: 18 * 3600_000,
  shareholding: 18 * 3600_000, pledge: 18 * 3600_000,
  pe: 12 * 3600_000, pb: 12 * 3600_000, roe: 12 * 3600_000, roce: 12 * 3600_000, debtToEquity: 12 * 3600_000,
  marketSize: 20 * 24 * 3600_000, cagr: 20 * 24 * 3600_000, other: 30 * 60_000,
};
function ttlFor(metric: string): number { return TTL_MS[metric] ?? 30 * 60_000; }

const store = new Map<string, CompanyFact[]>();

export function getCachedCompanyFacts(symbol: string): CompanyFact[] {
  return store.get(symbol.toUpperCase()) ?? [];
}

export function getFreshCompanyFacts(symbol: string, maxAgeMs?: number): CompanyFact[] {
  const now = Date.now();
  return getCachedCompanyFacts(symbol).filter((f) => now - f.lastCheckedAt < (maxAgeMs ?? ttlFor(f.metric)));
}

export function saveCompanyFacts(symbol: string, facts: CompanyFact[]): void {
  const key = symbol.toUpperCase();
  const existing = store.get(key) ?? [];
  store.set(key, mergeFacts(existing, facts));
}

// Newest sourceDate (or lastCheckedAt) wins per metric+period; cross-source agreement is handled
// upstream by companyMetricExtractor's crossVerifyMetrics before facts reach the store.
export function mergeFacts(existing: CompanyFact[], incoming: CompanyFact[]): CompanyFact[] {
  const byKey = new Map<string, CompanyFact>();
  for (const f of [...existing, ...incoming]) {
    const key = `${f.metric}|${f.period ?? ""}`;
    const prior = byKey.get(key);
    if (!prior || f.lastCheckedAt >= prior.lastCheckedAt) byKey.set(key, f);
  }
  return [...byKey.values()];
}
