// Follow-up intent detection: is the user modifying / referring to the previous Maven answer
// instead of asking a new market question? Deterministic regex classification (no token cost),
// same style as intentClassifier. The detector NEVER fires without a substantive previous
// answer, never claims advice asks (refusal wins upstream), and never claims queries that
// introduce their own market subject ("summarise fridays markets" is a fresh market question,
// "give me a bullet point summary" is a follow-up).

import { isAdviceRequest } from "../guard";
import { normalizeForClassification } from "./queryNormalizer";
import { isExplicitlyOutOfScope } from "./answerTypeRouter";
import { resolveStock } from "./stockResolver";
import { isSubstantiveTurn, type MavenConversationState } from "./conversationState";

export type FollowUpType =
  | "summarize_previous"
  | "expand_previous"
  | "format_transform"
  | "source_followup"
  | "chart_followup"
  | "entity_followup"
  | "time_followup"
  | "clarification"
  | "explain_leaderboard"
  | "sector_movers_followup"
  | "none";

export type RequestedFormat = "bullets" | "table" | "chart" | "short" | "detailed" | "simple" | "source_list";

export type FollowUpIntent = {
  isFollowUp: boolean;
  followUpType: FollowUpType;
  confidence: "high" | "medium" | "low";
  referencesPreviousAnswer: boolean;
  requestedFormat?: RequestedFormat;
};

const NONE: FollowUpIntent = { isFollowUp: false, followUpType: "none", confidence: "low", referencesPreviousAnswer: false };

// ---- pattern groups (tested against the normalized query) ----

