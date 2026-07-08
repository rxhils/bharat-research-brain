// Maven Self-Learning Improvement Loop v1 - orchestration / triage runner.
//
// Intended to be wired as an npm script `learn:loop` (e.g. "learn:loop": "node
// scripts/maven-improvement-loop.mjs"). DO NOT edit package.json here - that wiring is a
// separate, human-approved change. Run directly with:  node scripts/maven-improvement-loop.mjs
//
// WHAT THIS DOES (read-only, print-only):
//   1. Runs the existing eval suites as child processes (npm run eval:maven, eval:sources).
//      Suites hit a running server / remote URL; if that's unreachable the suite is reported
//      "unavailable" and the loop continues - it NEVER throws on a missing/erroring suite.
//   2. Reads the local learning event store (data/maven-learning/events.json) and aggregates
//      captured failures by type.
//   3. Prints a PRIORITIZED fix plan (fixed priority order) mapping failure buckets to the
//      subsystem that owns the fix (routing / retrieval / resolver / metric_validator /
//      guardrail / ui).
//
// WHAT THIS MUST NEVER DO: edit code, edit package.json, write files, mutate the event store,
// place orders, or emit advisory language. It only reads data, runs evals, and prints a plan.
// A human approves and applies any actual fix. See docs/maven-learning-loop.md.

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const EVENTS_FILE = path.join(REPO_ROOT, "data", "maven-learning", "events.json");

// Signals that a suite failed because the target server / remote URL was unreachable or the
// /api/ask endpoint isn't serving JSON (server up but route missing -> HTML error page, so the
// eval's r.json() throws). Either way it's an environment issue, not a real regression, so it
// is treated as "unavailable" rather than a hard-fail.
const UNREACHABLE_RE =
  /ECONNREFUSED|ENOTFOUND|ECONNRESET|ETIMEDOUT|EAI_AGAIN|fetch failed|failed to fetch|network error|UND_ERR|socket hang up|not valid JSON|Unexpected token '<'|<!DOCTYPE/i;

// ---------------------------------------------------------------------------
// 1. Run the eval suites (tolerant: never throws)
// ---------------------------------------------------------------------------

/**
 * Run one npm eval script and classify the outcome without throwing.
 * @returns {{ name: string, state: "ran"|"unavailable", passed: number|null,
 *             failed: number|null, summary: string|null, hardFailed: boolean, note: string }}
 */
function runSuite(name, script) {
  let res;
  try {
    res = spawnSync("npm", ["run", script], {
      shell: true,
      encoding: "utf8",
      cwd: REPO_ROOT,
      timeout: 5 * 60 * 1000,
    });
  } catch (e) {
    return { name, state: "unavailable", passed: null, failed: null, summary: null, hardFailed: false, note: `spawn error: ${e.message}` };
  }

  // spawn itself failed (e.g. npm not on PATH, script missing, timeout).
  if (res.error) {
    const why = res.error.code === "ENOENT" ? "npm not found on PATH" : res.error.message;
    return { name, state: "unavailable", passed: null, failed: null, summary: null, hardFailed: false, note: why };
  }

  const out = `${res.stdout || ""}\n${res.stderr || ""}`;

  // npm couldn't find the script at all ("Missing script"/"command not found").
  if (/missing script|command not found|could not determine executable/i.test(out)) {
    return { name, state: "unavailable", passed: null, failed: null, summary: null, hardFailed: false, note: "npm script not defined" };
  }

  // Server / remote URL unreachable, or up but not serving JSON on /api/ask -> report as
  // unavailable, not a genuine regression.
  if (UNREACHABLE_RE.test(out)) {
    const note = /not valid JSON|Unexpected token '<'|<!DOCTYPE/i.test(out)
      ? "server up but /api/ask not serving JSON (route missing / not started)"
      : "server not running (connection refused)";
    return { name, state: "unavailable", passed: null, failed: null, summary: null, hardFailed: false, note };
  }

  // Both suites print a summary line beginning with TOTAL, e.g.
  //   TOTAL 20  passed 5  failed 15  avgScore 47
  const summaryLine = out.split(/\r?\n/).find((l) => /^\s*TOTAL\b/.test(l)) || null;
  const m = summaryLine && summaryLine.match(/passed\s+(\d+)\s+failed\s+(\d+)/i);

  if (m) {
    const passed = Number(m[1]);
    const failed = Number(m[2]);
    return {
      name,
      state: "ran",
      passed,
      failed,
      summary: summaryLine.trim(),
      hardFailed: res.status !== 0 || failed > 0, // suite ran and reported regressions
      note: "",
    };
  }

  // Ran but produced no parseable summary - treat as unavailable rather than guessing.
  return { name, state: "unavailable", passed: null, failed: null, summary: null, hardFailed: false, note: `no summary parsed (exit ${res.status})` };
}

// ---------------------------------------------------------------------------
// 2. Read + aggregate the learning event store
// ---------------------------------------------------------------------------

function loadEvents() {
  try {
    const parsed = JSON.parse(readFileSync(EVENTS_FILE, "utf8"));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return []; // missing / unreadable / malformed => empty, never throw
  }
}

