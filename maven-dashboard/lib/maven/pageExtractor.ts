import type { ExtractedPage } from "./types";

// Lightweight, best-effort page extraction. Fetches HTML once with a short timeout and a
// browser-like UA, then strips scripts/styles/nav to recover readable text. It intentionally
// does NOT render JS, solve captchas, or defeat paywalls/login/anti-bot walls - if a page is
// gated we return whatever partial text is visible (or "failed"), never an error to the user.

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const MAX_TEXT = 2500; // chars kept per page (task: cap 1,500-2,500)

function domainOf(u: string): string {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "source"; }
}

function stripTags(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<(nav|header|footer|aside|form)[\s\S]*?<\/\1>/gi, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&").replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'").replace(/&lt;/gi, "<").replace(/&gt;/gi, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function firstMatch(html: string, re: RegExp): string | undefined {
  const m = html.match(re);
  return m ? m[1].trim() : undefined;
}

function extractTitle(html: string, fallback: string): string {
  return (
    firstMatch(html, /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i) ||
    firstMatch(html, /<title[^>]*>([\s\S]*?)<\/title>/i) ||
    fallback
  ).slice(0, 200);
}

function extractDate(html: string): string | undefined {
  return (
    firstMatch(html, /<meta[^>]+property=["']article:published_time["'][^>]+content=["']([^"']+)["']/i) ||
    firstMatch(html, /<meta[^>]+itemprop=["']datePublished["'][^>]+content=["']([^"']+)["']/i) ||
    firstMatch(html, /<time[^>]+datetime=["']([^"']+)["']/i)
  );
}

function extractCanonical(html: string, url: string): string {
  return firstMatch(html, /<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i) || url;
}

// Prefer <article>/main content when present; otherwise fall back to the whole body.
function mainText(html: string): string {
  const article = firstMatch(html, /<article[^>]*>([\s\S]*?)<\/article>/i);
  const body = article || firstMatch(html, /<body[^>]*>([\s\S]*?)<\/body>/i) || html;
  return stripTags(body).slice(0, MAX_TEXT);
}

export async function extractPage(url: string, timeoutMs = 4500): Promise<ExtractedPage> {
  const domain = domainOf(url);
  const base: ExtractedPage = { title: domain, url, domain, text: "", extractionStatus: "failed" };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      headers: { "User-Agent": UA, Accept: "text/html,application/xhtml+xml", "Accept-Language": "en-IN,en;q=0.9" },
      signal: ctrl.signal, cache: "no-store", redirect: "follow",
    });
    if (!r.ok) return base; // paywall/anti-bot/404 -> treat as failed, keep the search snippet upstream
    const ctype = r.headers.get("content-type") || "";
    if (!/text\/html|application\/xhtml/i.test(ctype)) return base;
    const html = (await r.text()).slice(0, 500_000);
    const text = mainText(html);
    return {
      title: extractTitle(html, domain),
      url: extractCanonical(html, url),
      domain,
      text,
      date: extractDate(html),
      extractionStatus: text.length >= 400 ? "success" : text.length > 0 ? "partial" : "failed",
    };
  } catch {
    return base; // timeout/network/abort - never surfaced to the user
  } finally {
    clearTimeout(timer);
  }
}
