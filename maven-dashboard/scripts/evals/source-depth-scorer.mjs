// Maven Source Depth & Research Quality Loop v1 - scorer.
// Scores a diagnostic row (see test-source-depth.mjs) 0-100 against tier-based source-depth
// and evidence-quality targets. Hard fails gate `pass` regardless of score.

const TIER_MIN = { light: 5, standard: 10, deep: 18 };
const TIER_TARGET = { light: 7, standard: 13, deep: 22 };
const CLICKABLE_MIN = { light: 3, standard: 5, deep: 10 };

// A response with zero sources beyond the always-present "market data" (Yahoo Finance, itself
// carries confidence "retrieved") and "Maven analysis" chips means no search provider actually
// returned results this run - an environment/config fact, not a pipeline defect. Hard count/URL
// fails are gated on this being true, per the task's own "when source search is available" wording.
// realSourceCount (computed by the caller from the raw sources array, excluding those two synthetic
// chips) is the reliable signal; the evidence-summary counts alone conflate the two.
function sourceSearchAvailable(row) {
  return (row.realSourceCount ?? 0) > 0;
}

export function scoreSourceDepth(row) {
  const reasons = [];
  let score = 0;
  const tier = row.tier || "standard";
  const min = TIER_MIN[tier] ?? TIER_MIN.standard;
  const target = TIER_TARGET[tier] ?? TIER_TARGET.standard;
  const clickMin = CLICKABLE_MIN[tier] ?? CLICKABLE_MIN.standard;
  const searchAvailable = sourceSearchAvailable(row);

  // --- hard fails (gate pass regardless of score) ---
  const hardFails = [];
  if (row.answerType === "unsafe_advice") hardFails.push("misrouted to unsafe_advice");
  if ((row.advice || []).length) hardFails.push("advice:" + row.advice.join(","));
  if ((row.leak || []).length) hardFails.push("leak:" + row.leak.join(","));
  if ((row.freshness || []).length) hardFails.push("freshness:" + row.freshness.join(","));
  if ((row.fakeOfficialCount || 0) > 0) hardFails.push(`fakeOfficialLabel:${row.fakeOfficialCount}`);
  if (searchAvailable && row.sourceCount < min) hardFails.push(`sourceCount ${row.sourceCount}<${min} (min, search available)`);
  if (searchAvailable && tier === "deep" && row.clickableUrlCount === 0) hardFails.push("no clickable URLs for deep research (search available)");
  if (!searchAvailable && row.limitations.length === 0) hardFails.push("no sources AND no limitation explaining why - silent gap");

  // --- scoring (informational when search unavailable; still computed for visibility) ---
  const countRatio = Math.min(1, row.sourceCount / target);
  score += Math.round(countRatio * 30);
  if (row.officialRequired || tier !== "light") { if (row.officialSourceCount > 0 || !searchAvailable) score += 10; else reasons.push("no official/reputable source"); }
  else score += 10;
  if (!searchAvailable || row.clickableUrlCount >= clickMin) score += 15; else reasons.push(`clickableUrlCount ${row.clickableUrlCount}<${clickMin}`);
  if (row.latestPeriodFound || row.latestAnnualPeriodFound || !searchAvailable) score += 10; else reasons.push("no latest period found in sources");
  if (row.metricEvidenceCount > 0 || row.limitations.some((l) => /unavailable|not verified|not available/i.test(l))) score += 15; else reasons.push("no metric evidence and no clean unavailable-limitation");
  if (hardFails.length === 0) score += 15; else reasons.push(...hardFails);
  if (row.coverageStatus && row.coverageStatus !== "unavailable") score += 5; else if (!searchAvailable) score += 5;
  if (row.latencyMs == null || row.latencyMs < 30000) score += 0; else reasons.push(`latency ${row.latencyMs}ms > 30s`);

  const pass = hardFails.length === 0 && score >= 60;
  return { score: Math.min(100, score), pass, reasons, searchAvailable, hardFails };
}
