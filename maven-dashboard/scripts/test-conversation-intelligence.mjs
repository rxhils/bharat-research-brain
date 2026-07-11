// Maven Conversation Intelligence + Sector Movers v1 - multi-turn flow test.
// Each flow: initial query -> follow-up with conversationContext (same shape the frontend sends).
// Checks routing, previous-context use, sector scoping, leakage/advice guards, and that no valid
// follow-up ever gets the "Maven focuses on Indian markets" scope card.
// Usage: npm run eval:conversation   (MAVEN_EVAL_URL overrides target; default localhost:3000)

const BASE = process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask";

async function ask(query, conversationContext) {
  const t0 = Date.now();
  const body = conversationContext ? { query, conversationContext } : { query };
  try {
    const r = await fetch(BASE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    return { j, ms: Date.now() - t0 };
  } catch {
    return { j: { error: true }, ms: Date.now() - t0 };
  }
}

const text = (j) => JSON.stringify(j).toLowerCase();
const leak = (j) => /deepseek|openai|\bllm\b|api key|stack ?trace|provider error|searxng|scraper/.test(text(j));
const advice = (j) => {
  const t = [j.headline, j.summary, ...(j.blocks ?? []).flatMap((b) => [b.title, b.body]), ...(j.bullets ?? [])].join(" ").toLowerCase();
  return /\b(strong buy|buy now|sell now|target price|price target|multibagger|guaranteed)\b/.test(t);
};
const scopeCard = (j) => /focuses on indian markets/.test(text(j));
const tableRows = (j) => { for (const c of j.charts ?? []) if (c.type === "comparison_table" && Array.isArray(c.data)) return c.data; return []; };

// Flow spec: [initial, followUp, expectations for the FOLLOW-UP answer]
const FLOWS = [
  { initial: "top gainers today", follow: "why did these move?",
    expect: { type: "stock_leaderboard", mode: "deep_explanation", table: true }, name: "explain leaderboard" },
  { initial: "top bank gainers today", follow: "give me a bullet summary",
    expect: { mode: "bullet_summary", bullets: true }, name: "bullet summary of sector leaderboard" },
  { initial: "what happened in the market today?", follow: "which individual stocks drove the move?",
    expect: { type: "stock_leaderboard", table: true }, name: "stocks-drove-the-move follow-up" },
  { initial: "why are banks leading today?", follow: "what does that mean for HDFC Bank?",
    expect: { type: "single_stock_research" }, name: "entity follow-up (HDFC Bank)" },
  { initial: "top sectors today", follow: "I mean individual stocks",
    expect: { type: "stock_leaderboard", table: true }, name: "individual-stocks correction" },
];

let fails = 0;
for (const f of FLOWS) {
  const first = await ask(f.initial);
  const ctx = { turns: [{ id: "t1", userQuery: f.initial, answer: first.j }] };
  const { j, ms } = await ask(f.follow, ctx);
  const type = j.type ?? j.answerType ?? "-";
  const mode = j.answerMode ?? "-";
  const rows = tableRows(j);
  const bullets = (j.bullets ?? []).length;
  const lims = (j.limitations ?? []).join(" | ");
  const problems = [];
  if (f.expect.type && type !== f.expect.type) problems.push(`type=${type} want=${f.expect.type}`);
  if (f.expect.mode && mode !== f.expect.mode) problems.push(`mode=${mode} want=${f.expect.mode}`);
  if (f.expect.table && rows.length === 0) problems.push("no table rows");
  if (f.expect.bullets && bullets === 0) problems.push("no bullets");
  if (scopeCard(j)) problems.push("scope card on a valid follow-up");
  if (leak(j)) problems.push("provider leakage");
  if (advice(j)) problems.push("advice leakage");
  const fail = problems.length > 0;
  if (fail) fails++;
  const firstType = first.j.type ?? first.j.answerType ?? "-";
  console.log(`${fail ? "XX" : "OK"}  [${f.name}] "${f.initial}" -> "${f.follow}"`);
  console.log(`     initial=${firstType}  follow: type=${type} mode=${mode} rows=${rows.length} bullets=${bullets} sources=${(j.sources ?? []).length} ms=${ms}`);
  if (lims) console.log(`     limitations: ${lims}`);
  if (fail) console.log(`     PROBLEMS: ${problems.join("; ")}`);
}
console.log(`\n${FLOWS.length - fails}/${FLOWS.length} flows passed`);
process.exit(fails ? 1 : 0);
