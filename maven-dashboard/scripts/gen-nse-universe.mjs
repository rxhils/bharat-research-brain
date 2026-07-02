// Generates a committed snapshot of the NSE equity universe from NSE's *published, downloadable*
// master files (same permitted category as bhavcopies - NOT page scraping / no anti-bot bypass).
// Output: lib/maven/data/nse-universe.json  (loaded statically at runtime; refreshed in-memory when reachable)
// Run: node scripts/gen-nse-universe.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const EQUITY = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv";
const SYMCHG = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv";
const NAMECHG = "https://nsearchives.nseindia.com/content/equities/namechange.csv";

async function getText(url) {
  const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "text/csv,*/*" } });
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.text();
}

// tiny CSV splitter (no embedded commas in these NSE files)
function rows(txt) { return txt.trim().split(/\r?\n/).map((l) => l.split(",").map((c) => c.trim())); }

const out = { generatedAt: new Date().toISOString(), source: "NSE published securities files", securities: [] };

const eq = rows(await getText(EQUITY));
// header: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
for (const r of eq.slice(1)) {
  if (r.length < 7 || !r[0]) continue;
  out.securities.push({
    s: r[0], n: r[1], series: r[2] || "EQ", listed: r[3] || undefined, isin: r[6] || undefined,
    segment: "equity", status: "active",
  });
}

// best-effort: symbol changes -> oldSymbols; name changes -> oldNames
const bySymbol = new Map(out.securities.map((x) => [x.s, x]));
try {
  const sc = rows(await getText(SYMCHG)); // cols vary: [SM_NAME?, OLD, NEW, DATE] or [NEW,OLD,...]
  for (const r of sc.slice(1)) {
    // heuristic: find a current symbol in the row and any other token as an old symbol
    const cur = r.find((t) => bySymbol.has(t));
    if (!cur) continue;
    const old = r.find((t) => t && t !== cur && /^[A-Z0-9&-]{2,20}$/.test(t) && !bySymbol.has(t));
    if (old) { const sec = bySymbol.get(cur); (sec.oldSymbols ||= []).push(old); }
  }
  console.log("symbolchange applied");
} catch (e) { console.log("symbolchange skipped:", e.message); }
try {
  const nc = rows(await getText(NAMECHG));
  for (const r of nc.slice(1)) {
    const cur = r.find((t) => bySymbol.has(t));
    if (!cur) continue;
    const sec = bySymbol.get(cur);
    const names = r.filter((t) => /[a-z]/i.test(t) && t.length > 6 && t !== sec.n);
    if (names.length) (sec.oldNames ||= []).push(...names.slice(0, 2));
  }
  console.log("namechange applied");
} catch (e) { console.log("namechange skipped:", e.message); }

const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "lib", "maven", "data");
mkdirSync(dir, { recursive: true });
const path = join(dir, "nse-universe.json");
writeFileSync(path, JSON.stringify(out), "utf8");
console.log(`wrote ${out.securities.length} securities -> ${path}`);
