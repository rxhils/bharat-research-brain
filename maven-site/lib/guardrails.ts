import type { ChatAnswer, AnswerBlock } from "./types";

// Post-generation compliance layer. Runs on EVERY answer (live DeepSeek or mock) so
// the same rules apply no matter where the text came from. Educational-only stance:
// neutralize hype/guarantee language and guarantee a risk + takeaway block exist.

// Hype / guarantee phrases -> neutral, education-safe rewrites. Order matters
// (longer phrases first so they win before their substrings).
const REWRITES: [RegExp, string][] = [
  [/\bguaranteed returns?\b/gi, "potential returns (never guaranteed)"],
  [/\bguaranteed\b/gi, "likely (not guaranteed)"],
  [/\bsure[\s-]?shot\b/gi, "research candidate"],
  [/\bmulti[\s-]?bagger\b/gi, "high-growth candidate"],
  [/\brisk[\s-]?free\b/gi, "lower-risk"],
  [/\bdouble (your |my )?money\b/gi, "significant upside (not assured)"],
  [/\bcan'?t lose\b/gi, "carries risk like any equity"],
  [/\bdefinitely (go|going) (up|higher)\b/gi, "could move (uncertain)"],
];

function scrub(text: string): string {
  let out = text;
  for (const [re, repl] of REWRITES) out = out.replace(re, repl);
  return out;
}

const GENERIC_RISK: AnswerBlock = {
  type: "risk",
  title: "Key risks",
  body: "Like any equity, this carries market, valuation and liquidity risk; flows and macro can reverse quickly. Cross-check claims against primary sources before acting on your own.",
};

const GENERIC_TAKEAWAY: AnswerBlock = {
  type: "takeaway",
  title: "Final view",
  body: "This is educational market context, not investment advice. Maven is not a SEBI-registered adviser or research analyst.",
};

export function sanitizeAnswer(a: ChatAnswer): ChatAnswer {
  const blocks = a.blocks.map((b) => ({ ...b, title: scrub(b.title), body: scrub(b.body) }));

  // Guarantee a risk block.
  if (!blocks.some((b) => b.type === "risk")) blocks.push(GENERIC_RISK);

  // Guarantee exactly one takeaway, and force it to the end.
  const nonTakeaway = blocks.filter((b) => b.type !== "takeaway");
  const takeaway = blocks.find((b) => b.type === "takeaway") ?? GENERIC_TAKEAWAY;
  const ordered = [...nonTakeaway, takeaway];

  return {
    ...a,
    headline: scrub(a.headline),
    summary: scrub(a.summary),
    verdict: a.verdict ? { ...a.verdict, label: scrub(a.verdict.label) } : a.verdict,
    blocks: ordered,
  };
}
