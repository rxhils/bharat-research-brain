// Pure transformations of the PREVIOUS Maven answer into a new presentation. Hard rules:
// - Never add a fact, number, or source that the previous answer did not already carry.
// - Preserve the previous answer's limitations and citation trail.
// - Never make old data look current: every output carries the "based on the previous
//   Maven answer" footer, and preserved limitations keep their timeframe caveats.
// - Refusals and scope cards are never transformed (route.ts gates on substantive turns).
// Deterministic, no LLM call, no I/O - a transformation cannot hallucinate.

import type { ChartSpec, MavenAnswer, MavenSource } from "./types";
import type { MavenConversationTurn } from "./conversationState";
import { chipsForAnswerType } from "./followUpChips";

const FOOTER = "Based on the previous Maven answer. Educational market context, not investment advice.";
const MAX_BULLETS = 7;

function firstSentences(text: string | undefined, count = 1, cap = 220): string {
  if (!text) return "";
  const parts = text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, count);
  const joined = parts.join(" ").trim();
  return joined.length > cap ? joined.slice(0, cap - 1).trimEnd() + "…" : joined;
}

// Keep chained transformations anchored on the real subject: "Bullet summary: Crude oil" must
// yield "Chart view: Crude oil", never "Chart view: Bullet summary".
const TRANSFORM_HEADLINE_PREFIX = /^(bullet summary|chart view|table view|sources behind|in plain terms|short version)\s*[:—]\s*/i;

function topicLabel(prev: MavenConversationTurn): string {
  const h = (prev.headline ?? "").replace(TRANSFORM_HEADLINE_PREFIX, "").replace(/[:—].*$/, "").trim();
  return h || "the previous answer";
}

function baseAnswer(prev: MavenConversationTurn): MavenAnswer {
  return {
    type: prev.answerType,
    headline: "", summary: "",
    keyData: [], charts: [], blocks: [],
    sources: prev.sources ?? [],
    followUps: chipsForAnswerType(prev.answerType),
    disclaimer: FOOTER,
    limitations: prev.limitations?.length ? [...prev.limitations] : undefined,
  };
}

/** Bullet candidates drawn strictly from the previous answer's own content. */
function bulletCandidates(prev: MavenConversationTurn): string[] {
  const out: string[] = [];
  for (const d of prev.keyData ?? []) out.push(`${d.label}: ${d.value}${d.change ? ` (${d.change})` : ""}`);
  for (const b of prev.blocks ?? []) {
    const body = firstSentences(b.body, 1);
    if (b.title && body) out.push(`${b.title} — ${body}`);
    else if (b.title || body) out.push(b.title || body);
  }
  if (!out.length && prev.bullets?.length) out.push(...prev.bullets);
  if (!out.length && prev.summary) {
    out.push(...prev.summary.split(/(?<=[.!?])\s+/).filter((s) => s.trim().length > 15).map((s) => s.trim()));
  }
  return out.slice(0, MAX_BULLETS);
}

export function transformToBulletSummary(prev: MavenConversationTurn): MavenAnswer {
  const bullets = bulletCandidates(prev);
  return {
    ...baseAnswer(prev),
    answerMode: "bullet_summary",
    headline: `Bullet summary: ${topicLabel(prev)}`,
    summary: "Key points from the previous Maven answer.",
    bullets: bullets.length ? bullets : [firstSentences(prev.summary, 2) || "The previous answer carried no summarizable detail."],
  };
}

export function transformToShortAnswer(prev: MavenConversationTurn): MavenAnswer {
  return {
    ...baseAnswer(prev),
    answerMode: "short_answer",
    headline: prev.headline ?? "Short version of the previous answer",
    summary: firstSentences(prev.summary, 2) || firstSentences(bulletCandidates(prev).join(". "), 2),
    bullets: bulletCandidates(prev).slice(0, 3),
  };
}

