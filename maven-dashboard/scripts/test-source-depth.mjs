// Maven Source Depth & Research Quality Loop v1 - diagnostic harness.
// Tests source depth/evidence quality for company/stock research queries against /api/ask.
// Run: node scripts/test-source-depth.mjs   (set MAVEN_EVAL_URL to override target)
import { writeFileSync } from "fs";
import { scanLeak, scanAdvice, scanFreshness, scanSourceRiskTerms } from "./evals/eval-guards.mjs";
import { scoreSourceDepth } from "./evals/source-depth-scorer.mjs";

const BASE = process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask";

// tier: expected depth tier per the task's own threshold table (light/standard/deep).
// officialRequired: results/shareholding/market-share/capex queries must attempt official sources first.
const QUERIES = [
  // A. Single-stock standard
  { q: "Why is Poonawalla Fincorp moving today?", cat: "A_single_stock", tier: "standard" },
  { q: "Why is Blue Star moving today?", cat: "A_single_stock", tier: "standard" },
  { q: "Why is Reliance moving today?", cat: "A_single_stock", tier: "standard" },
  { q: "Why is Zomato falling?", cat: "A_single_stock", tier: "standard" },
  { q: "Explain Cochin Shipyard", cat: "A_single_stock", tier: "standard" },
  // B. Stock comparison
  { q: "Compare Tata Elxsi and KPIT Tech in a chart", cat: "B_comparison", tier: "standard" },
  { q: "Compare HDFC Bank and ICICI Bank in a chart", cat: "B_comparison", tier: "standard" },
  { q: "Compare Reliance and ONGC in a chart", cat: "B_comparison", tier: "standard" },
  { q: "Compare HAL and BEL", cat: "B_comparison", tier: "standard" },
  { q: "Compare Voltas and Blue Star", cat: "B_comparison", tier: "standard" },
  // C. Deep research
  { q: "Give me a full research report on Blue Star", cat: "C_deep_research", tier: "deep" },
  { q: "Analyze Poonawalla Fincorp in detail", cat: "C_deep_research", tier: "deep" },
  { q: "Deep research on Tata Elxsi", cat: "C_deep_research", tier: "deep" },
  { q: "Full view on Reliance", cat: "C_deep_research", tier: "deep" },
  { q: "Analyze Cochin Shipyard in detail", cat: "C_deep_research", tier: "deep" },
  // D. Latest data / official-data queries
  { q: "Latest results for Blue Star", cat: "D_latest_data", tier: "standard", officialRequired: true },
  { q: "Blue Star market share", cat: "D_latest_data", tier: "standard", officialRequired: true },
  { q: "Latest capex update for Blue Star", cat: "D_latest_data", tier: "standard", officialRequired: true },
  { q: "Shareholding pattern of Reliance", cat: "D_latest_data", tier: "standard", officialRequired: true },
  { q: "Latest investor presentation for Tata Motors", cat: "D_latest_data", tier: "standard", officialRequired: true },
];

const OFFICIAL_DOMAINS = /nseindia\.com|bseindia\.com|rbi\.org\.in|sebi\.gov\.in/i;

