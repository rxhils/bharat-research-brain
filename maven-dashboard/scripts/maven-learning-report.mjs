// Maven Self-Learning Improvement Loop v1 - learning report.
// Reads the learning event + suggestion logs and prints a readable console summary of
// what Maven got wrong, which patterns repeat, and which fixes/evals are queued.
// Intended npm script (add manually to package.json, this file does NOT touch it):
//   "learn:report": "node scripts/maven-learning-report.mjs"
// Run: node scripts/maven-learning-report.mjs
// Exit code: non-zero ONLY when there are unresolved (new|triaged) critical failures,
// so it can gate CI. Everything else exits 0.
import { readFileSync, existsSync } from "fs";

// Paths are resolved relative to this file so the script works regardless of cwd.
const EVENTS_URL = new URL("../data/maven-learning/events.json", import.meta.url);
const SUGGESTIONS_URL = new URL("../data/maven-learning/suggestions.json", import.meta.url);
const SUGGESTED_EVALS_URL = new URL("./evals/learned-eval-cases.suggested.json", import.meta.url);

// failureTypes vocabulary - kept here for reference / future validation.
const FAILURE_VOCAB = [
  "wrong_route", "out_of_scope_false_positive", "bad_followup_handling", "wrong_symbol",
  "thin_sources", "stale_metric", "unsupported_metric", "fake_catalyst", "wrong_chart",
  "weak_reasoning", "missing_sources", "provider_leakage", "advice_leakage",
  "bad_ui_render", "slow_response", "other",
];

const UNRESOLVED_STATUSES = new Set(["new", "triaged"]);

// Read a JSON array from a URL; a missing file is treated as [] per the data contract.
function readJsonArray(url, label) {
  let raw;
  try {
    raw = readFileSync(url, "utf8");
  } catch (e) {
    if (e.code === "ENOENT") return [];
    throw new Error(`failed reading ${label} (${url.pathname}): ${e.message}`);
  }
  const trimmed = raw.trim();
  if (!trimmed) return [];
  let parsed;
  try {
    parsed = JSON.parse(trimmed);
  } catch (e) {
    throw new Error(`invalid JSON in ${label} (${url.pathname}): ${e.message}`);
  }
  if (!Array.isArray(parsed)) throw new Error(`${label} must be a JSON array, got ${typeof parsed}`);
  return parsed;
}

const events = readJsonArray(EVENTS_URL, "events.json");
const suggestions = readJsonArray(SUGGESTIONS_URL, "suggestions.json");

// A one-line ellipsized preview so the console stays readable.
function short(s, n = 80) {
  const str = String(s ?? "").replace(/\s+/g, " ").trim();
  return str.length > n ? str.slice(0, n - 1) + "…" : str;
}

// --- Section 1: totals ---------------------------------------------------------
console.log(`MAVEN LEARNING REPORT  ${new Date().toISOString()}`);
console.log(`\nTotal learning events: ${events.length}`);
console.log(`Total suggestions:     ${suggestions.length}`);

