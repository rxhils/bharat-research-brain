// Answer-mode routing: which PRESENTATION the user asked for. Modes never change evidence
// rules, refusals, or the freshness lock - a bullet summary of an answer contains exactly the
// facts that answer already carried. Deterministic, no token cost.

import type { MavenAnswerMode } from "./types";
import type { FollowUpIntent } from "./followUpIntentDetector";
import { normalizeForClassification } from "./queryNormalizer";

export type { MavenAnswerMode };

// Modes that are PURE transformations of the previous answer (no refetch, no new facts).
const TRANSFORM_MODES: ReadonlySet<MavenAnswerMode> = new Set([
  "bullet_summary", "short_answer", "table", "chart_first", "source_list", "eli5",
]);

export function isTransformationMode(mode: MavenAnswerMode): boolean {
  return TRANSFORM_MODES.has(mode);
}

/** Map a follow-up intent (plus the raw query as a tie-breaker) to an answer mode. */
export function routeAnswerMode(query: string, intent: FollowUpIntent): MavenAnswerMode {
  const n = normalizeForClassification(query);
  switch (intent.followUpType) {
    case "summarize_previous":
      return /\btl;?dr\b|\bshort|\bbrief|\bconcise\b|\bquick\b/.test(n) && !/\bbullet/.test(n) ? "short_answer" : "bullet_summary";
    case "format_transform":
      if (intent.requestedFormat === "simple") return "eli5";
      if (intent.requestedFormat === "chart") return "chart_first";
      if (intent.requestedFormat === "bullets") return "bullet_summary";
      if (intent.requestedFormat === "short") return "short_answer";
      return "table";
    case "source_followup": return "source_list";
    case "chart_followup": return "chart_first";
    case "expand_previous": return "deep_explanation";
    case "clarification": return "clarification_answer";
    case "entity_followup":
    case "time_followup":
      return "standard_card";
    default:
      return "standard_card";
  }
}