async function ask(query) {
  const t0 = Date.now();
  const r = await fetch(BASE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
  const j = await r.json();
  return { j, ms: Date.now() - t0 };
}

const rows = [];
for (const c of QUERIES) {
  try {
    const { j, ms } = await ask(c.q);
    const sources = j.sources || [];
    const ev = j.evidence || {};
    const leak = scanLeak(j);
    const advice = scanAdvice(j);
    const freshness = scanFreshness(j, { historical: false });
    // Informational only: a cited source's own title/snippet using advisory language (e.g. a news
    // headline reporting a brokerage's target price) is not Maven leakage - never gates pass/fail.
    const sourceRiskTerm = scanSourceRiskTerms(j);
    // fake-official check: any source CLAIMING type "official" whose URL isn't actually an official domain
    const fakeOfficial = sources.filter((s) => s.type === "official" && s.url && !OFFICIAL_DOMAINS.test(s.url));
    // "market data" (Yahoo Finance) and "Maven analysis" chips are always present regardless of
    // whether a search provider is configured - the market-data chip even carries confidence
    // "retrieved", so it must NOT be counted as evidence a search provider actually returned
    // results. realSourceCount excludes both synthetic chips.
    const realSourceCount = sources.filter((s) => s.type !== "market_data" && s.type !== "analysis").length;
    const row = {
      query: c.q, category: c.cat, tier: c.tier, officialRequired: !!c.officialRequired,
      answerType: j.type ?? j.answerType ?? "",
      evidenceDepth: ev.evidenceDepth ?? null,
      sourceBudget: ev.sourceBudget ?? null,
      sourceCount: ev.sourceCount ?? sources.length,
      officialSourceCount: ev.officialSourceCount ?? 0,
      verifiedSourceCount: ev.verifiedSourceCount ?? 0,
      retrievedSourceCount: ev.retrievedSourceCount ?? 0,
      analysisOnlySourceCount: ev.analysisOnlySourceCount ?? 0,
      clickableUrlCount: sources.filter((s) => s.url).length,
      latestPeriodFound: ev.latestPeriodFound ?? null,
      latestAnnualPeriodFound: ev.latestAnnualPeriodFound ?? null,
      metricEvidenceCount: ev.metricEvidenceCount ?? 0,
      blockedMetricCount: ev.blockedMetricCount ?? 0,
      coverageStatus: ev.coverageStatus ?? null,
      limitations: j.limitations || [],
      chartCount: (j.charts || []).length,
      latencyMs: ms,
      leak, advice, freshness, fakeOfficialCount: fakeOfficial.length, realSourceCount, sourceRiskTerm,
    };
    const scored = scoreSourceDepth(row);
    rows.push({ ...row, score: scored.score, pass: scored.pass, reasons: scored.reasons });
    console.log(`${c.cat.padEnd(16)} ${scored.pass ? "OK" : "XX"} ${String(scored.score).padStart(3)}  src=${row.sourceCount}/${row.sourceBudget ?? "?"} url=${row.clickableUrlCount} off=${row.officialSourceCount} cov=${row.coverageStatus}  ${c.q}`);
    if (!scored.pass) console.log(`   -> ${scored.reasons.join("; ")}`);
    if (sourceRiskTerm.length) console.log(`   (sourceRiskTerm, informational only: ${sourceRiskTerm.join(",")})`);
  } catch (e) {
    rows.push({ query: c.q, category: c.cat, tier: c.tier, score: 0, pass: false, reasons: ["ERROR " + e.message] });
    console.log(`${c.cat.padEnd(16)} XX   0  ERROR ${e.message}  ${c.q}`);
  }
}

const passed = rows.filter((r) => r.pass).length;
const avg = Math.round(rows.reduce((a, r) => a + (r.score || 0), 0) / rows.length);
const byTier = {};
for (const r of rows) { (byTier[r.category] ??= { p: 0, n: 0, srcSum: 0 }); byTier[r.category].n++; if (r.pass) byTier[r.category].p++; byTier[r.category].srcSum += r.sourceCount || 0; }

console.log(`\nTOTAL ${rows.length}  passed ${passed}  failed ${rows.length - passed}  avgScore ${avg}`);
for (const [cat, v] of Object.entries(byTier)) console.log(`  ${cat}: ${v.p}/${v.n}  avgSources=${(v.srcSum / v.n).toFixed(1)}`);

const report = { generatedAtMs: Date.now(), base: BASE, total: rows.length, passed, failed: rows.length - passed, avgScore: avg, byCategory: byTier, results: rows };
writeFileSync(new URL("./evals/source-depth-report.json", import.meta.url), JSON.stringify(report, null, 2));
console.log("\nreport -> scripts/evals/source-depth-report.json");
process.exitCode = passed === rows.length ? 0 : 1;
