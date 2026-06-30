import type { KnowledgeEntry } from "./types";

// Verified EVERGREEN mechanism grounding for Indian markets. NOT a substitute for live data -
// it grounds the mechanism + provides directional, widely-cited macro facts. Numbers here are
// directional and labelled as such; live numbers always come from data tools.
export const INDIA_KB: KnowledgeEntry[] = [
  {
    key: "crude", aliases: ["crude", "oil", "brent", "wti", "omc", "petroleum"],
    topic: "crude oil and India",
    summary: "India imports the bulk of its crude, so the oil price feeds straight into the import bill, the current-account deficit, the rupee, inflation and the fiscal/subsidy burden - then into sector winners and losers.",
    chain: "crude up -> import bill up -> CAD pressure up -> rupee pressure -> imported inflation up -> RBI less dovish -> rate-sensitive sectors pressured",
    winners: ["OMCs (marketing margins when retail prices lag)", "paints & tyres (crude derivatives as input)", "aviation & logistics (fuel cost)"],
    losers: ["upstream/ONGC-type (lower realizations when crude falls)", "broader market if a crude spike lifts inflation and yields"],
    facts: [
      { text: "India imports roughly 85% of its crude oil needs", confidence: "verified", directional: true },
      { text: "a ~$10/bbl sustained rise widens the current-account deficit by roughly 0.3-0.5% of GDP", confidence: "verified", directional: true },
    ],
    followUps: ["Which Indian sectors gain most from lower crude?", "How does crude affect USD/INR?", "Why do OMCs not always benefit from lower crude?"],
  },
  {
    key: "gsec", aliases: ["g-sec", "gsec", "yield", "10y", "bond", "bond yield"],
    topic: "G-Sec yields and banks",
    summary: "Government bond yields set the risk-free rate; when they fall, bond prices rise (bank treasury gains), funding-cost expectations ease, and valuation comfort improves - often supporting Bank Nifty.",
    chain: "yields down -> bond prices up -> bank treasury gains up -> valuation comfort up -> Bank Nifty leadership possible",
    winners: ["banks (treasury gains)", "NBFCs (funding cost)", "rate-sensitives: autos, real estate"],
    losers: ["banks if yields spike sharply (mark-to-market hit)"],
    facts: [],
    followUps: ["How do G-Sec yields affect bank NIMs?", "What RBI action moves yields?", "Why do rising yields hurt bank treasury books?"],
  },
  {
    key: "flows", aliases: ["fii", "fpi", "dii", "flow", "flows", "far", "institutional"],
    topic: "FII/DII flows",
    summary: "Foreign flows are sentiment-driven and hit large-caps and the rupee first; domestic institutions (DII) often absorb FII selling, so the FII-vs-DII balance and market breadth matter more than either alone.",
    chain: "FII selling up -> large-cap pressure up -> rupee pressure up -> DII absorption matters -> breadth may weaken",
    winners: ["large-cap financials when risk appetite returns"],
    losers: ["rupee and large-caps under heavy FII selling"],
    facts: [],
    followUps: ["How big is DII buying vs FII selling?", "What is the FAR route?", "How do flows affect the rupee?"],
  },
  {
    key: "usdinr", aliases: ["rupee", "usd/inr", "usdinr", "inr", "dollar"],
    topic: "USD/INR",
    summary: "The rupee moves with crude, the dollar index, rate differentials and flows. Weakness helps USD-earners (IT, pharma) but pressures importers (OMCs) and imported inflation.",
    chain: "rupee weak -> USD revenue worth more (IT/pharma) -> import costs up (OMCs/electronics) -> imported inflation up -> RBI watchful",
    winners: ["IT and pharma (USD revenue)", "other exporters"],
    losers: ["OMCs and importers", "inflation"],
    facts: [{ text: "Indian IT earns the majority of revenue in USD (US + Europe heavy)", confidence: "verified", directional: true }],
    followUps: ["How does a weak rupee help Indian IT?", "How does crude affect the rupee?", "Which sectors lose from a weak rupee?"],
  },
  {
    key: "rbi", aliases: ["rbi", "repo", "mpc", "rate cut", "rate hike", "policy", "liquidity"],
    topic: "RBI policy",
    summary: "Beyond the headline repo rate, the RBI's stance, liquidity actions (OMO/CRR) and inflation language drive bank funding costs, the rupee and rate-sensitive sectors.",
    chain: "RBI dovish/liquidity up -> funding costs down -> credit growth support -> banks/NBFCs/autos/real estate helped",
    winners: ["banks, NBFCs, autos, real estate when dovish"],
    losers: ["rate-sensitives if hawkish or liquidity tightens"],
    facts: [],
    followUps: ["What should I watch before an RBI policy?", "How does liquidity differ from the repo rate?", "Which sectors are most rate-sensitive?"],
  },
  {
    key: "banks", aliases: ["bank", "banks", "financials", "bank nifty", "nim", "casa"],
    topic: "Indian banks",
    summary: "Bank performance hinges on credit growth, deposit costs (CASA mix), net interest margins, slippages, and the rate/liquidity backdrop. Private banks usually lead on cleaner books and scale.",
    chain: "liquidity easy + yields soft -> funding cost down + treasury gains -> NIM/valuation comfort -> Bank Nifty leadership (if deposits keep pace)",
    winners: ["large private banks in easy-liquidity phases"],
    losers: ["banks if deposit growth lags credit or slippages rise"],
    facts: [],
    followUps: ["How do deposit costs affect bank NIMs?", "Compare a large private bank vs a PSU bank setup", "What reverses a bank rally?"],
  },
  {
    key: "monsoon", aliases: ["monsoon", "rural", "agri", "kharif", "rainfall"],
    topic: "monsoon and rural demand",
    summary: "A good monsoon supports rural incomes and demand (FMCG, two-wheelers, agri inputs) and can cool food inflation; a poor one does the reverse.",
    chain: "good monsoon -> rural income up -> rural demand up (FMCG/2W) + food inflation eases -> consumption + inflation outlook helped",
    winners: ["FMCG, two-wheelers, tractors, agri inputs"],
    losers: ["rural-exposed names in a weak monsoon; food inflation risk"],
    facts: [],
    followUps: ["Which sectors gain from a good monsoon?", "How does monsoon affect inflation?", "How exposed is FMCG to rural demand?"],
  },
  {
    key: "metals", aliases: ["metal", "metals", "steel", "aluminium", "china"],
    topic: "metals and global growth",
    summary: "Indian metals track global/China demand and the capex cycle; prices and the dollar drive realizations more than domestic factors.",
    chain: "China/global growth up -> metal prices up -> realizations up -> Indian metal earnings up (capex cycle helps)",
    winners: ["steel/aluminium producers when global demand firms"],
    losers: ["metals on China slowdown or a strong dollar"],
    facts: [],
    followUps: ["How does China demand affect Indian metals?", "How does the dollar affect metal prices?", "Are metals tied to the capex cycle?"],
  },
  {
    key: "it", aliases: ["it sector", "it stocks", "tcs", "infosys", "wipro", "tech"],
    topic: "Indian IT",
    summary: "IT is driven by US/Europe tech and BFSI spending, deal wins and attrition; a weak rupee helps margins but cannot offset a demand slowdown.",
    chain: "US demand up + rupee weak -> revenue + margins up -> IT outperformance (demand dominates currency)",
    winners: ["IT on strong US demand + weak rupee"],
    losers: ["IT in a US slowdown despite a weak rupee"],
    facts: [{ text: "a ~1% rupee depreciation can add roughly 30-50 bps to IT operating margins", confidence: "verified", directional: true }],
    followUps: ["How does the rupee affect IT margins?", "What drives IT demand?", "Why can a weak rupee not save IT in a downturn?"],
  },
];

export function lookupKnowledge(query: string): KnowledgeEntry | null {
  const s = (query || "").toLowerCase();
  for (const e of INDIA_KB) if (e.aliases.some((a) => new RegExp("\\b" + a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(s))) return e;
  return null;
}