import type { ChatAnswer } from "./chat-types";

// Preview answers until DEEPSEEK_API_KEY is set. India-tuned, educational, never advisory.
// Order matters: more specific patterns first.
const CANNED: { match: RegExp; answer: ChatAnswer }[] = [
  {
    match: /compare|icici|hdfc|versus|\bvs\b/i,
    answer: {
      headline: "ICICI Bank vs HDFC Bank - same tailwind, different starting points",
      summary: "Both large private banks benefit from easier rates and steady credit growth; the difference is where each sits in its cycle - ICICI on execution momentum, HDFC still digesting its merger.",
      blocks: [
        { type: "point", title: "Business mix", body: "Both lean on retail lending. ICICI has shown steady NIMs and asset quality; HDFC is absorbing the HDFC Ltd merger, which has weighed on margins and the deposit ratio." },
        { type: "point", title: "Macro exposure", body: "Both gain from falling G-Sec yields (treasury gains, cheaper funds) and a calm rupee; both face deposit-growth competition." },
        { type: "risk", title: "What differs", body: "ICICI's risk is valuation after a strong run; HDFC's is the pace of merger normalisation (CASA mix, NIM recovery)." },
        { type: "takeaway", title: "India takeaway", body: "Same macro tailwind, different self-help stories - this compares drivers, it is not a recommendation of either." },
      ],
      citations: [{ label: "Mint", time: "today" }, { label: "BusinessLine", time: "today" }],
      followups: ["What is NIM and why it matters?", "How does the HDFC merger affect this?", "Why do bank yields matter?"],
    },
  },
  {
    match: /rbi|repo|monetary policy|\bmpc\b|rate decision|rate cut|rate cycle/i,
    answer: {
      headline: "What to watch around an RBI policy",
      summary: "The decision itself often matters less than the tone: the stance, the liquidity signal, and the inflation/growth language set the path for bank funding costs and the rupee.",
      blocks: [
        { type: "point", title: "Rate + stance", body: "Watch the repo decision and whether the stance stays neutral or shifts - the stance hints at the next move more than the number does." },
        { type: "point", title: "Liquidity + language", body: "System-liquidity actions (OMO, CRR) and the inflation/growth wording matter for banks, NBFCs and bonds." },
        { type: "risk", title: "Market reaction", body: "Rate-sensitives (banks, autos, realty) and the rupee/G-Sec yields move on surprises versus expectations, not the absolute rate." },
        { type: "takeaway", title: "India takeaway", body: "Track stance + liquidity + tone, not just the rate. Educational context, not a trade plan." },
      ],
      citations: [{ label: "RBI", time: "scheduled" }, { label: "Mint", time: "today" }],
      followups: ["What is the repo rate?", "How does liquidity affect banks?", "What is OMO?"],
    },
  },
  {
    match: /crude|oil|omc/i,
    answer: {
      headline: "Softer crude is a tailwind for India macro",
      summary: "India imports most of its oil, so lower crude eases the import bill, the current-account deficit and inflation, and helps OMCs, paints, aviation and logistics.",
      blocks: [
        { type: "point", title: "Why it matters", body: "Crude is one of India's largest imports; a fall lowers the trade deficit and supports the rupee." },
        { type: "point", title: "Sectors helped", body: "Oil marketing companies (margins), paints and tyres (input costs), aviation and logistics (fuel)." },
        { type: "risk", title: "What to watch", body: "Crude is volatile and supply-driven; the benefit reverses quickly if prices spike." },
        { type: "takeaway", title: "India takeaway", body: "Lower crude is broadly supportive for Indian macro. Educational context, not advice." },
      ],
      citations: [{ label: "BusinessLine", time: "today" }],
      followups: ["Which OMCs benefit most?", "Explain the rupee link", "Summarize today's market"],
    },
  },
  {
    match: /fii|fpi|flow|debt inflow|\bfar\b/i,
    answer: {
      headline: "FII/FPI flows, explained simply",
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
  {
    match: /bank/i,
    answer: {
      headline: "Banks are leading on an easier rate-and-liquidity backdrop",
      summary: "Softening bond yields, comfortable system liquidity and selective institutional buying are supporting financials, with private banks ahead of PSUs.",
      blocks: [
        { type: "point", title: "Macro backdrop", body: "Lower 10Y G-Sec yields reduce banks' cost of funds and lift treasury gains; a stable rupee keeps the rate path calm." },
        { type: "point", title: "Flows", body: "DII buying has stayed steady while FII selling has slowed, and incoming flows tilt toward large-cap financials." },
        { type: "risk", title: "What to watch", body: "Deposit growth lagging credit growth, any uptick in slippages, and the RBI's next liquidity stance." },
        { type: "takeaway", title: "India takeaway", body: "Bank Nifty tends to lead when yields fall and liquidity is easy. This is a mechanism explanation, not a recommendation." },
      ],
      citations: [{ label: "Mint", time: "today" }, { label: "BusinessLine", time: "today" }],
      followups: ["Compare ICICI Bank vs HDFC Bank", "Explain this simply", "What changed today?"],
    },
  },
  {
    match: /summari|market wrap|today'?s? (indian )?market|wrap|market today/i,
    answer: {
      headline: "Today in the Indian market, in plain English",
      summary: "A quick read of the headline indices, what led and lagged, the flow picture, and the one or two macro threads driving the tape.",
      blocks: [
        { type: "point", title: "Index move", body: "Where Nifty 50, Sensex and Bank Nifty closed, and whether breadth (advances vs declines) confirmed the move." },
        { type: "point", title: "Leaders & laggards", body: "Which sectors led (often financials or IT) and which dragged (often metals or realty on global cues)." },
        { type: "point", title: "Flows & macro", body: "The FII vs DII balance for the session and the macro thread in focus - crude, the rupee, or rate expectations." },
        { type: "takeaway", title: "India takeaway", body: "A market wrap recaps what moved and why - context, not a call to act." },
      ],
      citations: [{ label: "Mint", time: "today" }, { label: "BusinessLine", time: "today" }],
      followups: ["Why did banks lead today?", "What are FIIs doing?", "What is market breadth?"],
    },
  },
];

const FALLBACK: ChatAnswer = {
  headline: "Here's the market context",
  summary: "Maven reads the market India-first - what is moving and why it matters across Nifty, sectors, flows and macro.",
  blocks: [
    { type: "point", title: "How to read it", body: "Name a stock, sector, flow or macro move and Maven explains the driver, the India context, and the risks on both sides." },
    { type: "takeaway", title: "India takeaway", body: "Maven explains market mechanisms for Indian investors - educational context, not investment advice." },
  ],
  citations: [{ label: "Maven analysis", time: "current" }],
  followups: ["Why are banks leading?", "What sectors benefit from softer crude?", "Summarize today's market"],
};

export function answerFor(query: string, subject?: string): ChatAnswer {
  const q = subject ? subject + " " + query : query;
  const hit = CANNED.find((c) => c.match.test(q));
  return { ...(hit ? hit.answer : FALLBACK), demo: true };
}