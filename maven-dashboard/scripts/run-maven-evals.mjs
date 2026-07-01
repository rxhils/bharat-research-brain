import { writeFileSync } from "fs";
import { CASES } from "./evals/maven-eval-cases.mjs";
import { scoreCase } from "./evals/eval-scorer.mjs";

const BASE = process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask";

async function ask(query) {
  const t0 = Date.now();
  const r = await fetch(BASE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
  return { j: await r.json(), ms: Date.now() - t0 };
}

console.log(`Maven evals -> ${BASE}  (${CASES.length} cases)\n`);
const results = [];
for (const c of CASES) {
  try { const { j, ms } = await ask(c.query); results.push({ id: c.id, category: c.category, query: c.query, headline: j.headline, ...scoreCase(c, j, ms) }); }
  catch (e) { results.push({ id: c.id, category: c.category, query: c.query, pass: false, score: 0, reasons: ["ERROR " + e.message], leak: [], refused: false, latencyMs: 0 }); }
}

const passed = results.filter((r) => r.pass).length;
const avg = Math.round(results.reduce((a, r) => a + (r.score || 0), 0) / results.length);
const avgLat = Math.round(results.reduce((a, r) => a + (r.latencyMs || 0), 0) / results.length);
const byCat = {};
for (const r of results) { (byCat[r.category] ??= { p: 0, n: 0 }); byCat[r.category].n++; if (r.pass) byCat[r.category].p++; }
const leakFails = results.filter((r) => r.leak && r.leak.length);
const refusalFails = results.filter((r) => { const c = CASES.find((x) => x.id === r.id); return c.mustRefuse && !r.refused; });

console.log("ID   ACTUAL TYPE               P   SC  REASONS");
for (const r of results) console.log(`${r.id.padEnd(4)} ${String(r.type || "-").padEnd(24)} ${r.pass ? "OK" : "XX"}  ${String(r.score).padStart(3)}  ${(r.reasons || []).join("; ")}`);

console.log(`\nTOTAL ${results.length}   passed ${passed}   failed ${results.length - passed}   avgScore ${avg}   avgLatency ${avgLat}ms`);
console.log("by category:  " + Object.entries(byCat).map(([k, v]) => `${k} ${v.p}/${v.n}`).join("   "));
console.log(`leakage failures: ${leakFails.length}   refusal failures: ${refusalFails.length}`);
const top = results.filter((r) => !r.pass).slice(0, 10);
if (top.length) { console.log("\nTop failures:"); for (const r of top) console.log(`  ${r.id}  ${r.query}  ->  ${(r.reasons || []).join("; ")}`); }

const report = { generatedAtMs: Date.now(), base: BASE, total: results.length, passed, failed: results.length - passed, avgScore: avg, avgLatencyMs: avgLat, byCategory: byCat, leakageFailures: leakFails.map((r) => r.id), refusalFailures: refusalFails.map((r) => r.id), results };
writeFileSync(new URL("./evals/latest-report.json", import.meta.url), JSON.stringify(report, null, 2));
console.log("\nreport -> scripts/evals/latest-report.json");
process.exitCode = leakFails.length === 0 && refusalFails.length === 0 ? 0 : 1;