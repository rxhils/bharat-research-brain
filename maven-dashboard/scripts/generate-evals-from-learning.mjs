// Maven Self-Learning Improvement Loop v1 - eval-case generator.
//
// Reads the operator's triaged learning events and turns each real failure into a SUGGESTED eval
// case, so a regression the operator noticed once becomes a permanent guardrail in the eval suite.
// This generator ONLY proposes cases for review - it never edits the main eval files
// (run-maven-evals.mjs, maven-eval-cases*, test-source-depth.mjs).
//
//   node scripts/generate-evals-from-learning.mjs            # print suggestions to stdout (no writes)
//   node scripts/generate-evals-from-learning.mjs --apply    # write scripts/evals/learned-eval-cases.suggested.json
//   node scripts/generate-evals-from-learning.mjs --input <path>   # override events file (default below)
//
// Intended package.json script (add manually - this generator does NOT edit package.json):
//   "learn:evals": "node scripts/generate-evals-from-learning.mjs"
//
// Input contract: data/maven-learning/events.json is a JSON array of MavenLearningEvent
//   { id, timestamp, userQuery, answerType?, resolvedSymbols?[], sourceCount?,
//     failureTypes[], failureExplanation?, expectedBehavior?, severity, status }
// A missing file is treated as []. Only events with a non-empty failureTypes and status in
// {new, triaged} are converted. The output is a *.suggested.json the operator reviews before
// wiring anything into the eval suite. Suggestions are printed as pure JSON to stdout; the
// one-line summary goes to stderr so `... > cases.json` stays clean.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const DEFAULT_INPUT = join(ROOT, "data", "maven-learning", "events.json");
const OUT_FILE = join(__dirname, "evals", "learned-eval-cases.suggested.json");

const argv = process.argv.slice(2);
const APPLY = argv.includes("--apply");
const inputIdx = argv.indexOf("--input");
const INPUT = inputIdx >= 0 && argv[inputIdx + 1] ? resolve(argv[inputIdx + 1]) : DEFAULT_INPUT;

const ELIGIBLE_STATUS = new Set(["new", "triaged"]);

const uniq = (xs) => [...new Set(xs.filter((x) => x != null && x !== ""))];

function slug(s) {
  return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 48) || "query";
}

// Visible-contract answer mode for a follow-up / mis-scoped query (mirrors the eval suite's modes).
function deriveAnswerMode(ev) {
  const q = String(ev.userQuery || "").toLowerCase();
  if (/\b(bullet|bullets|summar)/.test(q)) return "bullet_summary";
  if (/\btable\b/.test(q)) return "table";
  if (/\b(chart|graph|plot)\b/.test(q)) return "chart_first";
  if (/\bsources?\b/.test(q)) return "source_list";
  if (/\b(eli5|simpler|dumb it down)\b/.test(q)) return "eli5";
  if (/\b(explain|detail|elaborate|expand|more)\b/.test(q)) return "deep_explanation";
  return "clarification_answer";
}

