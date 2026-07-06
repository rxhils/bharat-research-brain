import type { SourceResult } from "./types";

// Real general-web search via Google's official Custom Search JSON API (Programmable Search).
// Unlike Google News RSS (news only), this returns diverse web pages - official sites, filings,
// reputable media, data pages - so Maven can pull Perplexity-style source coverage. It is an
// official Google API (not scraping, no anti-bot bypass), gated behind two env vars:
//   GOOGLE_CSE_KEY  - Custom Search API key (Google Cloud Console)
//   GOOGLE_CSE_CX   - Programmable Search Engine ID, configured to "search the entire web"
// Free tier is 100 queries/day; each query here is one API call. When unset or over quota we return
// [] (never a surfaced error) and the always-on Google News RSS layer still covers the request.

const ENDPOINT = "https://www.googleapis.com/customsearch/v1";

export function googleCustomSearchConfigured(): boolean {
  return !!(process.env.GOOGLE_CSE_KEY && process.env.GOOGLE_CSE_CX);
}

function hostOf(u: string): string {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; }
}

// Best-effort publish date from the CSE pagemap (present for many news/article results, absent
// otherwise). Never guessed - returns undefined when the source didn't supply one.
function dateFrom(item: any): string | undefined {
  const pm = item?.pagemap || {};
  const tags = pm.metatags?.[0] || {};
  return (
    tags["article:published_time"] ||
    tags["og:updated_time"] ||
    pm.newsarticle?.[0]?.datepublished ||
    pm.article?.[0]?.datepublished ||
    undefined
  );
}

export async function searchGoogleCustom(query: string, timeoutMs = 6000): Promise<SourceResult[]> {
  if (!query || !googleCustomSearchConfigured()) return [];
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const url =
      `${ENDPOINT}?key=${encodeURIComponent(process.env.GOOGLE_CSE_KEY as string)}` +
      `&cx=${encodeURIComponent(process.env.GOOGLE_CSE_CX as string)}` +
      `&q=${encodeURIComponent(query)}&gl=in&hl=en&num=10`;
    const r = await fetch(url, { headers: { Accept: "application/json" }, signal: ctrl.signal, cache: "no-store" });
    if (!r.ok) return []; // incl. 429 = daily quota exhausted; caller falls back to Google News RSS
    const j: any = await r.json();
    const items: any[] = Array.isArray(j?.items) ? j.items : [];
    return items
      .filter((it) => it && typeof it.link === "string")
      .map((it): SourceResult => ({
        title: String(it.title || hostOf(it.link)),
        url: String(it.link),
        snippet: String(it.snippet || "").replace(/\s+/g, " ").trim(),
        source: String(it.displayLink || hostOf(it.link)),
        published: dateFrom(it),
        provider: "google_cse",
      }));
  } catch {
    return []; // timeout/network/parse - never surfaced to the user
  } finally {
    clearTimeout(timer);
  }
}

// Run up to `limit` queries concurrently and flatten (dedupe happens in sourceSearch's ranker).
// `limit` should be kept modest by the caller to respect the 100/day free quota.
export async function searchGoogleCustomMany(queries: string[], limit = 4): Promise<SourceResult[]> {
  if (!googleCustomSearchConfigured()) return [];
  const qs = queries.filter(Boolean).slice(0, limit);
  if (!qs.length) return [];
  const settled = await Promise.allSettled(qs.map((q) => searchGoogleCustom(q)));
  return settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
}
