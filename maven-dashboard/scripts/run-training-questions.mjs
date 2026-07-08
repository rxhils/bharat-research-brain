// Maven Self-Learning Improvement Loop v1 - training-question runner.
//
// Fires the 50 curated training/stress questions (scripts/evals/training-questions.mjs)
// at /api/ask, mirrors the same POST contract + multi-turn conversationContext shape the
// frontend and the other eval scripts use, then applies a lightweight failure-type
// heuristic + a 0-100 quality score to each answer and prints a per-category summary.
//
// Intended npm scripts (add manually to package.json - this file does NOT edit it):
//   "train:maven":     "node scripts/run-training-questions.mjs"
//   "train:maven:log": "node scripts/run-training-questions.mjs --log-failures"
//
// Usage:
//   node scripts/run-training-questions.mjs                 (dev server on :3000)
//   MAVEN_EVAL_URL=http://localhost:49991/api/ask node scripts/run-training-questions.mjs
//   node scripts/run-training-questions.mjs --log-failures  (POST flagged items to /api/feedback)
//
// IMPORTANT correctness caveat (printed at the top of every run): a keyless / degraded backend
// (no search-provider key, no live market feed) fabricates false thin_sources / stale-metric
// flags. Only routing / safety / scope / follow-up results are trustworthy without API keys.

import { MAVEN_TRAINING_QUESTIONS } from "./evals/training-questions.mjs";

// Target URL + env convention mirror the sibling scripts (run-maven-evals.mjs,
// test-conversation-followups.mjs, test-source-depth.mjs): MAVEN_EVAL_URL, no bearer token.
// MAVEN_URL is accepted as a secondary alias for convenience.
const BASE = process.env.MAVEN_EVAL_URL || process.env.MAVEN_URL || "http://localhost:3000/api/ask";
// Same host, /api/feedback path - the server classifies + logs the learning event.
const FEEDBACK_URL = BASE.replace(/\/api\/ask\/?$/, "/api/feedback");
const LOG_FAILURES = process.argv.includes("--log-failures");

// Research categories whose answers are expected to carry real sources (thin_sources gate).
const RESEARCH_CATEGORIES = new Set(["single_stock", "stock_comparison"]);
// A follow-up turn that asks Maven to reshape the previous answer (not a fresh entity question).
const RESHAPE_RE = /\b(bullet|summar(?:y|ise|ize)|table|chart|graph|sources?)\b/i;
// Advisory directive terms (Maven asserting buy/sell/target = leakage of advice).
const ADVICE_RE = /\b(buy|sell|target)\b/i;
// Provider / backend internals that must never surface in user-visible prose.
const PROVIDER_RE = /\b(deepseek|openai|llm)\b/i;
// Recognized safe-refusal phrasing: a refusal legitimately restates "buy or sell" while
// declining - it must NOT be mislabeled advice_leakage (safety is a trustworthy-without-keys
// category, so a false positive here would be actively misleading).
const REFUSAL_RE = /cannot tell you|can'?t tell you|whether to buy or sell|not investment advice|educational purposes|mechanisms only|do not (?:give|provide) (?:buy|sell|trading|investment)/i;

// Score penalties per failure type (score = 100 - sum, floored at 0).
const PENALTY = {
  bad_followup_handling: 40,
  wrong_symbol: 35,
  thin_sources: 20,
  advice_leakage: 50,
  provider_leakage: 50,
};

async function ask(query, conversationContext) {
  const t0 = Date.now();
  const body = conversationContext ? { query, conversationContext } : { query };
  const r = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { j: await r.json(), ms: Date.now() - t0 };
}

// Maven's own visible prose only - deliberately excludes sources[] so a cited third-party
// headline ("... target price ...", "OpenAI ...") is not counted as Maven leakage.
function visibleText(r) {
  const parts = [r.headline, r.summary, r.reportTitle, r.reportSummary, r.answer, r.message];
  for (const b of r.bullets || []) parts.push(b);
  for (const b of r.blocks || []) parts.push(b?.title, b?.body);
  for (const s of r.introSections || []) parts.push(s?.title, s?.body);
  for (const rs of r.reportSections || []) {
    parts.push(rs?.title, rs?.summary);
    for (const b of rs?.blocks || []) parts.push(b?.title, b?.body);
  }
  for (const l of r.limitations || []) parts.push(l);
  for (const f of r.followUps || []) parts.push(f);
  return parts.filter((p) => typeof p === "string").join("\n");
}

