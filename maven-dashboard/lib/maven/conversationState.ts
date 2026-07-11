// Conversation state contract for Maven follow-up intelligence.
//
// The client sends the last few turns (user query + the previous Maven answer JSON) in the
// /api/ask body as `conversationContext`. This module sanitizes that UNTRUSTED payload into a
// bounded, typed MavenConversationState. Everything is capped (turn count, string lengths,
// array sizes) so a hostile or buggy client cannot inflate memory or smuggle megabytes through
// the follow-up path. Pure and deterministic: no I/O, no Date, no randomness.

import type {
  AnswerType, ChartSpec, ChecklistItem, MavenAnswerMode, MavenBlock, MavenEvidenceSummary,
  MavenKeyData, MavenSource, MetricEvidence,
} from "./types";

export type MavenConversationTurn = {
  id: string;
  userQuery: string;
  normalizedQuery?: string;
  answerType?: AnswerType;
  answerMode?: MavenAnswerMode;
  headline?: string;
  summary?: string;
  keyData?: MavenKeyData[];
  blocks?: MavenBlock[];
  charts?: ChartSpec[];
  sources?: MavenSource[];
  bullets?: string[];
  evidence?: MavenEvidenceSummary;
  latestDataChecklist?: ChecklistItem[];
  limitations?: string[];
  resolvedSymbols?: string[];
  metricEvidence?: MetricEvidence[];
  disclaimer?: string;
  createdAt?: string;
};

export type MavenConversationState = {
  turns: MavenConversationTurn[];
  lastUserQuery?: string;
  lastAnswer?: MavenConversationTurn;
  lastAnswerType?: AnswerType;
  lastResolvedSymbols?: string[];
  lastTopic?: string;
  lastIntent?: string;
  lastMarketDate?: string;
};

// Hard caps on client-supplied context (payload abuse guard - see 08_Lessons security audit).
const MAX_TURNS = 3;
const MAX_STR = 600;
const MAX_QUERY = 400;
const MAX_BLOCKS = 8;
const MAX_CHARTS = 4;
const MAX_CHART_ROWS = 40;
const MAX_SOURCES = 10;
const MAX_KEYDATA = 8;
const MAX_LIMITATIONS = 6;
const MAX_BULLETS = 10;

const ANSWER_TYPES = new Set<AnswerType>([
  "greeting", "basic_concept", "market_mechanism", "current_market_research",
  "stock_comparison", "single_stock_research", "stock_leaderboard", "macro_sector_impact", "unsafe_advice",
  "out_of_scope", "unsupported_live_data", "deep_research_report", "comparison_research_report",
]);

// Answer types that carry real content a follow-up can refer back to. Greetings, refusals and
// scope cards are not "previous answers" for transformation purposes.
const SUBSTANTIVE_TYPES = new Set<AnswerType>([
  "basic_concept", "market_mechanism", "current_market_research", "stock_comparison",
  "single_stock_research", "stock_leaderboard", "macro_sector_impact", "deep_research_report", "comparison_research_report",
]);

function str(v: unknown, cap = MAX_STR): string | undefined {
  return typeof v === "string" && v.trim() ? v.slice(0, cap) : undefined;
}
function strArr(v: unknown, maxItems: number, cap = MAX_STR): string[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const out = v.filter((x) => typeof x === "string" && x.trim()).slice(0, maxItems).map((x) => (x as string).slice(0, cap));
  return out.length ? out : undefined;
}
function rec(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : undefined;
}

function sanitizeBlocks(v: unknown): MavenBlock[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const types = new Set(["DATA", "POINT", "MACRO", "CONTEXT", "RISK", "TAKEAWAY"]);
  const out: MavenBlock[] = [];
  for (const raw of v.slice(0, MAX_BLOCKS)) {
    const b = rec(raw);
    if (!b) continue;
    const title = str(b.title, 200);
    const body = str(b.body, MAX_STR * 2);
    if (!title && !body) continue;
    const t = typeof b.type === "string" && types.has(b.type.toUpperCase()) ? (b.type.toUpperCase() as MavenBlock["type"]) : "POINT";
    out.push({ type: t, title: title ?? "", body: body ?? "" });
  }
  return out.length ? out : undefined;
}

function sanitizeCharts(v: unknown): ChartSpec[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const types = new Set(["line", "bar", "stacked_bar", "comparison_table", "area", "flow"]);
  const out: ChartSpec[] = [];
  for (const raw of v.slice(0, MAX_CHARTS)) {
    const c = rec(raw);
    if (!c) continue;
    const title = str(c.title, 200);
    const type = typeof c.type === "string" && types.has(c.type) ? (c.type as ChartSpec["type"]) : undefined;
    if (!title || !type) continue;
    const data = Array.isArray(c.data)
      ? (c.data.filter((r) => r && typeof r === "object").slice(0, MAX_CHART_ROWS) as Record<string, unknown>[])
      : undefined;
    out.push({
      type, title, dataSource: str(c.dataSource, 100) ?? "previous_answer",
      xKey: str(c.xKey, 50), yKeys: strArr(c.yKeys, 6, 50), data,
    });
  }
  return out.length ? out : undefined;
}

