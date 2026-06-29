import type { ChatAnswer } from "./types";

// Phase-1 preview answers. DeepSeek V4 Pro replaces these in Phase 2 (server-side).
// India-tuned, educational, never advisory.
const CANNED: { match: RegExp; answer: ChatAnswer }[] = [
  {
    match: /bank/i,
    answer: {
      verdict: { label: "Constructive - watch", tone: "constructive" },
      headline: "Banks are leading on an easier rate-and-liquidity backdrop",
      summary:
        "Softening bond yields, comfortable system liquidity and selective institutional buying are supporting financials, with private banks ahead of PSUs.",
      blocks: [
        { type: "data", title: "Key data", body: "Bank Nifty is outperforming the broader Nifty; 10Y G-Sec yields have eased and system liquidity is in surplus (cross-check live levels before relying on them)." },
        { type: "point", title: "Macro backdrop", body: "Lower 10Y G-Sec yields reduce banks cost of funds and lift treasury gains; a stable rupee keeps the rate path calm." },
        { type: "point", title: "Flows", body: "DII buying has stayed steady while FII selling has slowed, and incoming flows tilt toward large-cap financials." },
        { type: "risk", title: "Key risks", body: "Deposit growth lagging credit growth, any uptick in slippages, and a hawkish shift in the RBI liquidity stance." },
        { type: "trigger", title: "What would change the view", body: "A reversal in yields, tighter liquidity, or rising slippages in Q-results would weaken the leadership case." },
        { type: "takeaway", title: "Final view", body: "Bank Nifty tends to lead when yields fall and liquidity is easy. Educational mechanism, not a recommendation." },
      ],
      citations: [{ label: "Mint", time: "today" }, { label: "BusinessLine", time: "today" }],
      followups: ["Compare private vs PSU bank drivers", "Explain this simply", "What changed today?"],
    },
  },
  {
    match: /crude|oil|omc/i,
    answer: {
      verdict: { label: "Macro tailwind", tone: "constructive" },
      headline: "Softer crude is a tailwind for India macro",
      summary:
        "India imports most of its oil, so lower crude eases the import bill, the current-account deficit and inflation, and helps OMCs, paints, aviation and logistics.",
      blocks: [
        { type: "data", title: "Key data", body: "Crude is among India's largest single import lines; movements feed directly into the trade deficit and CPI fuel basket." },
        { type: "point", title: "Why it matters", body: "A fall lowers the import bill and trade deficit and supports the rupee, which cools imported inflation." },
        { type: "point", title: "Sectors helped", body: "Oil marketing companies (margins), paints and tyres (input costs), aviation and logistics (fuel)." },
        { type: "risk", title: "Key risks", body: "Crude is volatile and supply-driven; the benefit reverses quickly if prices spike on supply shocks." },
        { type: "trigger", title: "What would change the view", body: "A sustained crude rebound or rupee weakness would erase the macro tailwind." },
        { type: "takeaway", title: "Final view", body: "Lower crude is broadly supportive for Indian macro. Educational context, not advice." },
      ],
      citations: [{ label: "BusinessLine", time: "today" }],
      followups: ["How does crude link to the rupee?", "Which sectors are most crude-sensitive?", "Summarize today market"],
    },
  },
  {
    match: /fii|fpi|flow|debt inflow|far/i,
    answer: {
      verdict: { label: "Neutral / watchlist", tone: "neutral" },
      headline: "FII/FPI flows, explained for a retail investor",
      summary:
        "Foreign investors move money in and out of Indian equities and bonds. Equity flows swing with global risk appetite; debt flows have grown since Indian bonds joined global indices via the FAR route.",
      blocks: [
        { type: "data", title: "Key data", body: "FII/DII flow figures are end-of-day (NSDL/NSE), not real-time; check the daily provisional print before quoting a number." },
        { type: "point", title: "Equity vs debt", body: "Equity FII flows are sentiment-driven and volatile; FAR debt inflows are steadier, tied to global bond index inclusion." },
        { type: "point", title: "Who offsets them", body: "Domestic institutions (mutual funds and insurers) often absorb FII selling, cushioning the market." },
        { type: "risk", title: "Key risks", body: "A global risk-off shift can drive sharp, fast FII equity outflows that DII buying may not fully offset." },
        { type: "trigger", title: "What would change the view", body: "A change in the Fed path, INR trend, or index-inclusion schedule would shift the flow picture." },
        { type: "takeaway", title: "Final view", body: "Watch the FII vs DII balance: persistent DII buying can offset FII outflows. Context only, not advice." },
      ],
      citations: [{ label: "NSDL", time: "EOD" }, { label: "Mint", time: "today" }],
      followups: ["What is the FAR route?", "How big are DII flows?", "Explain this simply"],
    },
  },
];

const FALLBACK: ChatAnswer = {
  verdict: { label: "Needs more data", tone: "neutral" },
  headline: "Here is the market context",
  summary:
    "This is a Maven preview response. Live AI reasoning (DeepSeek V4 Pro) is wired in when DEEPSEEK_API_KEY is set; for now answers are illustrative and India-focused.",
  blocks: [
    { type: "data", title: "Key data", body: "Maven grounds answers in index, sector and flow data, with source types and rough timestamps." },
    { type: "point", title: "What happened", body: "It summarizes the move, then explains the India-specific knock-on effects for the sectors you care about." },
    { type: "risk", title: "Key risks", body: "Single-source claims and stale data are flagged; flows and macro can reverse quickly." },
    { type: "trigger", title: "What would change the view", body: "Fresh results, a macro print, or a flow reversal would update the read." },
    { type: "takeaway", title: "Final view", body: "Educational explanation only, never a buy or sell call." },
  ],
  citations: [{ label: "Maven", time: "preview" }],
  followups: ["Why are banks leading?", "What sectors benefit from softer crude?", "Summarize today market"],
};

export function answerFor(query: string, subject?: string): ChatAnswer {
  const q = subject ? subject + " " + query : query;
  const hit = CANNED.find((c) => c.match.test(q));
  return { ...(hit ? hit.answer : FALLBACK), demo: true };
}