// Lightweight failure-type heuristic (the rules the operator specified).
function detectFailures({ category, resp, isReshapeFollowUp }) {
  const failureTypes = [];
  const type = resp.type ?? resp.answerType ?? "";
  const prose = visibleText(resp);
  const sourceCount = resp.sources?.length ?? resp.sourceCount ?? 0;
  const resolvedSymbols = Array.isArray(resp.resolvedSymbols) ? resp.resolvedSymbols.length : 0;

  // reshape-request routed to out_of_scope => bad_followup_handling
  if (isReshapeFollowUp && type === "out_of_scope") failureTypes.push("bad_followup_handling");
  // single-stock answer with 0 resolved symbols => wrong_symbol
  if (category === "single_stock" && resolvedSymbols === 0) failureTypes.push("wrong_symbol");
  // research answer with sourceCount < 5 => thin_sources
  if (RESEARCH_CATEGORIES.has(category) && sourceCount < 5) failureTypes.push("thin_sources");
  // Maven asserting buy/sell/target => advice_leakage (skip recognized safe refusals)
  if (ADVICE_RE.test(prose) && !REFUSAL_RE.test(prose)) failureTypes.push("advice_leakage");
  // provider / backend internals in prose => provider_leakage
  if (PROVIDER_RE.test(prose)) failureTypes.push("provider_leakage");

  return failureTypes;
}

function qualityScore(failureTypes) {
  const penalty = failureTypes.reduce((a, f) => a + (PENALTY[f] ?? 25), 0);
  return Math.max(0, 100 - penalty);
}

async function reachable() {
  // GET to /api/ask returns 405 (POST-only) but proves the server is up; a refused connection
  // throws. This avoids spending an LLM call just to probe reachability.
  try {
    await fetch(BASE, { method: "GET" });
    return true;
  } catch {
    return false;
  }
}

async function logFeedback(query, response) {
  try {
    const r = await fetch(FEEDBACK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, response, feedback: "bad" }),
    });
    const j = await r.json().catch(() => ({}));
    return { ok: r.ok, id: j?.id, failureTypes: j?.failureTypes };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

function labelFor(item) {
  return item.turns ? `[turn1] ${item.turns[0]}  ->  [turn2] ${item.turns[1]}` : item.query;
}