export function transformToTable(prev: MavenConversationTurn): MavenAnswer {
  // Prefer a table the previous answer already computed; otherwise tabulate its own keyData/blocks.
  const existing = (prev.charts ?? []).find((c) => c.type === "comparison_table" && c.data?.length);
  let chart: ChartSpec | null = existing ?? null;
  if (!chart && prev.keyData?.length) {
    chart = {
      type: "comparison_table", title: `Table view: ${topicLabel(prev)}`, dataSource: "previous_answer",
      data: prev.keyData.map((d) => ({ metric: d.label, value: d.value, change: d.change ?? "-" })),
    };
  }
  if (!chart && prev.blocks?.length) {
    chart = {
      type: "comparison_table", title: `Table view: ${topicLabel(prev)}`, dataSource: "previous_answer",
      data: prev.blocks.map((b) => ({ aspect: b.title, detail: firstSentences(b.body, 1, 160) })),
    };
  }
  const base = baseAnswer(prev);
  if (!chart) {
    return {
      ...base, answerMode: "table",
      headline: `Table view: ${topicLabel(prev)}`,
      summary: "The previous answer did not carry table-ready data, so here are its key points instead.",
      bullets: bulletCandidates(prev),
      limitations: [...(base.limitations ?? []), "The previous answer had no structured data rows to tabulate."],
    };
  }
  return {
    ...base, answerMode: "table",
    headline: `Table view: ${topicLabel(prev)}`,
    summary: firstSentences(prev.summary, 1) || "Structured view of the previous Maven answer.",
    charts: [chart],
  };
}

export function transformToSourceList(prev: MavenConversationTurn): MavenAnswer {
  const sources: MavenSource[] = prev.sources ?? [];
  const base = baseAnswer(prev);
  const bullets = sources
    .filter((s) => s.name || s.title)
    .map((s) => `${s.name}${s.title && s.title !== s.name ? ` — ${s.title}` : ""}${s.date ? ` (${s.date})` : ""}${s.confidence ? ` [${s.confidence === "analysis_only" ? "Maven analysis" : s.confidence}]` : ""}`)
    .slice(0, 10);
  return {
    ...base,
    answerMode: "source_list",
    headline: `Sources behind: ${topicLabel(prev)}`,
    summary: sources.length
      ? `The previous answer drew on ${sources.length} source${sources.length === 1 ? "" : "s"}, listed below with confidence levels.`
      : "The previous answer did not carry retrievable source links.",
    bullets,
    followUps: chipsForAnswerType(prev.answerType, true),
    limitations: sources.length ? base.limitations : [...(base.limitations ?? []), "No source links were attached to the previous answer."],
  };
}

export function transformToChartFirst(prev: MavenConversationTurn): MavenAnswer {
  const withData = (prev.charts ?? []).filter((c) => c.data?.length);
  if (!withData.length) {
    // Honest fallback: tabulate what exists rather than inventing chart data.
    const t = transformToTable(prev);
    return {
      ...t, answerMode: "chart_first",
      headline: `Chart view: ${topicLabel(prev)}`,
      limitations: [...(t.limitations ?? []), "The previous answer carried no chart-ready series; showing its structured data instead."],
    };
  }
  return {
    ...baseAnswer(prev),
    answerMode: "chart_first",
    headline: `Chart view: ${topicLabel(prev)}`,
    summary: firstSentences(prev.summary, 1) || "Chart views from the previous Maven answer.",
    charts: withData,
    keyData: prev.keyData ?? [],
  };
}

export function transformToSimpleExplanation(prev: MavenConversationTurn): MavenAnswer {
  const bullets = (prev.blocks ?? [])
    .filter((b) => b.body)
    .map((b) => `${b.title ? b.title + ": " : ""}${firstSentences(b.body, 1)}`)
    .slice(0, MAX_BULLETS);
  return {
    ...baseAnswer(prev),
    answerMode: "eli5",
    headline: `In plain terms: ${topicLabel(prev)}`,
    summary: firstSentences(prev.summary, 2) || "A simpler read of the previous Maven answer.",
    bullets: bullets.length ? bullets : bulletCandidates(prev),
  };
}