function sanitizeSources(v: unknown): MavenSource[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const confs = new Set(["verified", "retrieved", "analysis_only", "unavailable"]);
  const out: MavenSource[] = [];
  for (const raw of v.slice(0, MAX_SOURCES)) {
    const s = rec(raw);
    if (!s) continue;
    const name = str(s.name, 150);
    if (!name) continue;
    // Client-supplied context can never mint trust: "verified" is reserved for sources the
    // server itself classified as official, so round-tripped sources cap at "retrieved".
    const rawConf = typeof s.confidence === "string" && confs.has(s.confidence) ? (s.confidence as NonNullable<MavenSource["confidence"]>) : "retrieved";
    out.push({
      name,
      title: str(s.title, 250),
      url: str(s.url, 500),
      date: str(s.date, 40),
      snippet: str(s.snippet, 300),
      type: str(s.type, 40),
      domain: str(s.domain, 100),
      confidence: rawConf === "verified" ? "retrieved" : rawConf,
    });
  }
  return out.length ? out : undefined;
}

function sanitizeKeyData(v: unknown): MavenKeyData[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const out: MavenKeyData[] = [];
  for (const raw of v.slice(0, MAX_KEYDATA)) {
    const d = rec(raw);
    if (!d) continue;
    const label = str(d.label, 100);
    const value = str(d.value, 100);
    if (!label || !value) continue;
    out.push({ label, value, change: str(d.change, 40) });
  }
  return out.length ? out : undefined;
}

function sanitizeTurn(raw: unknown, index: number): MavenConversationTurn | null {
  const t = rec(raw);
  if (!t) return null;
  const userQuery = str(t.userQuery, MAX_QUERY);
  if (!userQuery) return null;
  const a = rec(t.answer) ?? {};
  const answerType = typeof a.type === "string" && ANSWER_TYPES.has(a.type as AnswerType)
    ? (a.type as AnswerType)
    : typeof a.answerType === "string" && ANSWER_TYPES.has(a.answerType as AnswerType)
      ? (a.answerType as AnswerType)
      : undefined;
  return {
    id: str(t.id, 40) ?? `turn_${index}`,
    userQuery,
    answerType,
    headline: str(a.headline, 300),
    summary: str(a.summary, MAX_STR * 2),
    keyData: sanitizeKeyData(a.keyData),
    blocks: sanitizeBlocks(a.blocks),
    charts: sanitizeCharts(a.charts),
    sources: sanitizeSources(a.sources),
    bullets: strArr(a.bullets, MAX_BULLETS, 300),
    limitations: strArr(a.limitations, MAX_LIMITATIONS, 300),
    disclaimer: str(a.disclaimer, 300),
    createdAt: str(t.createdAt, 40),
  };
}

/** True when this turn holds an answer a follow-up can meaningfully refer back to. */
export function isSubstantiveTurn(turn: MavenConversationTurn | undefined): boolean {
  if (!turn) return false;
  if (turn.answerType && !SUBSTANTIVE_TYPES.has(turn.answerType)) return false;
  // With no declared type, require actual content so a bare {userQuery} can't fake context.
  return !!(turn.blocks?.length || turn.keyData?.length || turn.bullets?.length || (turn.headline && turn.summary));
}

// Transformation cards prefix their headline ("Bullet summary: X", "Chart view: X"); strip the
// prefix so chained follow-ups keep anchoring on the real topic X, not on "Bullet summary".
const TRANSFORM_HEADLINE_PREFIX = /^(bullet summary|chart view|table view|sources behind|in plain terms|short version)\s*[:—]\s*/i;

/** Topic label for the previous answer, used by the query rewriter ("the previous Maven answer about X"). */
function topicOf(turn: MavenConversationTurn | undefined): string | undefined {
  if (!turn) return undefined;
  const h = (turn.headline ?? "").replace(TRANSFORM_HEADLINE_PREFIX, "").replace(/[:—].*$/, "").trim();
  if (h && h.length >= 3) return h.slice(0, 80);
  return turn.userQuery.slice(0, 80);
}

/**
 * Most recent turn that carries the data a chart/table/source transformation needs. A bullet
 * summary of a market answer has no chart rows of its own - "now chart it" should reach back
 * to the market answer, not the summary card.
 */
export function findTurnWith(state: MavenConversationState, kind: "charts" | "sources"): MavenConversationTurn | undefined {
  for (let i = state.turns.length - 1; i >= 0; i--) {
    const t = state.turns[i];
    if (!isSubstantiveTurn(t)) continue;
    if (kind === "charts" && (t.charts?.some((c) => c.data?.length) || t.keyData?.length)) return t;
    if (kind === "sources" && t.sources?.length) return t;
  }
  return undefined;
}

/**
 * Build a bounded MavenConversationState from the untrusted `conversationContext` request field.
 * Accepts `{ turns: [{ id?, userQuery, answer?, createdAt? }] }` (newest turn LAST).
 */
export function buildConversationState(raw: unknown): MavenConversationState {
  const empty: MavenConversationState = { turns: [] };
  const ctx = rec(raw);
  if (!ctx || !Array.isArray(ctx.turns)) return empty;

  const turns = ctx.turns
    .slice(-MAX_TURNS)
    .map((t, i) => sanitizeTurn(t, i))
    .filter((t): t is MavenConversationTurn => t !== null);
  if (!turns.length) return empty;

  const last = turns[turns.length - 1];
  const lastSubstantive = [...turns].reverse().find(isSubstantiveTurn);
  return {
    turns,
    lastUserQuery: last.userQuery,
    lastAnswer: lastSubstantive,
    lastAnswerType: lastSubstantive?.answerType ?? last.answerType,
    lastTopic: topicOf(lastSubstantive),
  };
}