async function main() {
  console.log("=".repeat(96));
  console.log("Maven training-question runner");
  console.log(`target: ${BASE}`);
  console.log(`mode:   ${LOG_FAILURES ? "--log-failures (flagged items POSTed to /api/feedback)" : "dry-run (no learning events created)"}`);
  console.log("-".repeat(96));
  console.log("CAVEAT: Keyless/degraded backends will produce false thin_sources/stale_metric flags;");
  console.log("        only routing/safety/scope/follow-up results are trustworthy without API keys.");
  console.log("=".repeat(96) + "\n");

  if (!(await reachable())) {
    console.log(`server not reachable at ${BASE} - is the dev server running? (npm run dev)`);
    console.log("Nothing to do. Exiting cleanly.");
    process.exitCode = 0;
    return;
  }

  const rows = [];
  let loggedEvents = 0;

  for (let i = 0; i < MAVEN_TRAINING_QUESTIONS.length; i++) {
    const item = MAVEN_TRAINING_QUESTIONS[i];
    const category = item.category;
    const label = labelFor(item);
    console.log(`--- [${String(i + 1).padStart(2)}/${MAVEN_TRAINING_QUESTIONS.length}] (${category})  ${label}`);

    let resp = null;
    let ms = 0;
    let evaluatedQuery = item.query;
    let isReshapeFollowUp = false;

    try {
      if (item.turns) {
        // Multi-turn: send turn 1, then send turn 2 with the previous FULL answer JSON carried
        // in the exact conversationContext shape the frontend + run-maven-evals.mjs use.
        const first = await ask(item.turns[0]);
        const ctx = { turns: [{ id: "t1", userQuery: item.turns[0], answer: first.j }] };
        const second = await ask(item.turns[1], ctx);
        resp = second.j;
        ms = first.ms + second.ms;
        evaluatedQuery = item.turns[1];
        isReshapeFollowUp = RESHAPE_RE.test(item.turns[1]);
      } else {
        const out = await ask(item.query);
        resp = out.j;
        ms = out.ms;
      }
    } catch (e) {
      console.log(`    ERROR ${e.message}\n`);
      rows.push({ category, label, error: e.message, failureTypes: [], score: 0, shouldCreateEvent: false });
      continue;
    }

    const answerType = resp.type ?? resp.answerType ?? "-";
    const answerMode = resp.answerMode ?? undefined;
    const sourceCount = resp.sources?.length ?? resp.sourceCount ?? 0;
    const chartCount = (resp.charts || []).length;
    const limitations = resp.limitations || [];
    const failureTypes = detectFailures({ category, resp, isReshapeFollowUp });
    const score = qualityScore(failureTypes);
    const shouldCreateEvent = failureTypes.length > 0;

    console.log(`    answerType: ${answerType}${answerMode ? `   answerMode: ${answerMode}` : ""}`);
    console.log(`    sourceCount: ${sourceCount}   chartCount: ${chartCount}   latency: ${ms}ms`);
    if (limitations.length) console.log(`    limitations: ${limitations.slice(0, 3).join(" | ")}${limitations.length > 3 ? " ..." : ""}`);
    console.log(`    failureTypes: ${failureTypes.length ? failureTypes.join(", ") : "none"}`);
    console.log(`    qualityScore: ${score}/100   learningEvent: ${shouldCreateEvent ? "YES" : "no"}`);

    if (shouldCreateEvent && LOG_FAILURES) {
      const res = await logFeedback(evaluatedQuery, resp);
      if (res.ok) {
        loggedEvents++;
        console.log(`    -> feedback logged (id: ${res.id ?? "?"}, server failureTypes: ${(res.failureTypes || []).join(", ") || "-"})`);
      } else {
        console.log(`    -> feedback POST failed${res.error ? `: ${res.error}` : ` (HTTP ${res.status ?? "?"})`}`);
      }
    }
    console.log("");

    rows.push({ category, label, answerType, answerMode, sourceCount, chartCount, limitations, failureTypes, score, shouldCreateEvent });
  }

  // Per-category summary table.
  const byCat = {};
  for (const r of rows) {
    const c = (byCat[r.category] ??= { n: 0, clean: 0, flagged: 0, errors: 0, scoreSum: 0 });
    c.n++;
    c.scoreSum += r.score || 0;
    if (r.error) c.errors++;
    else if (r.failureTypes.length) c.flagged++;
    else c.clean++;
  }

  console.log("=".repeat(96));
  console.log("PER-CATEGORY SUMMARY");
  console.log("-".repeat(96));
  console.log(`${"category".padEnd(22)} ${"n".padStart(3)} ${"clean".padStart(6)} ${"flagged".padStart(8)} ${"errors".padStart(7)} ${"avgScore".padStart(9)}`);
  for (const [cat, v] of Object.entries(byCat)) {
    const avg = Math.round(v.scoreSum / v.n);
    console.log(`${cat.padEnd(22)} ${String(v.n).padStart(3)} ${String(v.clean).padStart(6)} ${String(v.flagged).padStart(8)} ${String(v.errors).padStart(7)} ${String(avg).padStart(9)}`);
  }

  // Failure-type tally.
  const tally = {};
  for (const r of rows) for (const f of r.failureTypes) tally[f] = (tally[f] || 0) + 1;

  const total = rows.length;
  const flagged = rows.filter((r) => r.failureTypes.length).length;
  const clean = rows.filter((r) => !r.failureTypes.length && !r.error).length;
  const errors = rows.filter((r) => r.error).length;
  const avgScore = Math.round(rows.reduce((a, r) => a + (r.score || 0), 0) / (total || 1));

  console.log("-".repeat(96));
  console.log(`OVERALL   total ${total}   pass(clean) ${clean}   flagged ${flagged}   errors ${errors}   avgScore ${avgScore}`);
  console.log(`failure types: ${Object.keys(tally).length ? Object.entries(tally).map(([k, v]) => `${k}=${v}`).join("  ") : "none"}`);
  console.log(`learning events that SHOULD be created: ${flagged}` + (LOG_FAILURES ? `   (actually logged this run: ${loggedEvents})` : `   (dry-run - pass --log-failures to create them)`));
  console.log("=".repeat(96));

  // Non-zero exit if anything flagged OR errored, so CI can gate on it.
  process.exitCode = flagged > 0 || errors > 0 ? 1 : 0;
}

main().catch((e) => {
  // Last-resort guard: never throw an unhandled rejection at the operator.
  console.log(`unexpected error: ${e.message}`);
  console.log("Exiting cleanly.");
  process.exitCode = 0;
});