// Fixed priority order + subsystem ownership. Mirrors lib/maven/learningTypes.ts failure
// vocabulary and lib/maven/learningStore.ts FIX_BY_FAILURE mapping.
const PRIORITY = [
  { rank: 1, label: "Advice leakage (buy/sell/target language)",       types: ["advice_leakage"],                                     subsystem: "guardrail" },
  { rank: 2, label: "Provider / model / backend leakage",              types: ["provider_leakage"],                                   subsystem: "guardrail" },
  { rank: 3, label: "Stale / unsupported metric",                      types: ["stale_metric", "unsupported_metric"],                 subsystem: "metric_validator" },
  { rank: 4, label: "Wrong symbol resolution",                         types: ["wrong_symbol"],                                       subsystem: "resolver" },
  { rank: 5, label: "Out-of-scope false positive / bad follow-up",     types: ["out_of_scope_false_positive", "bad_followup_handling"], subsystem: "routing" },
  { rank: 6, label: "Thin / missing sources",                          types: ["thin_sources", "missing_sources"],                    subsystem: "retrieval" },
  { rank: 7, label: "Weak reasoning",                                  types: ["weak_reasoning"],                                     subsystem: "answer_generator" },
  { rank: 8, label: "Bad UI render",                                   types: ["bad_ui_render"],                                      subsystem: "ui" },
];

const COVERED = new Set(PRIORITY.flatMap((p) => p.types));

const MAX_EXAMPLES = 5;

/** Collect events whose failureTypes intersect the given set, with example queries. */
function bucketFor(events, types) {
  const set = new Set(types);
  const matched = events.filter((e) => Array.isArray(e.failureTypes) && e.failureTypes.some((t) => set.has(t)));
  const queries = [];
  for (const e of matched) {
    const q = (e.userQuery || "").trim();
    if (q && !queries.includes(q)) queries.push(q);
    if (queries.length >= MAX_EXAMPLES) break;
  }
  return { count: matched.length, queries };
}

// ---------------------------------------------------------------------------
// 3. Report
// ---------------------------------------------------------------------------

console.log("Maven Self-Learning Improvement Loop  (learn:loop)");
console.log("read-only triage: run evals + aggregate learning events + print fix plan. No code edits.\n");

// --- eval suites ---
console.log("EVAL SUITES");
const suites = [runSuite("eval:maven", "eval:maven"), runSuite("eval:sources", "eval:sources")];
for (const s of suites) {
  if (s.state === "ran") {
    const verdict = s.hardFailed ? "FAIL" : "OK";
    console.log(`  ${s.name.padEnd(14)} ${verdict.padEnd(11)} passed ${s.passed} / failed ${s.failed}`);
    if (s.summary) console.log(`  ${" ".repeat(14)} ${s.summary}`);
  } else {
    console.log(`  ${s.name.padEnd(14)} ${"unavailable".padEnd(11)} ${s.note}`);
  }
}

// --- learning data ---
const events = loadEvents();
const bySeverity = {};
for (const e of events) bySeverity[e.severity || "unknown"] = (bySeverity[e.severity || "unknown"] || 0) + 1;
const sevSummary = Object.entries(bySeverity).map(([k, v]) => `${k} ${v}`).join("   ") || "none";

console.log("\nLEARNING DATA");
console.log(`  store: ${path.relative(REPO_ROOT, EVENTS_FILE)}`);
console.log(`  total events: ${events.length}   (by severity: ${sevSummary})`);

// --- prioritized fix plan ---
console.log("\nPRIORITIZED FIX PLAN");
let anyBucket = false;
let criticalFailures = 0;

for (const p of PRIORITY) {
  const b = bucketFor(events, p.types);
  if (b.count === 0) continue;
  anyBucket = true;
  if (p.rank <= 2) criticalFailures += b.count; // advice_leakage + provider_leakage are critical

  console.log(`\n  [P${p.rank}] ${p.label}`);
  console.log(`        events:    ${b.count}`);
  console.log(`        fix in:    ${p.subsystem}`);
  console.log(`        examples:`);
  for (const q of b.queries) console.log(`          - ${q}`);
  if (b.count > b.queries.length) console.log(`          ... and ${b.count - b.queries.length} more`);
}

// Catch-all: any captured failure type outside the 8 prioritized buckets (wrong_route,
// fake_catalyst, wrong_chart, slow_response, other) so nothing is silently dropped.
const otherTypes = [...new Set(events.flatMap((e) => (Array.isArray(e.failureTypes) ? e.failureTypes : [])).filter((t) => !COVERED.has(t)))];
if (otherTypes.length) {
  const b = bucketFor(events, otherTypes);
  anyBucket = true;
  console.log(`\n  [--] Unprioritized / other (${otherTypes.join(", ")})`);
  console.log(`        events:    ${b.count}`);
  console.log(`        fix in:    triage manually (see lib/maven/learningStore.ts FIX_BY_FAILURE)`);
  console.log(`        examples:`);
  for (const q of b.queries) console.log(`          - ${q}`);
}

if (!anyBucket) {
  console.log("\n  No captured failures to prioritize. (Empty or all-clean event store.)");
}

// --- exit code ---
// Exit non-zero ONLY when a suite genuinely hard-failed AND there are critical (leakage)
// failures in the learning store - the combination that should block a green loop. An
// unreachable server (unavailable) or a clean store leaves the loop at exit 0.
const anyHardFail = suites.some((s) => s.state === "ran" && s.hardFailed);
console.log(`\nSUMMARY  suites: ${suites.map((s) => `${s.name}=${s.state === "ran" ? (s.hardFailed ? "fail" : "ok") : "unavailable"}`).join("  ")}   critical-leakage events: ${criticalFailures}`);
if (anyHardFail && criticalFailures > 0) {
  console.log("RESULT   BLOCKING: eval suite hard-failed and critical leakage events are pending. Fix P1/P2 first.");
  process.exitCode = 1;
} else {
  console.log("RESULT   non-blocking: review the plan above and convert top buckets into regression eval cases.");
  process.exitCode = 0;
}
