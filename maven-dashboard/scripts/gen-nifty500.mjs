// Regenerate lib/maven/data/nifty500.json from NSE's published, downloadable Nifty 500
// constituents CSV (nsearchives - the same permitted host gen-nse-universe.mjs uses; this is a
// downloadable index file, not website scraping). Run manually when constituents change:
//   node scripts/gen-nifty500.mjs
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

const r = await fetch(URL, { headers: { "User-Agent": UA, Accept: "text/csv,*/*" } });
if (!r.ok) { console.error(`fetch failed: ${r.status}`); process.exit(1); }
const lines = (await r.text()).trim().split(/\r?\n/);
// header: Company Name,Industry,Symbol,Series,ISIN Code
const constituents = [];
for (const line of lines.slice(1)) {
  const c = line.split(",").map((x) => x.trim());
  if (c.length < 5 || !c[2]) continue;
  if ((c[3] || "EQ").toUpperCase() !== "EQ") continue; // normal equity series only
  constituents.push({ s: c[2], n: c[0], industry: c[1] || undefined });
}
if (constituents.length < 400) { console.error(`suspiciously few rows (${constituents.length}) - aborting, not overwriting snapshot`); process.exit(1); }

const out = { generatedAt: new Date().toISOString(), source: URL, constituents };
const dest = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "lib", "maven", "data", "nifty500.json");
writeFileSync(dest, JSON.stringify(out, null, 1), "utf8");
console.log(`wrote ${constituents.length} Nifty 500 constituents -> ${dest}`);
