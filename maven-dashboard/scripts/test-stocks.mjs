// Maven Stock Intelligence v1 acceptance. Hits local /api/ask with single-stock queries.
const BASE = process.env.MAVEN_URL || "http://localhost:3000";
const RESOLVE = { reliance: "RELIANCE.NS", "hdfc bank": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS", "tata motors": "TATAMOTORS.NS", zomato: "ZOMATO.NS" };
const QUERIES = [
  "Why is Reliance moving today?",
  "Why is HDFC Bank down today?",
  "Explain ICICI Bank today.",
  "What changed in Tata Motors?",
  "Why is Zomato falling?",
  "Compare HDFC Bank and ICICI Bank",
  "Should I buy Reliance?",
];
const FORBIDDEN = ["deepseek","openai","anthropic","llm","api key","backend","provider","tavily error","yahoo error","env","fallback","mock","preview","demo","server-side key"];
function leak(o){ const s=JSON.stringify(o); return FORBIDDEN.filter(t=>new RegExp("\\b"+t.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\b","i").test(s)); }
function resolved(q){ const l=q.toLowerCase(); for(const k of Object.keys(RESOLVE)) if(l.includes(k)) return RESOLVE[k]; return "-"; }

let anyLeak=false;
for (const q of QUERIES) {
  try {
    const r = await fetch(BASE+"/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:q})});
    const a = await r.json();
    const text = JSON.stringify(a).toLowerCase();
    const type = a.type ?? a.answerType ?? "";
    const snapshot = /market cap|p\/e|p\/b|\broe\b|valuation comparison/.test(text);
    const announcements = (a.sources||[]).some(s=>s.url) || / news:/.test(text);
    const catalyst = /catalyst/.test(text);
    const l = leak(a); if(l.length) anyLeak=true;
    console.log(`\n== ${q}`);
    console.log(`   type=${type}  resolved=${resolved(q)}`);
    console.log(`   ${a.headline}`);
    console.log(`   charts=${(a.charts||[]).length} sources=${(a.sources||[]).length} snapshot=${snapshot} announcements=${announcements} catalyst=${catalyst} limits=${(a.limitations||[]).length}`);
    if((a.limitations||[]).length) console.log(`   limitations: ${a.limitations.join(" | ")}`);
    console.log(`   leak=[${l.join(",")}]`);
  } catch(e){ console.log(`\n== ${q}\n   ERROR ${e.message}`); }
}
console.log(`\nLeakage scan: ${anyLeak?"FAIL":"CLEAN"}`);