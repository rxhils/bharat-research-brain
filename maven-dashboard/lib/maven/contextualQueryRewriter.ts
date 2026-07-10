// Rewrites a contextual follow-up ("what does that mean for HDFC Bank?") into a standalone
// query the existing research pipeline can route and research. INTERNAL ONLY: the rewritten
// query is never shown to the user and never echoed in any answer field. Deterministic
// templates - no LLM call, no I/O.

import type { MavenConversationState } from "./conversationState";
import type { FollowUpIntent } from "./followUpIntentDetector";
import { normalizeForClassification } from "./queryNormalizer";
import { parseSectorScope } from "./sectorClassifier";

export type RewriteResult = {
  rewrittenQuery: string;
  usedContext: boolean;
};

// Strip referential lead-ins so the entity remains: "what does that mean for HDFC Bank?" -> "HDFC Bank".
const ENTITY_LEADIN = /^(and\s+)?(so\s+)?(what (does|would|will) (that|this|it) mean for|how (does|would|will) (that|this|it) (affect|impact|change)|what about|impact (on|for)|effect (on|for)|and for)\s+/i;

function entityFrom(query: string): string | undefined {
  const stripped = query.trim().replace(ENTITY_LEADIN, "").replace(/[?!.]+\s*$/, "").trim();
  if (stripped && stripped.length >= 2 && stripped.toLowerCase() !== query.trim().toLowerCase()) return stripped;
  return undefined;
}

function timePhraseFrom(query: string): string {
  const m = query.toLowerCase().match(/\b(last )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|this week|last week|this month|last month)\b/);
  return m ? m[0] : "today";
}

/**
 * Build the standalone query for a detected follow-up. `usedContext` is false when there was
 * nothing usable to anchor on (caller should fall back to the original query).
 */
export function rewriteContextualQuery(
  query: string,
  state: MavenConversationState,
  intent: FollowUpIntent,
): RewriteResult {
  const topic = state.lastTopic ?? state.lastUserQuery ?? "";
  const asIs: RewriteResult = { rewrittenQuery: query, usedContext: false };
  if (!intent.isFollowUp) return asIs;

  switch (intent.followUpType) {
    case "summarize_previous":
      return { rewrittenQuery: `Summarize the previous Maven answer${topic ? ` about ${topic}` : ""} in bullet points.`, usedContext: true };
    case "format_transform":
      return { rewrittenQuery: `Reformat the previous Maven answer${topic ? ` about ${topic}` : ""} (${intent.requestedFormat ?? "table"} view).`, usedContext: true };
    case "source_followup":
      return { rewrittenQuery: `Show the sources and evidence used in the previous Maven answer${topic ? ` about ${topic}` : ""}.`, usedContext: true };
    case "chart_followup":
      return { rewrittenQuery: `Create chart/table views from the previous Maven answer${topic ? ` about ${topic}` : ""} using available chart data and evidence.`, usedContext: true };
    case "expand_previous":
      // Routes back into the research pipeline; keep the previous subject so routing resolves it.
      if (/\brisks?\b/i.test(query) && topic) return { rewrittenQuery: `What should I watch on ${topic} - key risks in the Indian market context`, usedContext: true };
      return { rewrittenQuery: topic ? `Explain ${topic} in more detail with mechanisms and current evidence` : query, usedContext: !!topic };
    case "entity_followup": {
      const entity = entityFrom(query);
      if (!entity) {
        // Subjectless peer ask ("compare with closest peer") anchors on the previous topic.
        if (/\bpeers?\b|\bcompetitors?\b|\brivals?\b/i.test(query) && topic) {
          return { rewrittenQuery: `Compare ${topic} with its closest listed peer in India`, usedContext: true };
        }
        return asIs;
      }
      // The entity is the routing subject; the previous topic is the context it is read against.
      return { rewrittenQuery: `How does ${topic || "the current Indian market context"} affect ${entity} today`, usedContext: true };
    }
    case "time_followup": {
      const when = timePhraseFrom(query);
      const wantsRefresh = /\bupdate|latest|refresh\b/i.test(query);
      if (wantsRefresh) return { rewrittenQuery: topic ? `${topic} latest update today` : "Summarize Indian market today", usedContext: !!topic };
      return { rewrittenQuery: `Summarize Indian market ${when}`, usedContext: true };
    }
    case "clarification": {
      const m = query.trim().replace(/[?!.]+\s*$/, "").match(/(?:define|what is|what's|whats|meaning of|explain)\s+(.{2,60})$/i);
      const term = m?.[1]?.trim();
      if (term) return { rewrittenQuery: `What is ${term} in Indian markets?`, usedContext: true };
      return { rewrittenQuery: topic ? `Explain ${topic} in simple terms` : query, usedContext: !!topic };
    }
    case "explain_leaderboard":
      // Handled upstream in route.ts with the PREVIOUS leaderboard rows - never re-run as fresh
      // research (a re-ranked table could reshuffle the very names the user is asking about).
      return asIs;
    case "sector_movers_followup": {
      // Sector comes from the follow-up itself ("which bank stocks drove...") or, when absent
      // ("which stocks drove it?"), from the previous turn's query/topic.
      const norm = normalizeForClassification(query);
      const prevText = `${state.lastUserQuery ?? ""} ${state.lastTopic ?? ""}`;
      const sec = parseSectorScope(query, norm) ?? parseSectorScope(prevText, normalizeForClassification(prevText));
      const down = /\b(down|fell|fall|pulled|dragged|losers?)\b/i.test(query);
      const what = down ? "fell the most" : "moved the most";
      return {
        rewrittenQuery: sec
          ? `Show the top individual ${sec.label} stocks in the Nifty 500 that ${what} today in a table.`
          : `Show the top individual Nifty 500 stocks that ${what} today in a table.`,
        usedContext: true,
      };
    }
    default:
      return asIs;
  }
}

/**
 * Rewrite a "I mean individual stocks / not indices" correction into a standalone stock-leaderboard
 * query. Direction and count are inferred from the previous query so "top 5 ... increased the most"
 * -> gainers/5. The rewritten query re-enters routeAnswerType and lands on stock_leaderboard.
 */
export function rewriteMoversCorrection(query: string, state: MavenConversationState): string {
  const ctx = `${state.lastUserQuery ?? ""} ${query}`.toLowerCase();
  const verb = /\b(losers?|fell|fallen|declin|decreas|dropp?ed|worst|down)\b/.test(ctx) ? "fell the most"
    : /\b(most active|active|volume|traded)\b/.test(ctx) ? "were the most active"
    : "gained the most";
  const m = (state.lastUserQuery ?? "").match(/\btop\s+(\d{1,3})\b/) || query.match(/\btop\s+(\d{1,3})\b/);
  const n = m ? Math.max(1, Math.min(parseInt(m[1], 10), 25)) : 5;
  return `Show the top ${n} individual NSE stocks that ${verb} today in a table.`;
}
