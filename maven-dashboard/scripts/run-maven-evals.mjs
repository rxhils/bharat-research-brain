import { writeFileSync } from "fs";
import { CASES } from "./evals/maven-eval-cases.mjs";
import { scoreCase, scoreFollowUpCase } from "./evals/eval-scorer.mjs";

const BASE = process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask";

async function ask(query, conversationContext) {
  const t0 = Date.now();
  const body = conversationContext ? { query, conversationContext } : { query };
  const r = await fetch(BASE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { j: await r.json(), ms: Date.now() - t0 };
}

console.log(`Maven evals -> ${BASE}  (${CASES.length} cases)\n`);
const results = [];
for (const c of CASES) {
  try {
    // Multi-turn case: run the setup query first, then send the follow-up with a
    // conversationContext built from the setup answer (same shape the frontend sends).
    // injectContext cases send a RAW crafted context instead (adversarial-injection guard).
    let setupResp = null, ctx;
    if (c.injectContext) {
      ctx = c.injectContext;
      setupResp = c.injectContext.turns?.[0]?.answer ?? null;
    } else if (c.setup) {
      setupResp = (await ask(c.setup)).j;
      ctx = { turns: [{ id: "t1", userQuery: c.setup, answer: setupResp }] };
    }
    const { j, ms } = await ask(c.query, ctx);
    const scored = c.category === "conversation_followup" ? scoreFollowUpCase(c, setupResp ?? {}, j, ms) : scoreCase(c, j, ms);
    results.push({ id: c.id, category: c.category, query: c.query, headline: j.headline, evidence: j.evidence, latestDataChecklist: j.latestDataChecklist, ...scored });
  }
  catch (e) { results.push({ id: c.id, category: c.category, query: c.query, pass: false, score: 0, reasons: ["ERROR " + e.message], leak: [], refused: false, latencyMs: 0 }); }
}

const passed = results.filter((r) => r.pass).length;
const avg = Math.round(results.reduce((a, r) => a + (r.score || 0), 0) / results.length);
const avgLat = Math.round(results.reduce((a, r) => a + (r.latencyMs || 0), 0) / results.length);
const byCat = {};
for (const r of results) { (byCat[r.category] ??= { p: 0, n: 0 }); byCat[r.category].n++; if (r.pass) byCat[r.category].p++; }
const leakFails = results.filter((r) => r.leak && r.leak.length);
const refusalFails = results.filter((r) => { const c = CASES.find((x) => x.id === r.id); return c.mustRefuse && !r.refused; });
// Evidence & Deep Research UI v1: for stock-research categories, evidence must be a well-formed
// object (schema integrity, not a threshold on source counts - those depend on a live provider).
const EVIDENCE_CATEGORIES = ["single_stock", "comparison", "nse_universe", "company_data"];
const evidenceFails = results.filter((r) => {
  const c = CASES.find((x) => x.id === r.id);
  if (!c || !EVIDENCE_CATEGORIES.includes(c.category)) return false;
  const ev = r.evidence;
  return ev == null || typeof ev !== "object" || typeof ev.sourceCount !== "number" || Number.isNaN(ev.sourceCount);
});
// Freshness lock: stale FY metrics or unsourced approximate metrics in current stock answers.
const freshnessFails = results.filter((r) => r.freshness && r.freshness.length);
const staleMetricFailures = freshnessFails.filter((r) => r.freshness.some((f) => f.startsWith("stale:")));
const approxMetricFailures = freshnessFails.filter((r) => r.freshness.some((f) => f.startsWith("approx:")));
// Verified Company Data Engine v2: company queries must carry a latest-data checklist.
const checklistFails = results.filter((r) => {
  const c = CASES.find((x) => x.id === r.id);
  return c?.requireChecklist && (!Array.isArray(r.latestDataChecklist) || r.latestDataChecklist.length === 0);
});

console.log("ID   ACTUAL TYPE               P   SC  REASONS");
for (const r of results) console.log(`${r.id.padEnd(4)} ${String(r.type || "-").padEnd(24)} ${r.pass ? "OK" : "XX"}  ${String(r.score).padStart(3)}  ${(r.reasons || []).join("; ")}`);

console.log(`\nTOTAL ${results.length}   passed ${passed}   failed ${results.length - passed}   avgScore ${avg}   avgLatency ${avgLat}ms`);
console.log("by category:  " + Object.entries(byCat).map(([k, v]) => `${k} ${v.p}/${v.n}`).join("   "));
console.log(`leakage failures: ${leakFails.length}   refusal failures: ${refusalFails.length}   evidence-schema failures: ${evidenceFails.length}   stale-metric failures: ${staleMetricFailures.length}   approx-metric failures: ${approxMetricFailures.length}   checklist-missing failures: ${checklistFails.length}`);
const top = results.filter((r) => !r.pass).slice(0, 10);
if (top.length) { console.log("\nTop failures:"); for (const r of top) console.log(`  ${r.id}  ${r.query}  ->  ${(r.reasons || []).join("; ")}`); }

const report = { generatedAtMs: Date.now(), base: BASE, total: results.length, passed, failed: results.length - passed, avgScore: avg, avgLatencyMs: avgLat, byCategory: byCat, leakageFailures: leakFails.map((r) => r.id), refusalFailures: refusalFails.map((r) => r.id), evidenceSchemaFailures: evidenceFails.map((r) => r.id), staleMetricFailures: staleMetricFailures.map((r) => r.id), approxMetricFailures: approxMetricFailures.map((r) => r.id), checklistFailures: checklistFails.map((r) => r.id), results };
writeFileSync(new URL("./evals/latest-report.json", import.meta.url), JSON.stringify(report, null, 2));
console.log("\nreport -> scripts/evals/latest-report.json");
process.exitCode = leakFails.length === 0 && refusalFails.length === 0 && evidenceFails.length === 0 && freshnessFails.length === 0 && checklistFails.length === 0 ? 0 : 1;