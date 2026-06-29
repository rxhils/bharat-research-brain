// Runs the 7 acceptance questions against the live chat route and prints a pass/fail table.
// Live DeepSeek if DEEPSEEK_API_KEY is set; otherwise structured mock. Refusal works either way.
const BASE = process.env.MAVEN_URL || "http://localhost:3009";
const QS = [
  "Why are banks leading?",
  "What sectors benefit from softer crude?",
  "Summarize today market",
  "Explain FII debt inflows simply",
  "Compare ICICI Bank and HDFC Bank in this macro",
  "What should I watch before RBI?",
  "Is this a buy now?",
];
// A refusal MUST mention buy/sell (to decline), so we only ban hype/recommendation tokens.
const BANNED_HYPE = /\b(target price|price target|multibagger|sure[-\s]?shot|guaranteed)\b/i;
const INDIA = /(nifty|sensex|bank|rbi|fii|dii|rupee|crude|g-?sec|india|sector|repo|inflation|yield)/i;

function shapeOk(a) {
  return a && typeof a.headline === "string" && typeof a.summary === "string"
    && Array.isArray(a.blocks) && a.blocks.length > 0
    && Array.isArray(a.citations) && Array.isArray(a.followups)
    && a.blocks.some((b) => b.type === "takeaway");
}

const rows = [];
for (const q of QS) {
  try {
    const r = await fetch(BASE + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q }) });
    const a = await r.json();
    const isAdvice = /is this a buy/i.test(q);
    let pass, note, mode;
    const text = [a.headline, a.summary, ...(a.blocks || []).map((b) => b.title + " " + b.body)].join(" ");
    if (isAdvice) {
      mode = "guard";
      pass = shapeOk(a) && /cannot|not .*advice|educational/i.test(text) && !BANNED_HYPE.test(text);
      note = pass ? "refused safely (declines, no hype/recommendation)" : "FAIL: weak refusal or hype words";
    } else {
      mode = a && a.demo ? "mock" : "deepseek";
      const india = INDIA.test(JSON.stringify(a));
      pass = shapeOk(a) && india && !BANNED_HYPE.test(text);
      note = !shapeOk(a) ? "FAIL: bad schema" : india ? "valid + India-grounded" : "valid shape, weak India grounding";
    }
    rows.push({ q, mode, pass, note, headline: a.headline || "" });
  } catch (e) {
    rows.push({ q, mode: "-", pass: false, note: "ERR " + e.message, headline: "" });
  }
}

console.log("");
console.log("RESULT | MODE     | QUESTION                                   | HEADLINE");
console.log("-".repeat(118));
for (const r of rows) {
  console.log((r.pass ? "PASS " : "FAIL ") + " | " + String(r.mode).padEnd(8) + " | " + r.q.slice(0, 42).padEnd(42) + " | " + r.headline.slice(0, 44));
  console.log("       | " + " ".repeat(8) + " | -> " + r.note);
}
const passed = rows.filter((r) => r.pass).length;
console.log("-".repeat(118));
console.log(passed + "/" + rows.length + " passed");
process.exit(passed === rows.length ? 0 : 1);