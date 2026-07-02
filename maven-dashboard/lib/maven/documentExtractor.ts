import type { ExtractedPage } from "./types";
import { extractPage } from "./pageExtractor";
import { parseFiscalPeriod, formatFiscalPeriod } from "./reportingPeriods";

// Extends pageExtractor.ts (HTML) with PDF support for result documents, investor presentations
// and annual reports. No native/npm PDF dependency - a dependency-free best-effort text pull that
// works on uncompressed PDF text streams and cleanly reports "failed" on compressed/complex PDFs
// (common for scanned/image-based or FlateDecode-only reports) rather than inventing content.
// Never bypasses paywalls/logins/anti-bot systems; a blocked fetch is just "failed".

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const MAX_TEXT = 4000; // PDFs (results/presentations) get a larger cap than HTML pages

export function isPdfUrl(url: string): boolean {
  return /\.pdf($|\?)/i.test(url);
}

function domainOf(u: string): string { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "source"; } }

// Extract text from PDF "Tj"/"TJ" text-showing operators inside uncompressed content streams.
// This intentionally does NOT decompress FlateDecode streams - if the document is compressed
// (most modern PDFs), this yields little/no text and extraction is honestly reported as failed.
function pdfBytesToText(buf: Buffer): string {
  const raw = buf.toString("latin1");
  const chunks: string[] = [];
  // (text) Tj  and  [(text) ... ] TJ
  const tj = /\(((?:[^()\\]|\\.)*)\)\s*Tj/g;
  const tjArray = /\[((?:[^\[\]]|\\.)*)\]\s*TJ/g;
  let m: RegExpExecArray | null;
  while ((m = tj.exec(raw)) !== null) chunks.push(unescapePdfString(m[1]));
  while ((m = tjArray.exec(raw)) !== null) {
    const inner = m[1];
    const parts = inner.match(/\(((?:[^()\\]|\\.)*)\)/g) || [];
    chunks.push(parts.map((p) => unescapePdfString(p.slice(1, -1))).join(""));
  }
  return chunks.join(" ").replace(/\s+/g, " ").trim();
}

function unescapePdfString(s: string): string {
  return s.replace(/\\(\d{3})/g, (_, o) => String.fromCharCode(parseInt(o, 8)))
    .replace(/\\n/g, " ").replace(/\\r/g, " ").replace(/\\\(/g, "(").replace(/\\\)/g, ")").replace(/\\\\/g, "\\");
}

export async function extractPdfText(url: string, timeoutMs = 6000): Promise<ExtractedPage> {
  const domain = domainOf(url);
  const base: ExtractedPage = { title: domain, url, domain, text: "", extractionStatus: "failed" };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/pdf,*/*" }, signal: ctrl.signal, cache: "no-store" });
    if (!r.ok) return base;
    const ctype = r.headers.get("content-type") || "";
    if (!/pdf/i.test(ctype) && !isPdfUrl(url)) return base;
    const ab = await r.arrayBuffer();
    if (ab.byteLength > 15_000_000) return base; // don't hold huge annual-report PDFs in memory
    const buf = Buffer.from(ab);
    const text = pdfBytesToText(buf).slice(0, MAX_TEXT);
    return { title: domain, url, domain, text, extractionStatus: text.length >= 200 ? "success" : text.length > 0 ? "partial" : "failed" };
  } catch {
    return base;
  } finally {
    clearTimeout(timer);
  }
}

export async function extractHtmlText(url: string): Promise<ExtractedPage> {
  return extractPage(url); // reuse the existing HTML extractor - no duplicate logic
}

export async function extractDocument(url: string): Promise<ExtractedPage> {
  return isPdfUrl(url) ? extractPdfText(url) : extractHtmlText(url);
}

export function detectDocumentDate(text: string, url: string): string | undefined {
  const t = text || "";
  const iso = t.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
  if (iso) return iso[1];
  const dmy = t.match(/\b(\d{1,2})[\s-](jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,-]+(20\d{2})\b/i);
  if (dmy) return `${dmy[3]}-${dmy[2].slice(0, 3)}-${dmy[1].padStart(2, "0")}`; // best-effort, human readable
  const urlDate = url.match(/\/(20\d{2})[-/](\d{2})[-/](\d{2})\//);
  if (urlDate) return `${urlDate[1]}-${urlDate[2]}-${urlDate[3]}`;
  return undefined;
}

export function detectReportingPeriod(text: string): string | undefined {
  const p = parseFiscalPeriod(text || "");
  return p ? formatFiscalPeriod(p) : undefined;
}

// Best-effort: pull simple whitespace/pipe-delimited numeric rows (common in extracted result
// tables). Returns [] rather than guessing structure when nothing table-like is found.
export function extractTablesIfPossible(text: string): string[][] {
  const lines = (text || "").split(/\n|(?<=\d)\s{2,}(?=[A-Za-z])/);
  const rows: string[][] = [];
  for (const line of lines) {
    const cells = line.split(/\s{2,}|\t|\|/).map((c) => c.trim()).filter(Boolean);
    if (cells.length >= 2 && cells.some((c) => /\d/.test(c))) rows.push(cells);
  }
  return rows.slice(0, 40);
}
