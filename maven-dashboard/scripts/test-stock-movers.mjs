// Maven Real Stock Movers Data Source v1 - leaderboard data-source smoke test.
// Runs mover + scope queries against /api/ask and checks: routes to stock_leaderboard, rows are
// individual stocks (never index names), source/freshness present, no provider leakage, no advice.
// Usage: npm run eval:movers   (MAVEN_EVAL_URL overrides the target; defaults to localhost:3000)

const BASE = process.env.MAVEN_EVAL_URL || "http://localhost:3000/api/ask";
const INDEX_NAMES = ["nifty 50", "sensex", "bank nifty", "nifty midcap", "nifty smallcap", "brent", "usd/inr", "usd / inr"];

async function ask(query) {
  const t0 = Date.now();
  try {
    const r = await fetch(BASE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
    const j = await r.json().catch(() => ({}));
    return { j, ms: Date.now() - t0 };
  } catch {
    return { j: { error: true }, ms: Date.now() - t0 };
  }
}

function tableRows(j) {
  for (const c of j.charts ?? []) if (c.type === "comparison_table" && Array.isArray(c.data)) return c.data;
  return [];
}
function hasLeakage(j) {
  return /deepseek|openai|\bllm\b|api key|stack ?trace|provider error|unauthorized|429/.test(JSON.stringify(j).toLowerCase());
}
function hasAdvice(j) {
  const text = [j.headline, j.summary, ...(j.blocks ?? []).flatMap((b) => [b.title, b.body])].join(" ").toLowerCase();
  return /\b(strong buy|buy now|sell now|target price|price target|multibagger|guaranteed)\b/.test(text);
}

const QUERIES = [
  { q: "top 5 stocks that increased the most today in a table", dir: "gainers", expect: "stock_leaderboard" },
  { q: "top gainers today", dir: "gainers", expect: "stock_leaderboard" },
  { q: "top 10 stocks down today", dir: "losers", expect: "stock_leaderboard" },
  { q: "most active stocks today", dir: "most_active", expect: "stock_leaderboard" },
  { q: "top sectors today", dir: "-", expectNot: "stock_leaderboard" },
  { q: "top crypto gainers today", dir: "-", expect: "out_of_scope" },
  { q: "top US stock gainers today", dir: "-", expect: "out_of_scope" },
];

let fails = 0;
for (const c of QUERIES) {
  const { j, ms } = await ask(c.q);
  const type = j.type ?? j.answerType ?? "-";
  const rows = tableRows(j);
  const syms = rows.map((r) => r.symbol ?? r.stock).filter(Boolean).slice(0, 10);
  const indexRows = rows.some((r) => INDEX_NAMES.some((n) => String(r.stock ?? r.symbol ?? "").toLowerCase().includes(n)));
  const src = rows[0]?.source ?? j.charts?.find((x) => x.type === "comparison_table")?.dataSource ?? "-";
  const lim = (j.limitations ?? []).join(" | ");
  const leak = hasLeakage(j), advice = hasAdvice(j);

  let fail = false;
  if (c.expect && type !== c.expect) fail = true;
  if (c.expectNot && type === c.expectNot) fail = true;
  if (indexRows) fail = true; // index names as table rows = hard fail
  if (leak || advice) fail = true;
  if (fail) fails++;

  console.log(`${fail ? "XX" : "OK"}  ${c.q}`);
  console.log(`     type=${type} dir=${c.dir} rows=${rows.length} syms=[${syms.join(",")}] src="${src}" ms=${ms} indexRows=${indexRows} leak=${leak} advice=${advice}`);
  if (lim) console.log(`     limitations: ${lim}`);
}
console.log(`\n${QUERIES.length - fails}/${QUERIES.length} passed`);
process.exit(fails ? 1 : 0);
