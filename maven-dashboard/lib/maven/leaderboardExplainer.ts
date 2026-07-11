// "Why did these move?" - source-backed explanation of the PREVIOUS leaderboard's rows.
//
// Takes the previous turn's comparison-table rows (sanitized client context), retrieves news
// context for the top 3-5 names via the existing source waterfall, and builds a compact catalyst
// table. HARD RULES: catalysts are never invented - a name with no matching retrieved headline is
// explicitly marked "No verified company-specific catalyst found in current sources." The
// previous rows are never re-ranked or re-fetched (the user is asking about THOSE names).

import type { MavenAnswer, MavenBlock, MavenSource, ChartSpec, DisclaimerLevel } from "./types";
import type { MavenConversationTurn } from "./conversationState";
import { searchSources } from "./sourceSearch";
import { disclaimerText } from "./answerTypeRouter";

type LbRow = { stock: string; symbol?: string; move?: string };

const NO_CATALYST = "No verified company-specific catalyst found in current sources.";
const MAX_NAMES = 5;

function rowsFrom(turn: MavenConversationTurn): LbRow[] {
  for (const c of turn.charts ?? []) {
    if (c.type !== "comparison_table" || !c.data?.length) continue;
    const rows: LbRow[] = [];
    for (const r of c.data) {
      const stock = typeof r.stock === "string" ? r.stock : typeof r.symbol === "string" ? r.symbol : "";
      if (!stock) continue;
      rows.push({
        stock,
        symbol: typeof r.symbol === "string" ? r.symbol : undefined,
        move: typeof r["change%"] === "string" ? (r["change%"] as string) : undefined,
      });
    }
    if (rows.length) return rows;
  }
  return [];
}

/** Company token used to check that a retrieved headline is actually about this stock. */
function matchToken(row: LbRow): string {
  const first = (row.stock.split(/\s+/)[0] || "").toLowerCase();
  if (first.length >= 4) return first;
  return (row.symbol ?? first).toLowerCase();
}

/**
 * Build the explanation answer from the previous leaderboard turn. Returns null when the turn
 * carries no usable rows (caller falls through to the normal pipeline).
 */
export async function explainLeaderboard(turn: MavenConversationTurn, disclaimerLevel: DisclaimerLevel): Promise<MavenAnswer | null> {
  const rows = rowsFrom(turn).slice(0, MAX_NAMES);
  if (!rows.length) return null;

  const results = await Promise.all(rows.map(async (row) => {
    const srcs = await searchSources([`${row.stock} stock news today why moving`], { budget: 3 });
    const token = matchToken(row);
    const hit = token.length >= 3
      ? srcs.find((s) => `${s.title ?? ""}`.toLowerCase().includes(token))
      : undefined;
    return { row, hit };
  }));

  const tableRows: Record<string, unknown>[] = results.map(({ row, hit }) => ({
    stock: row.stock,
    move: row.move ?? "-",
    "likely catalyst": hit ? `${hit.title} [${hit.source}]` : NO_CATALYST,
    "source quality": hit ? ((hit.sourceRank ?? 9) <= 3 ? "official/exchange" : "news (retrieved)") : "-",
  }));

  const sources: MavenSource[] = [];
  for (const { hit } of results) {
    if (hit && hit.url && !sources.some((s) => s.url === hit.url)) {
      sources.push({ name: hit.source, title: hit.title, url: hit.url, date: hit.date ?? hit.published, confidence: hit.confidence ?? "retrieved" });
    }
  }
  sources.push({ name: "Maven analysis", type: "analysis", confidence: "analysis_only" });

  const found = results.filter((x) => x.hit).length;
  const disc = disclaimerText(disclaimerLevel);
  const chart: ChartSpec = {
    type: "comparison_table",
    title: "Why these moved — retrieved catalysts",
    dataSource: "Retrieved news/context sources",
    data: tableRows,
  };
  const blocks: MavenBlock[] = [
    { type: "DATA", title: "What the sources show", body: `Retrieved context for ${rows.length} of the previous top movers; a company-specific catalyst was found in current sources for ${found} of them. Where none was found, Maven says so rather than guessing.` },
    { type: "RISK", title: "Catalyst confidence", body: "Catalysts are retrieved headlines, not confirmed filings unless marked official. Single-day moves can also be flow- or sector-driven with no company-specific news." },
    { type: "TAKEAWAY", title: "Context", body: "Educational context on why these names moved - not a recommendation." + (disc ? " " + disc : "") },
  ];

  return {
    type: "stock_leaderboard",
    answerMode: "deep_explanation",
    headline: "Why these moved — retrieved catalysts for the top movers",
    summary: `Company-specific catalysts were checked for the ${rows.length} names in the previous leaderboard; found for ${found}, honestly marked as not found for the rest.`,
    keyData: [],
    charts: [chart],
    blocks,
    sources,
    followUps: ["Show top losers too", "Most active stocks today", "Summarize this in bullets"],
    disclaimer: disc,
    limitations: ["Catalysts are retrieved from open sources; where none was verified, Maven does not guess."],
  };
}
