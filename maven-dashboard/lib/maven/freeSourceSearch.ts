import type { SourceResult } from "./types";

// Free, self-hosted web search via a SearXNG instance (JSON API). No paid key required.
// Configure SEARXNG_URL (e.g. http://localhost:8080). If it is unset in production or the
// instance is unreachable, we return [] and let the caller fall back to a paid provider -
// we never surface a scraper/provider error to the user.

function base(): string {
  return process.env.SEARXNG_URL || (process.env.NODE_ENV !== "production" ? "http://localhost:8080" : "");
}

export function searxngConfigured(): boolean {
  return !!base();
}

function hostOf(u: string): string {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "source"; }
}

export async function searchSearxng(query: string, timeoutMs = 5000): Promise<SourceResult[]> {
  const b = base();
  if (!b || !query) return [];
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const url = `${b.replace(/\/$/, "")}/search?q=${encodeURIComponent(query)}&format=json&pageno=1&safesearch=1&language=en-IN`;
    const r = await fetch(url, {
      headers: { Accept: "application/json" }, signal: ctrl.signal, cache: "no-store",
    });
    if (!r.ok) return [];
    const j: any = await r.json();
    const rows: any[] = Array.isArray(j?.results) ? j.results : [];
    return rows
      .filter((x) => x && typeof x.url === "string")
      .slice(0, 10)
      .map((x): SourceResult => ({
        title: String(x.title || hostOf(x.url)),
        url: String(x.url),
        snippet: String(x.content || x.snippet || "").slice(0, 400),
        source: hostOf(x.url),
        provider: "searxng",
        confidence: "retrieved",
        freshness: "latest_available",
        domain: hostOf(x.url),
        date: x.publishedDate || undefined,
      }));
  } catch {
    return []; // unreachable/timeout -> clean empty, caller records a soft limitation
  } finally {
    clearTimeout(timer);
  }
}

// Run several queries concurrently against SearXNG and flatten (dedupe happens in the ranker).
export async function searchSearxngMany(queries: string[]): Promise<SourceResult[]> {
  if (!searxngConfigured() || !queries.length) return [];
  const settled = await Promise.allSettled(queries.map((q) => searchSearxng(q)));
  return settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
}
