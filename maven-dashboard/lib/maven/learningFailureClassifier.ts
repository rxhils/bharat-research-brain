// Maven Self-Learning Improvement Loop v1 - automatic failure classifier.
//
// Given a query + the /api/ask response (+ optional explicit user feedback), infer likely
// failure types. Deterministic and conservative: it should under-flag rather than invent
// failures, because every flagged event can become a regression eval case.

import type { MavenFailureType, MavenSeverity, MavenUserFeedback } from "./learningTypes";

// Advice ASSERTIONS (not neutral mentions). Kept in step with the output-side guard philosophy.
const ADVICE_ASSERT =
  /\b(strong buy|buy (?:now|today|this|the stock)|sell (?:now|today|this)|target price|price target|multibagger|guaranteed returns?|sure ?shot|book profit|accumulate now)\b/i;
// Provider/model/backend leakage that must never reach a user.
const PROVIDER_LEAK =
  /\b(deepseek|openai|gpt-?\d|anthropic|claude\b|ollama|large language model|\bllm\b|fallback answer|provider error|api key|stack ?trace)\b/i;
// A fiscal year at least two years stale, presented in visible text (FY20-FY24 while current is FY26).
const STALE_FY = /\bFY\s?(?:20|21|22|23|24)\b/i;
// Approximate / percentage figures that read like unsupported metrics.
const APPROX_METRIC = /(?:~\s?\d|(?:approx(?:imately)?|about|around|roughly)\s+\d|\b\d+(?:\.\d+)?\s?%)/i;

export interface ClassifyInput {
  query: string;
  /** MavenAnswer-shaped object; accessed defensively (field names vary across answer types). */
  response?: any;
  feedback?: MavenUserFeedback;
}

export interface ClassifyResult {
  failureTypes: MavenFailureType[];
  severity: MavenSeverity;
  explanation: string;
}

function visibleText(r: any): string {
  if (!r) return "";
  const parts: string[] = [];
  if (typeof r.headline === "string") parts.push(r.headline);
  if (typeof r.summary === "string") parts.push(r.summary);
  for (const b of Array.isArray(r.blocks) ? r.blocks : []) {
    if (typeof b?.text === "string") parts.push(b.text);
    if (Array.isArray(b?.items)) parts.push(b.items.filter((x: unknown) => typeof x === "string").join(" "));
  }
  for (const k of Array.isArray(r.keyData) ? r.keyData : []) {
    if (typeof k?.label === "string") parts.push(k.label);
    if (typeof k?.value === "string") parts.push(k.value);
  }
  return parts.join(" \n ");
}

function hasCitation(text: string): boolean {
  return /\[source:|https?:\/\//i.test(text);
}

export function classifyFailure(input: ClassifyInput): ClassifyResult {
  const { response, feedback } = input;
  const query = (input.query || "").toLowerCase();
  const types = new Set<MavenFailureType>();
  const notes: string[] = [];

  const answerType: string = String(response?.type ?? response?.answerType ?? "");
  const text = visibleText(response);
  const sources = Array.isArray(response?.sources) ? response.sources : undefined;
  const sourceCount =
    typeof response?.sourceCount === "number" ? response.sourceCount : sources?.length;
  const resolvedSymbols: string[] | undefined = Array.isArray(response?.resolvedSymbols)
    ? response.resolvedSymbols
    : undefined;

  // Reshape / follow-up request that fell through to the out_of_scope card.
  const reshapeAsk =
    /\b(bullet|summary|summari[sz]e|shorter|in a table|make it a table|chart it|show (?:me )?(?:the )?sources?|eli5|explain like)\b/i.test(
      query,
    );
  if (reshapeAsk && /out.?of.?scope/i.test(answerType)) {
    types.add("bad_followup_handling");
    types.add("out_of_scope_false_positive");
    notes.push("Reshape/follow-up request routed to out_of_scope.");
  }

  // Apparent single-stock intent but no symbol resolved.
  if (/single_stock|single stock|stock_research/i.test(answerType) && resolvedSymbols?.length === 0) {
    types.add("wrong_symbol");
    notes.push("Single-stock intent but no symbol resolved.");
  }

  // Thin sources on a research-style answer.
  if (
    /stock|single_stock|comparison|research/i.test(answerType) &&
    typeof sourceCount === "number" &&
    sourceCount < 5
  ) {
    types.add("thin_sources");
    notes.push(`Only ${sourceCount} source(s) on a research answer.`);
  }

  // Stale fiscal year presented as current.
  if (STALE_FY.test(text)) {
    types.add("stale_metric");
    notes.push("Visible text presents a 2+ year stale fiscal year.");
  }

  // Approximate metric with no visible citation.
  if (APPROX_METRIC.test(text) && !hasCitation(text)) {
    types.add("unsupported_metric");
    notes.push("Approximate/percentage metric without a visible source.");
  }

  // Provider/model/backend leakage (critical).
  if (PROVIDER_LEAK.test(text)) {
    types.add("provider_leakage");
    notes.push("Answer text leaks provider/model/backend terms.");
  }

  // Advice leakage (critical).
  if (ADVICE_ASSERT.test(text)) {
    types.add("advice_leakage");
    notes.push("Answer text asserts buy/sell/target advice.");
  }

  // Map explicit user feedback onto failure types.
  switch (feedback) {
    case "not_enough_sources":
      types.add("thin_sources");
      break;
    case "outdated":
      types.add("stale_metric");
      break;
    case "wrong":
      types.add("weak_reasoning");
      break;
    case "too_generic":
      types.add("weak_reasoning");
      break;
    default:
      break;
  }

  const failureTypes = [...types];
  const severity: MavenSeverity =
    types.has("advice_leakage") || types.has("provider_leakage")
      ? "critical"
      : types.has("stale_metric") || types.has("unsupported_metric") || types.has("wrong_symbol")
        ? "high"
        : types.has("thin_sources") || types.has("bad_followup_handling")
          ? "medium"
          : "low";

  return {
    failureTypes,
    severity,
    explanation:
      notes.join(" ") ||
      (feedback === "bad" ? "User marked the answer as bad." : "No automatic failure signal detected."),
  };
}
