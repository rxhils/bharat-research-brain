import type { SourceResult } from "./types";

// Free news search via Google News' public RSS search-syndication endpoint
// (news.google.com/rss/search). This is Google's own documented RSS feed, not HTML scraping:
// no API key, no login, no anti-bot bypass. Always available (no config/env var needed), so it
// runs unconditionally alongside SearXNG in sourceSearch.ts - unlike SearXNG or the paid
// providers, it never depends on an env var or local service being reachable. Only returns
// third-party news; sourceQualityScorer.ts's official/regulator checks never match
// news.google.com or a real publisher domain recovered below, so this can never produce a fake
// official-source label.

const ENDPOINT = "https://news.google.com/rss/search";

function decodeEntities(s: string): string {
  return s
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'").replace(/&amp;/g, "&");
}

function stripTags(s: string): string {
  return decodeEntities(s.replace(/<[^>]*>/g, " ")).replace(/\s+/g, " ").trim();
}

function hostOf(u: string): string {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; }
}

// Generic query words that carry no company-identifying signal - excluded so relevance checks
// key on the actual entity (company name, ticker) rather than boilerplate shared by every query.
const STOPWORDS = new Set([
  "india", "indian", "stock", "stocks", "news", "today", "why", "moving", "latest", "quarterly",
  "results", "result", "investor", "relations", "presentation", "share", "shares", "price", "analysis",
  "earnings", "credit", "rating", "outlook", "peer", "comparison", "sector", "management", "commentary",
  "concall", "market", "capex", "update", "shareholding", "pattern", "nse", "bse", "annual", "report",
  "corporate", "announcement", "the", "and", "for", "of", "in", "on", "a", "to", "moneycontrol", "businessline", "mint",
]);

function significantTokens(query: string): string[] {
  return (query.toLowerCase().match(/[a-z0-9&]+/g) || []).filter((w) => w.length >= 3 && !STOPWORDS.has(w));
}

// Google News' own relevance ranking is loose enough that a generic query (e.g. "peer comparison
// sector India") can surface an article about an unrelated company. Keep only items that share at
// least one company-identifying token with the query that produced them; skip the check entirely
// if the query has no such token (nothing meaningful to filter on).
function isRelevant(query: string, text: string): boolean {
  const toks = significantTokens(query);
  if (!toks.length) return true;
  const lower = text.toLowerCase();
  return toks.some((t) => lower.includes(t));
}

type RawItem = { title: string; link: string; pubDate?: string; sourceName?: string; sourceUrl?: string; description?: string };

// Hand-rolled RSS parsing (no xml dependency in this project) - the feed shape is stable and
// simple (flat <item> list), so a bounded regex scan is sufficient and avoids adding a new
// package for one consumer.
function parseItems(xml: string): RawItem[] {
  const items: RawItem[] = [];
  const itemRe = /<item>([\s\S]*?)<\/item>/g;
  let m: RegExpExecArray | null;
  while ((m = itemRe.exec(xml))) {
    const block = m[1];
    const title = decodeEntities((block.match(/<title>([\s\S]*?)<\/title>/) || ["", ""])[1]).trim();
    const link = decodeEntities((block.match(/<link>([\s\S]*?)<\/link>/) || ["", ""])[1]).trim();
    const pubDate = (block.match(/<pubDate>([\s\S]*?)<\/pubDate>/) || ["", undefined])[1];
    const srcMatch = block.match(/<source url="([^"]*)"[^>]*>([\s\S]*?)<\/source>/);
    const sourceUrl = srcMatch ? decodeEntities(srcMatch[1]) : undefined;
    const sourceName = srcMatch ? decodeEntities(srcMatch[2]).trim() : undefined;
    const descRaw = (block.match(/<description>([\s\S]*?)<\/description>/) || ["", ""])[1];
    const description = stripTags(descRaw);
    if (title && link) items.push({ title, link, pubDate, sourceName, sourceUrl, description });
  }
  return items;
}

export async function searchGoogleNews(query: string, timeoutMs = 6000): Promise<SourceResult[]> {
  if (!query) return [];
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const url = `${ENDPOINT}?q=${encodeURIComponent(query)}&hl=en-IN&gl=IN&ceid=IN:en`;
    const r = await fetch(url, {
      headers: { Accept: "application/rss+xml, application/xml, text/xml" },
      signal: ctrl.signal, cache: "no-store",
    });
    if (!r.ok) return [];
    const xml = await r.text();
    const items = parseItems(xml).slice(0, 8);
    return items.map((it): SourceResult => {
      // Google's <source url> attribute is the publisher's real domain (e.g. economictimes.indiatimes.com),
      // distinct from the news.google.com redirect link in <link> - used as a classification hint so
      // reputable publishers still rank as "media" tier instead of falling through to "generic".
      const domainHint = it.sourceUrl ? hostOf(it.sourceUrl) : undefined;
      const suffix = it.sourceName ? ` - ${it.sourceName}` : "";
      const title = suffix && it.title.endsWith(suffix) ? it.title.slice(0, -suffix.length) : it.title;
      return {
        title, url: it.link, snippet: it.description || title,
        source: it.sourceName || domainHint || "Google News",
        published: it.pubDate, provider: "google_news_rss",
        domainHint,
      };
    });
  } catch {
    return []; // unreachable/timeout -> clean empty, caller records a soft limitation
  } finally {
    clearTimeout(timer);
  }
}

// Run a bounded set of queries concurrently and flatten (dedupe happens in sourceSearch's ranker).
export async function searchGoogleNewsMany(queries: string[], perQueryLimit = 3): Promise<SourceResult[]> {
  const qs = queries.filter(Boolean).slice(0, perQueryLimit);
  if (!qs.length) return [];
  const settled = await Promise.allSettled(qs.map((q) => searchGoogleNews(q)));
  return settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
}
