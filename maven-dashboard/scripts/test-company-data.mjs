const BASE = process.env.MAVEN_URL || "http://localhost:3000";
const RES = { reliance: "RELIANCE.NS", "hdfc bank": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS", "tata motors": "TATAMOTORS.NS", zomato: "ZOMATO.NS", ongc: "ONGC.NS" };
const QUERIES = [
  "Why is Reliance moving today?", "Why is HDFC Bank down today?", "Explain ICICI Bank today.",
  "What changed in Tata Motors?", "Why is Zomato falling?", "Compare HDFC Bank and ICICI Bank",
  "Compare Reliance and ONGC", "What are the latest results for HDFC Bank?", "What is the shareholding pattern of Reliance?",
];
const FORBIDDEN = ["deepseek","openai","anthropic","llm","api key","backend","provider","tavily error","yahoo error","env","fallback","mock","preview","demo","server-side key"];
function leak(o){ const s=JSON.stringify(o); return FORBIDDEN.filter(t=>new RegExp("\\b"+t.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\b","i").test(s)); }
function resolved(q){ const l=q.toLowerCase(); const out=[]; for(const k of Object.keys(RES)) if(l.includes(k)) out.push(RES[k]); return out.join(",")||"-"; }
let anyLeak=false;
for (const q of QUERIES) {
  try {
    const r = await fetch(BASE+"/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:q})});
    const a = await r.json(); const text = JSON.stringify(a).toLowerCase();
    const type = a.type ?? a.answerType ?? "";
    const snapFields = ["p/e","p/b","roe","mkt cap","market cap"].filter(k=>text.includes(k)).length;
    const anns = (a.sources||[]).filter(s=>s.url).length;
    const result = /latest results|yoy|quarterly result/.test(text);
    const shp = /shareholding|promoter %|promoter holding/.test(text);
    const l = leak(a); if(l.length) anyLeak=true;
    console.log(`\n== ${q}`);
    console.log(`   type=${type}  resolved=${resolved(q)}`);
    console.log(`   ${a.headline}`);
    console.log(`   snapFields=${snapFields} announcements=${anns} result=${result} shareholding=${shp} charts=${(a.charts||[]).length} sources=${(a.sources||[]).length} limits=${(a.limitations||[]).length}`);
    if((a.limitations||[]).length) console.log(`   limitations: ${a.limitations.join(" | ")}`);
    console.log(`   leak=[${l.join(",")}]`);
  } catch(e){ console.log(`\n== ${q}\n   ERROR ${e.message}`); }
}
console.log(`\nLeakage scan: ${anyLeak?"FAIL":"CLEAN"}`);