const SOURCE_RE = /^(sources?|citations?|links?)[\s?!.]*$|\b(show|list|give me|see|view)\b.*\b(sources?|citations?|links?|evidence)\b|\bwhere (did|does) (this|that|it) come from\b|\bcite (this|that|it|your sources?)\b|\bwhich sources? did you (check|use)\b|\bsources? (used|behind|for (this|that))\b|\bwhat (data|information) (was|is) (missing|unavailable)\b|\bwhat('s| is) missing\b|\bwhich claims?\b.*\b(official|source|backed|verified)\b/;

const CHART_RE = /\b(chart|graph|plot|visuali[sz]e?)\b.*\b(it|this|that|them|view)\b|\b(show|see|view|put|give me)\b.*\bin a (chart|graph)\b|\bcompare\b.*\bin a (chart|graph)\b|^(chart|graph|plot|visuali[sz]e) (it|this|that)[\s?!.]*$|\bchart view\b|\bas a (chart|graph)\b/;

const SUMMARIZE_RE = /\bbullet[- ]?points?\b|\bbullet[- ]?point summary\b|\bsummarize (this|that|it|in bullets?|the (above|answer|previous))\b|^summarize[\s?!.]*$|^(quick )?summary[\s?!.]*$|\btl;?dr\b|\bkey points?( only)?\b|\bmain points?\b|\bmake (it|this|that) (short|shorter|brief|concise)\b|\bin short\b|\bshorten (it|this|that)\b|\bsummarize that\b|\bgive me (a |the )?(bullet|quick|short|brief)[- ]?(points?|summary|version|recap)\b/;

const FORMAT_RE = /\b(make|show|put|format|turn|convert|give me)\b.*\b(a |as a |into a |in a )?(table|checklist|list)\b|\bside[- ]by[- ]side\b|\bnumbers? only\b|\bas a table\b|\bin a table\b|\bin (a )?tabular (form|format)\b|\bmake (it|this|that) (simpler|easier|simple)\b|\bsimplify (it|this|that)?\b|\bexplain (it |this |that )?(simply|like i'?m (new|five|5)|in simple (terms|words|language))\b|\beli5\b/;

const EXPAND_RE = /\b(explain|tell me) more\b|\bgo deeper\b|\bexpand (on )?(this|that|it)?\b|\b(more|extra|full|deeper) detail(s)?\b|\bwhy exactly\b|\bexplain the mechanism\b|\bbreak (it|this|that) down\b|\belaborate\b|\bin (more )?depth\b|\bwhat are the (key |main )?risks?\b|\bkey risks?\b/;

// "Why did these move?" after a leaderboard answer - explain the PREVIOUS rows, never re-rank.
const EXPLAIN_LB_RE = /\bwhy (did|do|are|were) (these|those|they)\b|\bwhy did these\b|\bexplain (these|those|the (top )?(gainers?|losers?|movers?))\b|\bwhat(?:'s| is) driving these\b|\bwhy are these (stocks? )?(up|down|moving|falling|rising)\b/;

// "Which stocks drove it / the move?" after a market/sector answer - rewrite to a leaderboard.
const DROVE_RE = /\bwhich [^.?!]{0,20}stocks?\b[^.?!]{0,30}\b(drove|led|pulled|pushed|caused|behind)\b|\bwhich stocks? moved\b|\bwho drove the (move|rally|fall)\b/;

// Subjectless peer-comparison ask ("compare with closest peer") - the peer of the PREVIOUS answer.
const PEER_RE = /\bcompare\b.*\b(peers?|competitors?|rivals?)\b|\bclosest peer\b|\bvs (its )?peers?\b/;

const ENTITY_RE = /\bwhat (does|would|will) (that|this|it) mean for\b|\bhow (does|would|will) (that|this|it) (affect|impact|change)\b|\bwhat about\b|\b(impact|effect) (on|for)\b|\bwhich (sectors?|stocks?|banks?|companies)\b.*\b(benefit|gain|lose|suffer|win)\b|\band (for|what about)\b|\bdoes (that|this|it) (help|hurt)\b/;

const TIME_RE = /\bwhat about (last )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|this week|last week|this month|last month)\b|\bwhat (happened|changed) (yesterday|today|last week|this week|on (monday|tuesday|wednesday|thursday|friday))\b|\bupdate (this|that|it)( with)?( the)?( latest| latest data| new data)?\b|\bwith (the )?latest (data|numbers)\b|\brefresh (this|that|it)\b|\bsummarize (last|this) (week|month)\b|\b(show|see|get)?\s*(the )?latest (filings?|announcements?|results?|updates?|news)\b/;

const CLARIFY_RE = /\bwhat do you mean( by (that|this|it))?\b|\bexplain (that|this) term\b|\bwhy does (that|this|it) matter\b|\bwhat (is|does) (that|this) (mean|refer to)\b|\bi (don'?t|do not) (understand|get) (that|this|it)\b/;

const DEFINE_RE = /^(define|what is|what's|whats|meaning of)\s+(.{1,60})[\s?!.]*$/;

// Words that indicate the query brings its own market subject (so it is a fresh question, not
// a pure transformation of the previous answer). Stock names are checked via resolveStock.
const SUBJECT_RE = /\b(market|nifty|sensex|midcap|smallcap|dalal street|india|indian|nse|bse|sebi|rbi|crude|oil|rupee|usd ?inr|g-?sec|yield|repo|inflation|cpi|wpi|gdp|fii|dii|monsoon|banks?|financials|pharma|auto|fmcg|metals?|realty|energy|defence|railway|it sector|ipo|earnings|results)\b/;

function hasOwnSubject(normalized: string, original: string): boolean {
  return SUBJECT_RE.test(normalized) || !!resolveStock(original);
}

function requestedFormatOf(n: string): RequestedFormat | undefined {
  if (/\btable\b|\bside[- ]by[- ]side\b|\btabular\b/.test(n)) return "table";
  if (/\bchart\b|\bgraph\b|\bplot\b|\bvisuali[sz]e?\b/.test(n)) return "chart";
  if (/\bbullet/.test(n)) return "bullets";
  if (/\bsources?\b|\bcitations?\b|\blinks?\b|\bevidence\b/.test(n)) return "source_list";
  if (/\bsimpl|\beli5\b|\blike i'?m (new|five|5)\b/.test(n)) return "simple";
  if (/\bshort|\bbrief|\bconcise\b|\btl;?dr\b|\bquick\b/.test(n)) return "short";
  if (/\bdetail|\bdeeper\b|\bdepth\b/.test(n)) return "detailed";
  return undefined;
}

/**
 * Follow-up-shaped query with no market subject of its own ("give me a bullet point summary",
 * "sources?"). Used when there is NO previous answer: these should get a gentle "ask a market
 * question first" card, never the out_of_scope redirect.
 */
export function looksLikeBareFollowUp(query: string): boolean {
  const original = (query || "").trim();
  if (!original || isAdviceRequest(original) || isExplicitlyOutOfScope(original)) return false;
  const n = normalizeForClassification(original);
  if (hasOwnSubject(n, original)) return false;
  return SOURCE_RE.test(n) || CHART_RE.test(n) || SUMMARIZE_RE.test(n) || FORMAT_RE.test(n) || EXPAND_RE.test(n) || CLARIFY_RE.test(n) || EXPLAIN_LB_RE.test(n);
}

// User correcting a prior index/market answer to ask for INDIVIDUAL stocks instead of indices:
// "im talking about individual stocks", "not indices", "I mean companies", "actual shares",
// "not the market, the stocks". Tested against the RAW query (the normalizer collapses
// "individual stocks" -> "stocks", which would lose the correction signal).
const CORRECTION_RE = /\b(individual (stocks?|equit\w+|companies|shares?)|not (the )?indic\w*|not nifty|not sensex|not the market,?\s*(the )?stocks?|actual (stocks?|shares?|companies)|i(?:'m| am)?\s*(?:talking about|mean|meant|asked for|said|want)\s+(?:individual\s+)?(?:stocks?|companies|shares?|equit\w+)|give me (?:actual|individual|real)\s+(?:stocks?|shares?|companies)|listed companies|stocks?,? not (?:the )?(?:index|indices|nifty|sensex|market))\b/i;

/** True when the message corrects a previous index/market answer toward individual stocks. */
export function isMoversCorrection(query: string): boolean {
  const original = (query || "").trim();
  if (!original || isAdviceRequest(original) || isExplicitlyOutOfScope(original)) return false;
  return CORRECTION_RE.test(original.toLowerCase());
}

/**
 * Classify whether `query` is a follow-up on the previous Maven answer.
 * Fires only when the conversation state carries a substantive previous answer.
 */
export function detectFollowUpIntent(query: string, state: MavenConversationState): FollowUpIntent {
  const original = (query || "").trim();
  if (!original) return NONE;
  const hasPrev = isSubstantiveTurn(state.lastAnswer);
  if (!hasPrev) return NONE;

  // Safety and scope always win: advice asks are refused upstream, explicit non-India subjects
  // stay out_of_scope even mid-conversation ("US market summary Friday").
  if (isAdviceRequest(original)) return NONE;
  if (isExplicitlyOutOfScope(original)) return NONE;

  const n = normalizeForClassification(original);
  const subject = hasOwnSubject(n, original);
  const short = n.split(/\s+/).length <= 12;
  const fmt = requestedFormatOf(n);

  // Leaderboard-aware follow-ups may carry their own subject words ("which bank stocks drove
  // Bank Nifty?"), so they are checked BEFORE the no-subject transformation gate.
  if (EXPLAIN_LB_RE.test(n) && state.lastAnswerType === "stock_leaderboard") {
    return { isFollowUp: true, followUpType: "explain_leaderboard", confidence: "high", referencesPreviousAnswer: true };
  }
  if (DROVE_RE.test(n)) {
    return { isFollowUp: true, followUpType: "sector_movers_followup", confidence: short ? "high" : "medium", referencesPreviousAnswer: true };
  }

  // Pure transformations of the previous answer: only when the query does NOT introduce its own
  // market subject ("summarise fridays markets" must stay a fresh market-summary question).
  if (!subject) {
    if (SOURCE_RE.test(n)) return { isFollowUp: true, followUpType: "source_followup", confidence: "high", referencesPreviousAnswer: true, requestedFormat: "source_list" };
    if (CHART_RE.test(n)) return { isFollowUp: true, followUpType: "chart_followup", confidence: "high", referencesPreviousAnswer: true, requestedFormat: "chart" };
    if (TIME_RE.test(n)) return { isFollowUp: true, followUpType: "time_followup", confidence: short ? "high" : "medium", referencesPreviousAnswer: true };
    if (SUMMARIZE_RE.test(n)) return { isFollowUp: true, followUpType: "summarize_previous", confidence: "high", referencesPreviousAnswer: true, requestedFormat: fmt ?? "bullets" };
    if (FORMAT_RE.test(n)) return { isFollowUp: true, followUpType: "format_transform", confidence: "high", referencesPreviousAnswer: true, requestedFormat: fmt ?? "table" };
    if (PEER_RE.test(n)) return { isFollowUp: true, followUpType: "entity_followup", confidence: "medium", referencesPreviousAnswer: true };
    if (EXPAND_RE.test(n)) return { isFollowUp: true, followUpType: "expand_previous", confidence: "high", referencesPreviousAnswer: true, requestedFormat: "detailed" };
    if (CLARIFY_RE.test(n)) return { isFollowUp: true, followUpType: "clarification", confidence: "high", referencesPreviousAnswer: true };
    // "define X" / "what is X" counts as clarification only when X appears in the previous
    // answer's text - otherwise it is an ordinary basic_concept question.
    const def = n.match(DEFINE_RE);
    if (def) {
      const term = def[2].trim().toLowerCase();
      const prevText = JSON.stringify(state.lastAnswer ?? {}).toLowerCase();
      if (term.length >= 2 && prevText.includes(term)) {
        return { isFollowUp: true, followUpType: "clarification", confidence: "medium", referencesPreviousAnswer: true };
      }
    }
    return NONE;
  }

  // Queries WITH a subject can still be follow-ups when they use referential phrasing:
  // "what does that mean for HDFC Bank?", "what about banks?", "impact on NBFCs?".
  // A named driver ("... from softer crude") means the question is self-contained - fresh pipeline.
  if (ENTITY_RE.test(n) && !/\bfrom\b/.test(n)) {
    return { isFollowUp: true, followUpType: "entity_followup", confidence: short ? "high" : "medium", referencesPreviousAnswer: true };
  }
  // Formatting request that names the same subject as the previous answer ("show the crude
  // impact in a table") - treat as transformation when the subject already appeared previously.
  if ((SUMMARIZE_RE.test(n) || FORMAT_RE.test(n) || CHART_RE.test(n)) && short) {
    const prevText = `${state.lastAnswer?.headline ?? ""} ${state.lastAnswer?.summary ?? ""} ${state.lastUserQuery ?? ""}`.toLowerCase();
    const subjectWords = n.match(SUBJECT_RE);
    if (subjectWords && prevText.includes(subjectWords[0])) {
      const type: FollowUpType = CHART_RE.test(n) ? "chart_followup" : SUMMARIZE_RE.test(n) ? "summarize_previous" : "format_transform";
      return { isFollowUp: true, followUpType: type, confidence: "medium", referencesPreviousAnswer: true, requestedFormat: fmt };
    }
  }
  return NONE;
}
