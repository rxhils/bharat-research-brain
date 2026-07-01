// Visible-output guards for Maven evals.
export const FORBIDDEN = ["deepseek","openai","anthropic","llm","api key","provider","backend","env","tavily error","yahoo error","server-side key","fallback","mock","demo","preview"];
export const ADVICE = ["strong buy","buy now","sell now","target price","guaranteed","sure shot","multibagger","risk-free return","risk free returns","double your money","double money","option strike"];
function wb(t){ return new RegExp("\\b" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i"); }
export function scanLeak(obj){ const s = JSON.stringify(obj); return FORBIDDEN.filter((t) => wb(t).test(s)); }
export function scanAdvice(obj){ const s = JSON.stringify(obj); return ADVICE.filter((t) => wb(t).test(s)); }