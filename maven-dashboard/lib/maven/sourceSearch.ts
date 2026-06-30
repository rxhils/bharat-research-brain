import type { SourceResult } from "./types";

// Provider-agnostic web search. Plug in any provider via env keys; returns [] gracefully
// if none configured (the context pack records this as a limitation - never fabricates).
type Provider = "tavily" | "serper" | "exa" | "brave" | null;

function pickProvider(): Provider {
  if (process.env.TAVILY_API_KEY) return "tavily";
  if (process.env.SERPER_API_KEY) return "serper";
  if (process.env.EXA_API_KEY) return "exa";
  if (process.env.BRAVE_API_KEY) return "brave";
  return null;
}

async function tavily(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.tavily.com/search", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: process.env.TAVILY_API_KEY, query: q, max_results: 4, search_depth: "basic" }),
    cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).map((x: any) => ({ title: x.title, url: x.url, snippet: x.content || "", source: hostOf(x.url) }));
}

async function serper(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://google.serper.dev/news", {
    method: "POST", headers: { "Content-Type": "application/json", "X-API-KEY": process.env.SERPER_API_KEY || "" },
    body: JSON.stringify({ q, gl: "in", num: 4 }), cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.news || j?.organic || []).slice(0, 4).map((x: any) => ({ title: x.title, url: x.link, snippet: x.snippet || "", source: x.source || hostOf(x.link), published: x.date }));
}

async function exa(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.exa.ai/search", {
    method: "POST", headers: { "Content-Type": "application/json", "x-api-key": process.env.EXA_API_KEY || "" },
    body: JSON.stringify({ query: q, numResults: 4, contents: { text: true } }), cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).map((x: any) => ({ title: x.title, url: x.url, snippet: (x.text || "").slice(0, 280), source: hostOf(x.url), published: x.publishedDate }));
}

async function brave(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.search.brave.com/res/v1/news/search?q=" + encodeURIComponent(q) + "&country=in&count=4", {
    headers: { "X-Subscription-Token": process.env.BRAVE_API_KEY || "", Accept: "application/json" }, cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).slice(0, 4).map((x: any) => ({ title: x.title, url: x.url, snippet: x.description || "", source: hostOf(x.url), published: x.age }));
}

function hostOf(u: string): string { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "source"; } }

export async function searchSources(queries: string[]): Promise<SourceResult[]> {
  const provider = pickProvider();
  if (!provider || !queries.length) return [];
  const run = provider === "tavily" ? tavily : provider === "serper" ? serper : provider === "exa" ? exa : brave;
  const settled = await Promise.allSettled(queries.slice(0, 3).map((q) => run(q)));
  const all = settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
  // dedupe by url
  const seen = new Set<string>();
  return all.filter((x) => x.url && !seen.has(x.url) && seen.add(x.url)).slice(0, 8);
}