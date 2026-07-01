import type { Catalyst } from "./types";

// Keyword-pattern catalyst detection from company news/announcement snippets. Never invents:
// if nothing matches, returns "no_clear_catalyst".
const CATS: [string, RegExp][] = [
  ["earnings", /\b(results?|q[1-4]fy|quarter|profit|\bpat\b|revenue|earnings|net income|topline|bottomline)\b/i],
  ["guidance", /\b(guidance|outlook|forecast|raises? guidance|cuts? guidance)\b/i],
  ["margin pressure", /\b(margin|\bnim\b|ebitda margin|gross margin|cost pressure|input cost)\b/i],
  ["order win", /\b(order win|new order|contract|deal win|bags order|order book|awarded|order intake)\b/i],
  ["regulatory", /\b(rbi|sebi|regulat|penalt|\bban\b|probe|investigat|approval|licen[cs]e|cci)\b/i],
  ["corporate action", /\b(dividend|bonus issue|stock split|buyback|merger|acquisition|demerger|stake sale)\b/i],
  ["promoter/FII/DII", /\b(promoter|\bfii\b|\bdii\b|\bfpi\b|block deal|bulk deal|shareholding|pledge)\b/i],
  ["management commentary", /\b(concall|earnings call|management (said|commentary)|\bceo\b|\bmd\b guidance)\b/i],
  ["commodity input", /\b(crude|steel|coal|aluminium|raw material|commodit)\b/i],
  ["currency impact", /\b(rupee|usd\s*\/?\s*inr|currency|forex|depreciat|apprec)\b/i],
  ["valuation/derating", /\b(valuation|expensive|derat|rerat|downgrade|upgrade|target price)\b/i],
  ["sector rotation", /\b(sector rotation|sectoral move|rotation into|peers? (rally|fall))\b/i],
];

export function extractCatalyst(items: { title?: string; snippet?: string }[]): Catalyst {
  const text = items.map((i) => (i.title || "") + " " + (i.snippet || "")).join(" ").toLowerCase();
  const found: { cat: string; ev: string }[] = [];
  for (const [cat, re] of CATS) { const m = text.match(re); if (m) found.push({ cat, ev: m[0] }); }
  if (!found.length) return { primaryCatalyst: "no_clear_catalyst", secondaryCatalysts: [], confidence: "low", evidence: [] };
  const primary = found[0].cat;
  const secondary = Array.from(new Set(found.slice(1).map((f) => f.cat))).slice(0, 3);
  return { primaryCatalyst: primary, secondaryCatalysts: secondary, confidence: items.length >= 2 && found.length >= 2 ? "medium" : "low", evidence: found.slice(0, 3).map((f) => f.ev) };
}