// Per-failure-type rules. `priority` picks the dominant type -> the case's category. `apply` layers
// the expected guards onto the case; every failure type on an event is applied to its single case.
const FAILURE_RULES = {
  advice_leakage: {
    priority: 100, category: "unsafe",
    apply: (c) => { c.mustContainRefusal = true; c.mustNotContain = uniq([...(c.mustNotContain || []), "buy", "target"]); },
  },
  provider_leakage: {
    priority: 90, category: "official_source",
    apply: (c) => { c.mustNotContain = uniq([...(c.mustNotContain || []), "searxng", "scraper", "provider error", "fetch error", "anti-bot"]); },
  },
  out_of_scope_false_positive: {
    priority: 85, category: "market_summary",
    apply: (c, ev) => {
      c.expectedAnswerMode = deriveAnswerMode(ev);
      if (ev.answerType) c.expectedAnswerType = ev.answerType;
      c.mustNotContain = uniq([...(c.mustNotContain || []), "out of scope", "Maven focuses on Indian markets"]);
    },
  },
  bad_followup_handling: {
    priority: 80, category: "conversation_followup",
    apply: (c, ev) => {
      c.expectedAnswerMode = deriveAnswerMode(ev);
      c.mustNotContain = uniq([...(c.mustNotContain || []), "out of scope", "Maven focuses on Indian markets"]);
    },
  },
  wrong_symbol: {
    priority: 75, category: "single_stock",
    apply: (c, ev) => {
      c.expectResolvedSymbol = true;
      if (Array.isArray(ev.resolvedSymbols) && ev.resolvedSymbols.length) c.expectedSymbols = ev.resolvedSymbols;
    },
  },
  wrong_route: {
    priority: 70, category: "routing",
    apply: (c, ev) => { if (ev.answerType) c.expectedAnswerType = ev.answerType; },
  },
  thin_sources: {
    priority: 65, category: "source_depth",
    apply: (c) => { c.minSources = 5; c.mustHaveSources = true; },
  },
  missing_sources: {
    priority: 63, category: "source_depth",
    apply: (c) => { c.minSources = 1; c.mustHaveSources = true; },
  },
  stale_metric: {
    priority: 60, category: "freshness",
    apply: (c) => { c.requireFreshMetrics = true; },
  },
  unsupported_metric: {
    priority: 58, category: "freshness",
    apply: (c) => { c.requireSourcedMetrics = true; },
  },
  fake_catalyst: {
    priority: 56, category: "freshness",
    apply: (c) => { c.noInventedCatalyst = true; c.mustHaveSources = true; },
  },
  wrong_chart: {
    priority: 50, category: "chart",
    apply: (c) => { c.requireChart = true; },
  },
  weak_reasoning: {
    priority: 45, category: "reasoning",
    apply: (c) => { c.requireReasoning = true; },
  },
  bad_ui_render: {
    priority: 40, category: "ui_render",
    apply: (c) => { c.requireCleanRender = true; },
  },
  slow_response: {
    priority: 35, category: "performance",
    apply: (c) => { c.maxLatencyMs = 15000; },
  },
  other: {
    priority: 10, category: "misc",
    apply: () => {},
  },
};

function loadEvents(path) {
  let raw;
  try {
    raw = readFileSync(path, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw new Error(`Cannot read learning events at ${path}: ${e.message}`);
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Learning events file is not valid JSON (${path}): ${e.message}`);
  }
  if (!Array.isArray(data)) throw new Error(`Learning events file must be a JSON array (${path})`);
  return data;
}

function dominantType(types) {
  return [...types]
    .filter((t) => FAILURE_RULES[t])
    .sort((a, b) => FAILURE_RULES[b].priority - FAILURE_RULES[a].priority)[0];
}

function buildCase(ev, counter) {
  const declared = Array.isArray(ev.failureTypes) ? ev.failureTypes : [];
  const known = declared.filter((t) => FAILURE_RULES[t]);
  const unknown = declared.filter((t) => !FAILURE_RULES[t]);
  const types = known.length ? known : ["other"];
  const dom = dominantType(types) || "other";

  const c = {
    id: `learned_${slug(ev.userQuery)}_${String(counter).padStart(3, "0")}`,
    query: String(ev.userQuery || ""),
    category: FAILURE_RULES[dom].category,
  };

  for (const t of types) FAILURE_RULES[t].apply(c, ev);
  if (c.mustNotContain) c.mustNotContain = uniq(c.mustNotContain);

  // provenance for the reviewing operator
  c.severity = ev.severity || "medium";
  c.failureTypes = uniq(declared);
  c.sourceEventId = ev.id;
  c.notes = `Generated from learning event ${ev.id}` +
    (ev.expectedBehavior ? ` - expected: ${ev.expectedBehavior}` : "") +
    (unknown.length ? ` (unrecognized failureTypes: ${unknown.join(", ")})` : "");
  return c;
}

const events = loadEvents(INPUT);
const eligible = events.filter(
  (ev) => ev && Array.isArray(ev.failureTypes) && ev.failureTypes.length > 0 && ELIGIBLE_STATUS.has(ev.status),
);
const cases = eligible.map((ev, i) => buildCase(ev, i + 1));
const skipped = events.length - eligible.length;

if (APPLY) {
  writeFileSync(OUT_FILE, JSON.stringify(cases, null, 2) + "\n");
  console.error(
    `learn:evals - wrote ${cases.length} suggested eval case(s) to ${relative(ROOT, OUT_FILE)} ` +
    `(from ${eligible.length}/${events.length} eligible event(s), ${skipped} skipped). ` +
    `Review before wiring into the eval suite.`,
  );
} else {
  console.log(JSON.stringify(cases, null, 2));
  console.error(
    `learn:evals - ${cases.length} suggested eval case(s) from ${eligible.length}/${events.length} eligible event(s), ` +
    `${skipped} skipped. Re-run with --apply to write ${relative(ROOT, OUT_FILE)}.`,
  );
}
