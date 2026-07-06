// Visible-output guards for Maven evals.
export const FORBIDDEN = ["deepseek","openai","anthropic","llm","api key","provider","backend","env","tavily error","yahoo error","server-side key","fallback","mock","demo","preview","searxng","serper","scraper"];
export const ADVICE = ["strong buy","buy now","sell now","target price","guaranteed","sure shot","multibagger","risk-free return","risk free returns","double your money","double money","option strike"];
function wb(t){ return new RegExp("\\b" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i"); }

// Maven's own generated prose - the only text that can leak backend internals or assert advice.
// Deliberately excludes `sources` (cited third-party titles/snippets legitimately contain
// journalism phrases like "target price" or "Q4 preview" when reporting what a source said) and
// `evidence`/other internal metadata fields.
function visibleProse(obj) {
  const parts = [obj.headline, obj.summary, obj.reportTitle, obj.reportSummary];
  for (const k of obj.keyData || []) parts.push(k.label, k.value, k.change);
  for (const b of obj.blocks || []) parts.push(b.title, b.body);
  for (const f of obj.followUps || []) parts.push(f);
  for (const l of obj.limitations || []) parts.push(l);
  for (const bl of obj.bullets || []) parts.push(bl);
  for (const s of obj.introSections || []) parts.push(s.title, s.body);
  for (const rs of obj.reportSections || []) {
    parts.push(rs.title, rs.summary);
    for (const b of rs.blocks || []) parts.push(b.title, b.body);
    for (const l of rs.limitations || []) parts.push(l);
  }
  return parts.filter((p) => typeof p === "string").join("\n");
}

function sourceText(obj) {
  return (obj.sources || []).map((s) => `${s.title || ""} ${s.name || ""} ${s.snippet || ""}`).join("\n");
}

// Blocks sometimes embed a cited headline inline as "News: <title>. [source: X]" rather than as a
// separate `sources` entry - the same legitimate-citation exception, just inline. Extracted out so
// the leak/advice scan only sees Maven's own sentences, and captured for scanSourceRiskTerms.
const INLINE_NEWS = /News:\s*.*?\[source:[^\]]*\]/gi;

export function scanLeak(obj){ const s = visibleProse(obj).replace(INLINE_NEWS, ""); return FORBIDDEN.filter((t) => wb(t).test(s)); }
export function scanAdvice(obj){ const s = visibleProse(obj).replace(INLINE_NEWS, ""); return ADVICE.filter((t) => wb(t).test(s)); }

// Informational only, never gates pass/fail: flags when a cited source's own title/snippet
// contains advisory-sounding language (e.g. a news headline reporting a brokerage's target
// price). Lets a reviewer see this without treating a legitimate citation as Maven's own advice.
export function scanSourceRiskTerms(obj){
  const inline = (visibleProse(obj).match(INLINE_NEWS) || []).join("\n");
  const s = sourceText(obj) + "\n" + inline;
  return ADVICE.filter((t) => wb(t).test(s));
}

// Freshness lock (stock answers): VISIBLE text must not state stale-FY or approximate company
// metrics unless they are backed by the answer's own source snippets (evidence-backed figures pass).
function latestCompletedFY(d = new Date()){ const y = d.getFullYear() - 2000; return (d.getMonth() >= 3 ? y + 1 : y) - 1; }
const FY_TOKEN = /\bQ[1-4]\s*[-\s]?FY\s*'?(\d{2,4})\b|\bFY\s*'?(\d{2,4})\b/gi;
const APPROX = /(~\s?\d[\d.,]*\s*%?|\b(?:approx(?:imately)?|roughly|around|estimated)\s+[₹$]?\d[\d.,]*|\b\d{1,3}\s*[–—-]\s*\d{1,3}\s*%)/gi;
const METRIC_WORDS = /\b(revenue|margin|market share|capex|profit|pat|ebitda|order book|guidance|growth|cagr|volume share|shareholding|pledge|roe|roce|valuation)\b/i;

export function scanFreshness(resp, { historical = false } = {}) {
  if (historical) return [];
  const visible = [resp.headline, resp.summary, ...(resp.blocks || []).map((b) => `${b.title} ${b.body}`)].join("\n");
  const srcText = JSON.stringify(resp.sources || []).toLowerCase();
  const hits = [];
  const cutoff = latestCompletedFY();
  let m;
  FY_TOKEN.lastIndex = 0;
  while ((m = FY_TOKEN.exec(visible)) !== null) {
    const raw = parseInt(m[1] || m[2], 10);
    const fy = raw >= 2000 ? raw - 2000 : raw;
    if (fy < cutoff && !srcText.includes(m[0].toLowerCase())) hits.push(`stale:${m[0]}`);
  }
  for (const sentence of visible.split(/(?<=[.!?])\s+/)) {
    if (!METRIC_WORDS.test(sentence)) continue;
    APPROX.lastIndex = 0;
    let a;
    while ((a = APPROX.exec(sentence)) !== null) {
      const frag = a[0].toLowerCase().replace(/\s+/g, " ").trim();
      if (!srcText.includes(frag) && !srcText.includes(frag.replace(/^~\s?/, ""))) hits.push(`approx:${a[0]}`);
    }
  }
  return hits;
}