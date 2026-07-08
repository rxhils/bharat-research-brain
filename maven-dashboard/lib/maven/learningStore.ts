// Maven Self-Learning Improvement Loop v1 - local JSON event store.
//
// v1 uses local JSON files under data/maven-learning/. This is intentionally simple and
// supervised. NOTE: serverless filesystems (e.g. Vercel) are ephemeral/read-only outside
// /tmp, so durable production capture should later move to a Supabase-backed store. See
// docs/maven-learning-loop.md.
//
// Hard rules enforced here: no secrets/keys/PII persisted, minimal payloads only.

import { promises as fs } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type {
  MavenLearningEvent,
  MavenLearningEventStatus,
  MavenLearningSuggestion,
  MavenSuggestedFixType,
} from "./learningTypes";

const DATA_DIR = path.join(process.cwd(), "data", "maven-learning");
const EVENTS_FILE = path.join(DATA_DIR, "events.json");
const SUGGESTIONS_FILE = path.join(DATA_DIR, "suggestions.json");

const MAX_STR = 2000;
const MAX_ARR = 25;

/** Strip obvious secrets/PII before anything is written to disk. */
function redact(input: unknown): string {
  const s = typeof input === "string" ? input : String(input ?? "");
  return s
    .replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, "[email]")
    .replace(/\b\+?\d[\d\s-]{8,}\d\b/g, "[number]")
    .replace(/\b[A-Za-z0-9_-]{40,}\b/g, "[redacted]") // long opaque tokens / API keys
    .slice(0, MAX_STR);
}

function capArr<T>(a: T[] | undefined, n = MAX_ARR): T[] | undefined {
  return Array.isArray(a) ? a.slice(0, n) : undefined;
}

async function ensureDir(): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function readJson<T>(file: string, fallback: T): Promise<T> {
  try {
    return JSON.parse(await fs.readFile(file, "utf8")) as T;
  } catch {
    return fallback;
  }
}

async function writeJson(file: string, data: unknown): Promise<void> {
  await ensureDir();
  const tmp = `${file}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(data, null, 2), "utf8");
  await fs.rename(tmp, file); // near-atomic replace
}

export type NewLearningEvent = Omit<MavenLearningEvent, "id" | "timestamp" | "status"> & {
  status?: MavenLearningEventStatus;
};

function sanitize(e: NewLearningEvent): MavenLearningEvent {
  return {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    status: e.status ?? "new",
    userQuery: redact(e.userQuery),
    conversationContext: undefined, // never persist raw client context payloads in v1
    answerType: e.answerType,
    headline: e.headline ? redact(e.headline) : undefined,
    summary: e.summary ? redact(e.summary) : undefined,
    resolvedSymbols: capArr(e.resolvedSymbols),
    sourceCount: e.sourceCount,
    clickableSourceCount: e.clickableSourceCount,
    chartCount: e.chartCount,
    limitations: capArr(e.limitations)?.map((l) => redact(l)),
    userFeedback: e.userFeedback,
    failureTypes: capArr(e.failureTypes) ?? [],
    failureExplanation: e.failureExplanation ? redact(e.failureExplanation) : undefined,
    expectedBehavior: e.expectedBehavior ? redact(e.expectedBehavior) : undefined,
    severity: e.severity,
  };
}

export async function logLearningEvent(event: NewLearningEvent): Promise<MavenLearningEvent> {
  const events = await readJson<MavenLearningEvent[]>(EVENTS_FILE, []);
  const stored = sanitize(event);
  events.push(stored);
  await writeJson(EVENTS_FILE, events);
  return stored;
}

export interface LearningEventFilter {
  status?: MavenLearningEventStatus;
  failureType?: string;
  severity?: string;
}

export async function listLearningEvents(
  filter?: LearningEventFilter,
): Promise<MavenLearningEvent[]> {
  const events = await readJson<MavenLearningEvent[]>(EVENTS_FILE, []);
  return events.filter((e) => {
    if (filter?.status && e.status !== filter.status) return false;
    if (filter?.severity && e.severity !== filter.severity) return false;
    if (filter?.failureType && !e.failureTypes.includes(filter.failureType as never)) return false;
    return true;
  });
}

export async function updateLearningEventStatus(
  id: string,
  status: MavenLearningEventStatus,
): Promise<MavenLearningEvent | null> {
  const events = await readJson<MavenLearningEvent[]>(EVENTS_FILE, []);
  const idx = events.findIndex((e) => e.id === id);
  if (idx === -1) return null;
  events[idx] = { ...events[idx], status };
  await writeJson(EVENTS_FILE, events);
  return events[idx];
}

const FIX_BY_FAILURE: Record<string, MavenSuggestedFixType> = {
  wrong_route: "routing_rule",
  out_of_scope_false_positive: "routing_rule",
  bad_followup_handling: "routing_rule",
  wrong_symbol: "stock_resolver",
  thin_sources: "source_search",
  missing_sources: "source_search",
  stale_metric: "metric_validator",
  unsupported_metric: "metric_validator",
  fake_catalyst: "answer_generator",
  wrong_chart: "answer_generator",
  weak_reasoning: "answer_generator",
  provider_leakage: "guardrail",
  advice_leakage: "guardrail",
  bad_ui_render: "ui_render",
  slow_response: "answer_generator",
  other: "eval_case",
};

export async function createLearningSuggestion(
  events: MavenLearningEvent[],
): Promise<MavenLearningSuggestion> {
  const failures = events.flatMap((e) => e.failureTypes);
  const counts = new Map<string, number>();
  for (const f of failures) counts.set(f, (counts.get(f) ?? 0) + 1);
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  const suggestion: MavenLearningSuggestion = {
    id: randomUUID(),
    eventIds: events.map((e) => e.id),
    suggestedFixType: (top && FIX_BY_FAILURE[top]) || "eval_case",
    summary: `Recurring failure "${top ?? "unknown"}" across ${events.length} event(s). Review routing/retrieval/formatting and add a regression eval case before any fix ships.`,
    proposedEvalCase: undefined,
    requiresApproval: true,
  };
  const all = await readJson<MavenLearningSuggestion[]>(SUGGESTIONS_FILE, []);
  all.push(suggestion);
  await writeJson(SUGGESTIONS_FILE, all);
  return suggestion;
}

export async function exportLearningEvents(): Promise<MavenLearningEvent[]> {
  return readJson<MavenLearningEvent[]>(EVENTS_FILE, []);
}
