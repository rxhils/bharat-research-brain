import type { ChatAnswer } from "./chat-types";

// Preview answers until DEEPSEEK_API_KEY is set. India-tuned, educational, never advisory.
const CANNED: { match: RegExp; answer: ChatAnswer }[] = [
  {
    match: /bank/i,
    answer: {
      headline: "Banks are leading on an easier rate-and-liquidity backdrop",
      summary: "Softening bond yields, comfortable system liquidity and selective institutional buying are supporting financials, with private banks ahead of PSUs.",
      blocks: [
        { type: "point", title: "Macro backdrop", body: "Lower 10Y G-Sec yields reduce banks cost of funds and lift treasury gains; a stable rupee keeps the rate path calm." },
        { type: "point", title: "Flows", body: "DII buying has stayed steady while FII selling has slowed, and incoming flows tilt toward large-cap financials." },
        { type: "risk", title: "What to watch", body: "Deposit growth lagging credit growth, any uptick in slippages, and the RBI next liquidity stance." },
        { type: "takeaway", title: "India takeaway", body: "Bank Nifty tends to lead when yields fall and liquidity is easy. This is a mechanism explanation, not a recommendation." },
      ],
      citations: [{ label: "Mint", time: "today" }, { label: "BusinessLine", time: "today" }],
      followups: ["Compare ICICI Bank vs HDFC Bank", "Explain this simply", "What changed today?"],
    },
  },
  {
    match: /crude|oil|omc/i,
    answer: {
      headline: "Softer crude is a tailwind for India macro",
      summary: "India imports most of its oil, so lower crude eases the import bill, the current-account deficit and inflation, and helps OMCs, paints, aviation and logistics.",
      blocks: [
        { type: "point", title: "Why it matters", body: "Crude is one of India largest imports; a fall lowers the trade deficit and supports the rupee." },
        { type: "point", title: "Sectors helped", body: "Oil marketing companies (margins), paints and tyres (input costs), aviation and logistics (fuel)." },
        { type: "risk", title: "What to watch", body: "Crude is volatile and supply-driven; the benefit reverses quickly if prices spike." },
        { type: "takeaway", title: "India takeaway", body: "Lower crude is broadly supportive for Indian macro. Educational context, not advice." },
      ],
      citations: [{ label: "BusinessLine", time: "today" }],
      followups: ["Which OMCs benefit most?", "Explain the rupee link", "Summarize today market"],
    },
  },
  {
    match: /fii|fpi|flow|debt inflow|far/i,
    answer: {
      headline: "FII/FPI flows, explained for a retail investor",
      summary: "Foreign investors move money in and out of Indian equities and bonds. Equity flows swing with global risk appetite; debt flows have grown since Indian bonds joined global indices via the FAR route.",
      blocks: [
        { type: "point", title: "Equity vs debt", body: "Equity FII flows are sentiment-driven and volatile; FAR debt inflows are steadier, tied to index inclusion." },
        { type: "point", title: "Who offsets them", body: "Domestic institutions (mutual funds and insurers) often absorb FII selling, cushioning the market." },
        { type: "takeaway", title: "India takeaway", body: "Watch the FII vs DII balance: persistent DII buying can offset FII outflows. Context only, not advice." },
      ],
      citations: [{ label: "NSDL", time: "EOD" }, { label: "Mint", time: "today" }],
      followups: ["What is the FAR route?", "How big are DII flows?", "Explain this simply"],
    },
  },
];

const FALLBACK: ChatAnswer = {
  headline: "Here is the market context",
  summary: "This is a Maven preview answer. Live AI reasoning (DeepSeek V4 Pro) turns on once a server-side key is set; for now answers are illustrative and India-focused.",
  blocks: [
    { type: "point", title: "What happened", body: "Maven summarizes the move using index, sector and flow data." },
    { type: "point", title: "Why it matters", body: "It then explains the India-specific knock-on effects for the sectors you care about." },
    { type: "takeaway", title: "India takeaway", body: "Educational explanation only, never a buy or sell call." },
  ],
  citations: [{ label: "Maven", time: "preview" }],
  followups: ["Why are banks leading?", "What sectors benefit from softer crude?", "Summarize today market"],
};

export function answerFor(query: string, subject?: string): ChatAnswer {
  const q = subject ? subject + " " + query : query;
  const hit = CANNED.find((c) => c.match.test(q));
  return { ...(hit ? hit.answer : FALLBACK), demo: true };
}