// Maven Self-Learning Improvement Loop v1 - shared type contract.
//
// This is a SUPERVISED learning/eval loop, NOT fine-tuning and NOT autonomous
// self-modifying production code. Flow:
//   observe -> score -> log -> classify failure -> suggest eval case -> human approves -> fix -> ship
//
// No secrets are ever stored. No production behaviour changes without approval.

export type MavenFailureType =
  | "wrong_route"
  | "out_of_scope_false_positive"
  | "bad_followup_handling"
  | "wrong_symbol"
  | "thin_sources"
  | "stale_metric"
  | "unsupported_metric"
  | "fake_catalyst"
  | "wrong_chart"
  | "weak_reasoning"
  | "missing_sources"
  | "provider_leakage"
  | "advice_leakage"
  | "bad_ui_render"
  | "slow_response"
  | "other";

export type MavenUserFeedback =
  | "good"
  | "bad"
  | "too_generic"
  | "outdated"
  | "wrong"
  | "not_enough_sources";

export type MavenLearningEventStatus =
  | "new"
  | "triaged"
  | "converted_to_eval"
  | "fixed"
  | "ignored";

export type MavenSeverity = "low" | "medium" | "high" | "critical";

export interface MavenLearningEvent {
  id: string;
  timestamp: string;
  userQuery: string;
  conversationContext?: unknown;
  answerType?: string;
  headline?: string;
  summary?: string;
  resolvedSymbols?: string[];
  sourceCount?: number;
  clickableSourceCount?: number;
  chartCount?: number;
  limitations?: string[];
  userFeedback?: MavenUserFeedback;
  failureTypes: MavenFailureType[];
  failureExplanation?: string;
  expectedBehavior?: string;
  severity: MavenSeverity;
  status: MavenLearningEventStatus;
}

export type MavenSuggestedFixType =
  | "routing_rule"
  | "query_normalization"
  | "source_search"
  | "stock_resolver"
  | "metric_validator"
  | "answer_generator"
  | "ui_render"
  | "eval_case"
  | "guardrail";

export interface MavenLearningSuggestion {
  id: string;
  eventIds: string[];
  suggestedFixType: MavenSuggestedFixType;
  summary: string;
  proposedEvalCase?: unknown;
  requiresApproval: boolean;
}
