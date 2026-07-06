import type { SourceResult } from "./types";

// Real Google SERP results via Serplify (https://serplify.io) - a paid SERP API returning
// AI-ready JSON. Gives Maven Perplexity-style general-web coverage (official sites, filings,
// reputable media). Gated behind SERPLIFY_API_KEY; when unset or the call fails we return []
// (never a surfaced error) and the always-on Google News RSS layer still covers the request.
//
// Contract (per docs.serplify.io): POST https://api.serplify.io/v1/serp/search
//   Authorization: Bearer <key>;  body { keyword, location:{code}, language:{code}, device, format }
//   organic results at data.items[]. Response-path and item-field mapping below are defensive
//   (tolerant of the exact field names) so a minor contract difference degrades to fewer/no
//   results rather than a crash. India geo-target code = 2356.

const ENDPOINT = "https://api.serplify.io/v1/serp/search";
const INDIA_GEO = 2356;

export function serplifyConfigured(): boolean {
  return !!process.env.SERPLIFY_API_KEY;
}

function hostOf(u: string): string {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; }
}

// Pull the organic-results array regardless of the exact response wrapper the API uses.
function itemsOf(j: any): any[] {
  const cands = [j?.data?.items, j?.data?.organic, j?.data?.results, j?.organic_results, j?.results, j?.items];
  for (const c of cands) if (Array.isArray(c)) return c;
  return [];
}

function mapItem(it: any): SourceResult | null {
  const url = it?.link || it?.url || it?.displayed_link || it?.displayedLink;
  if (typeof url !== "string" || !url) return null;
  return {
    title: String(it.title || it.name || hostOf(url)),
    url,
    snippet: String(it.snippet || it.description || it.text || "").replace(/\s+/g, " ").trim(),
    source: String(it.source || it.domain || it.displayed_link || hostOf(url)),
    published: it.date || it.published_date || it.datePublished || undefined,
    provider: "serplify",
  };
}

export async function searchSerplify(query: string, timeoutMs = 12000): Promise<SourceResult[]> {
  if (!query || !serplifyConfigured()) return [];
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(ENDPOINT, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.SERPLIFY_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        keyword: query,
        location: { code: INDIA_GEO },
        language: { code: "en" },
        device: "desktop",
        format: "advanced",
      }),
      signal: ctrl.signal,
      cache: "no-store",
    });
    if (!r.ok) return []; // incl. 401/402/429 (auth/quota) - caller falls back to Google News RSS
    const j: any = await r.json();
    return itemsOf(j).map(mapItem).filter((x): x is SourceResult => x !== null);
  } catch {
    return []; // timeout/network/parse - never surfaced to the user
  } finally {
    clearTimeout(timer);
  }
}

// Run up to `limit` queries concurrently and flatten (dedupe happens in sourceSearch's ranker).
export async function searchSerplifyMany(queries: string[], limit = 4): Promise<SourceResult[]> {
  if (!serplifyConfigured()) return [];
  const qs = queries.filter(Boolean).slice(0, limit);
  if (!qs.length) return [];
  const settled = await Promise.allSettled(qs.map((q) => searchSerplify(q)));
  return settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
}