// --- Section 2: failures by type ----------------------------------------------
const byType = new Map();
for (const ev of events) {
  const types = Array.isArray(ev.failureTypes) ? ev.failureTypes : [];
  for (const t of types) byType.set(t, (byType.get(t) || 0) + 1);
}
const byTypeSorted = [...byType.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
console.log(`\nFAILURES BY TYPE (${byTypeSorted.length} distinct)`);
if (byTypeSorted.length === 0) {
  console.log("  (none logged)");
} else {
  for (const [type, count] of byTypeSorted) {
    const known = FAILURE_VOCAB.includes(type) ? "" : "  (!unknown type)";
    console.log(`  ${String(count).padStart(4)}  ${type}${known}`);
  }
}

// --- Section 3: top repeated failure patterns (failureType + answerType) -------
const byPattern = new Map();
for (const ev of events) {
  const answerType = ev.answerType || "unknown";
  const types = Array.isArray(ev.failureTypes) ? ev.failureTypes : [];
  for (const t of types) {
    const key = `${t} @ ${answerType}`;
    byPattern.set(key, (byPattern.get(key) || 0) + 1);
  }
}
const repeated = [...byPattern.entries()]
  .filter(([, c]) => c >= 2)
  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
console.log(`\nTOP REPEATED PATTERNS  (failureType @ answerType, count >= 2)`);
if (repeated.length === 0) {
  console.log("  (no pattern repeats yet)");
} else {
  for (const [key, count] of repeated.slice(0, 10)) {
    console.log(`  ${String(count).padStart(4)}x  ${key}`);
  }
}

// --- Section 4: critical failures ---------------------------------------------
const critical = events.filter((ev) => ev.severity === "critical");
console.log(`\nCRITICAL FAILURES (${critical.length})`);
if (critical.length === 0) {
  console.log("  (none)");
} else {
  for (const ev of critical) {
    const types = Array.isArray(ev.failureTypes) ? ev.failureTypes.join(",") : "";
    console.log(`  [${ev.status ?? "?"}] ${ev.id ?? "?"}  ${types}`);
    console.log(`    q: ${short(ev.userQuery)}`);
    if (ev.failureExplanation) console.log(`    -> ${short(ev.failureExplanation, 120)}`);
  }
}

// --- Section 5: unresolved failures (status new|triaged) -----------------------
const unresolved = events.filter((ev) => UNRESOLVED_STATUSES.has(ev.status));
console.log(`\nUNRESOLVED FAILURES (status new|triaged): ${unresolved.length}`);
if (unresolved.length > 0) {
  const ids = unresolved.map((ev) => ev.id ?? "?");
  console.log(`  ids: ${ids.join(", ")}`);
}

// --- Section 6: suggested fixes (grouped by suggestedFixType) ------------------
const byFixType = new Map();
for (const s of suggestions) {
  const ft = s.suggestedFixType || "unspecified";
  if (!byFixType.has(ft)) byFixType.set(ft, []);
  byFixType.get(ft).push(s);
}
const fixGroups = [...byFixType.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
console.log(`\nSUGGESTED FIXES (${suggestions.length}, grouped by fixType)`);
if (fixGroups.length === 0) {
  console.log("  (none)");
} else {
  for (const [fixType, group] of fixGroups) {
    console.log(`  ${fixType}  (${group.length})`);
    for (const s of group) {
      const approval = s.requiresApproval ? " [needs approval]" : "";
      const evc = Array.isArray(s.eventIds) ? s.eventIds.length : 0;
      console.log(`    - ${s.id ?? "?"}: ${short(s.summary, 90)}  (events:${evc})${approval}`);
    }
  }
}

// --- Section 7: suggested eval cases -------------------------------------------
// Distinguish "file missing" (operator hasn't generated evals yet) from "file present
// but empty" - the former points at the generator step, the latter is a real 0 count.
let evalNote;
if (existsSync(SUGGESTED_EVALS_URL)) {
  try {
    const suggestedEvals = readJsonArray(SUGGESTED_EVALS_URL, "learned-eval-cases.suggested.json");
    evalNote = `${suggestedEvals.length} case(s) in scripts/evals/learned-eval-cases.suggested.json`;
  } catch (e) {
    evalNote = `unreadable (${e.message})`;
  }
} else {
  evalNote = "no suggested eval file - run learn:evals";
}
console.log(`\nSUGGESTED EVAL CASES: ${evalNote}`);

// --- Gate: fail CI only on unresolved critical failures ------------------------
const unresolvedCritical = events.filter(
  (ev) => ev.severity === "critical" && UNRESOLVED_STATUSES.has(ev.status),
);
console.log(`\nUNRESOLVED CRITICAL: ${unresolvedCritical.length}`);
if (unresolvedCritical.length > 0) {
  console.log(`  ids: ${unresolvedCritical.map((ev) => ev.id ?? "?").join(", ")}`);
  console.log("FAIL: unresolved critical failures block the loop.");
  process.exitCode = 1;
} else {
  console.log("OK: no unresolved critical failures.");
  process.exitCode = 0;
}
