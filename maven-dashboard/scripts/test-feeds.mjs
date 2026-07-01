// Maven Data Feeds v1 acceptance test. Hits local /api/ask with 7 queries and reports
// structure + a leakage scan. Run: `node scripts/test-feeds.mjs` (set MAVEN_URL to override).
const BASE = process.env.MAVEN_URL || "http://localhost:3000";

const QUERIES = [
  "Summarize today's Indian market",
  "Why is Bank Nifty moving today?",
  "How do FII flows affect Indian markets?",
  "What happens when 10Y G-Sec yields fall?",
  "How does crude oil affect Indian markets?",
  "Compare HDFC Bank and ICICI Bank",
  "Why is Reliance moving today?",
];

// Never let provider/impl wording reach the user. Word-boundary matched to avoid false
// positives (e.g. "env" must not match "government"/"environment").
const FORBIDDEN = [
  "deepseek", "openai", "anthropic", "llm", "api key", "backend", "provider",
  "tavily error", "yahoo error", "env", "fallback", "mock", "preview", "demo", "server-side key",
];

function leakScan(obj) {
  const s = JSON.stringify(obj);
  const hits = [];
  for (const t of FORBIDDEN) {
    const re = new RegExp("\\b" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i");
    if (re.test(s)) hits.push(t);
  }
  return hits;
}

async function ask(query) {
  const r = await fetch(BASE + "/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return r.json();
}

const rows = [];
let anyLeak = false;

for (const q of QUERIES) {
  try {
    const a = await ask(q);
    const text = JSON.stringify(a).toLowerCase();
    const type = a.type ?? a.answerType ?? "";
    const keyData = (a.keyData || []).length;
    const charts = (a.charts || []).length;
    const sources = (a.sources || []).length;
    const limitations = a.limitations || [];
    const hasFiiDii = /\bfii\b|\bdii\b/.test(text);
    const hasGSec = /g-?sec|10y|government bond|benchmark yield/.test(text);
    const hasSnapshot = /market cap|p\/e|p\/b|\broe\b|valuation|dividend yield/.test(text);
    const leak = leakScan(a);
    if (leak.length) anyLeak = true;
    rows.push({ q, type, keyData, charts, sources, limits: limitations.length, hasFiiDii, hasGSec, hasSnapshot, leak: leak.join(",") });

    console.log(`\n== ${q}`);
    console.log(`   type=${type} | ${a.headline}`);
    console.log(`   keyData=${keyData}  charts=${charts}  sources=${sources}  limitations=${limitations.length}`);
    console.log(`   FII/DII=${hasFiiDii}  G-Sec=${hasGSec}  snapshot=${hasSnapshot}`);
    if (limitations.length) console.log(`   limitations: ${limitations.join(" | ")}`);
    console.log(`   leak=[${leak.join(",")}]`);
  } catch (e) {
    console.log(`\n== ${q}\n   ERROR ${e.message}`);
    rows.push({ q, type: "ERR", leak: "" });
  }
}

console.log("\n=== SUMMARY ===");
console.log("query".padEnd(38) + "type".padEnd(24) + "kd ch src lim  FII  GSec  snap  leak");
for (const r of rows) {
  console.log(
    String(r.q).slice(0, 36).padEnd(38) +
    String(r.type).padEnd(24) +
    String(r.keyData ?? "-").padEnd(3) + String(r.charts ?? "-").padEnd(3) + String(r.sources ?? "-").padEnd(4) +
    String(r.limits ?? "-").padEnd(5) + String(r.hasFiiDii ?? "-").padEnd(5) + String(r.hasGSec ?? "-").padEnd(6) +
    String(r.hasSnapshot ?? "-").padEnd(6) + (r.leak ? "LEAK:" + r.leak : "clean"),
  );
}
console.log(`\nLeakage scan: ${anyLeak ? "FAIL" : "CLEAN"}`);
