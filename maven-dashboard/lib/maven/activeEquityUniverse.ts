// Curated liquid NSE active-equity universe for the stock-mover leaderboard.
//
// Why a curated subset (not all ~2,380 NSE symbols): the only keyless quote path is Yahoo's v8
// per-symbol chart endpoint (the v7 batch endpoint now 401s without a crumb/cookie, which we do
// NOT bypass). Scanning the full universe per request is too slow / rate-limit-prone, so v1 ranks
// movers within a documented, highly-liquid large/mid-cap subset and labels it honestly. This is a
// real market-data leaderboard of individual stocks - never indices, never fabricated.
//
// Swap-in path for "all-NSE" later: replace SYMBOLS with a cached Nifty 500 / F&O / bhavcopy-derived
// active list (loadNseUniverse already downloads the permitted EQUITY_L.csv) - the consumer contract
// below is stable.

export type ActiveEquityUniverse = {
  symbols: { symbol: string; name: string }[];
  universeLabel: string;
  coverage: "subset" | "full";
  limitation?: string;
};

// Nifty 50 core + a set of very liquid large/mid-caps. Symbols are NSE tickers (yahoo suffix .NS is
// appended by the scanner). Stale/renamed symbols simply return no quote and drop out safely.
const SYMBOLS: { symbol: string; name: string }[] = [
  { symbol: "RELIANCE", name: "Reliance Industries" }, { symbol: "TCS", name: "Tata Consultancy Services" },
  { symbol: "HDFCBANK", name: "HDFC Bank" }, { symbol: "ICICIBANK", name: "ICICI Bank" },
  { symbol: "INFY", name: "Infosys" }, { symbol: "HINDUNILVR", name: "Hindustan Unilever" },
  { symbol: "ITC", name: "ITC" }, { symbol: "SBIN", name: "State Bank of India" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel" }, { symbol: "BAJFINANCE", name: "Bajaj Finance" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank" }, { symbol: "LT", name: "Larsen & Toubro" },
  { symbol: "HCLTECH", name: "HCL Technologies" }, { symbol: "AXISBANK", name: "Axis Bank" },
  { symbol: "ASIANPAINT", name: "Asian Paints" }, { symbol: "MARUTI", name: "Maruti Suzuki" },
  { symbol: "SUNPHARMA", name: "Sun Pharmaceutical" }, { symbol: "TITAN", name: "Titan Company" },
  { symbol: "ULTRACEMCO", name: "UltraTech Cement" }, { symbol: "WIPRO", name: "Wipro" },
  { symbol: "NESTLEIND", name: "Nestle India" }, { symbol: "ONGC", name: "Oil & Natural Gas Corp" },
  { symbol: "NTPC", name: "NTPC" }, { symbol: "POWERGRID", name: "Power Grid Corp" },
  { symbol: "TATAMOTORS", name: "Tata Motors" }, { symbol: "TATASTEEL", name: "Tata Steel" },
  { symbol: "JSWSTEEL", name: "JSW Steel" }, { symbol: "ADANIENT", name: "Adani Enterprises" },
  { symbol: "ADANIPORTS", name: "Adani Ports & SEZ" }, { symbol: "COALINDIA", name: "Coal India" },
  { symbol: "BAJAJFINSV", name: "Bajaj Finserv" }, { symbol: "HDFCLIFE", name: "HDFC Life Insurance" },
  { symbol: "SBILIFE", name: "SBI Life Insurance" }, { symbol: "GRASIM", name: "Grasim Industries" },
  { symbol: "HINDALCO", name: "Hindalco Industries" }, { symbol: "DRREDDY", name: "Dr. Reddy's Labs" },
  { symbol: "CIPLA", name: "Cipla" }, { symbol: "BRITANNIA", name: "Britannia Industries" },
  { symbol: "EICHERMOT", name: "Eicher Motors" }, { symbol: "HEROMOTOCO", name: "Hero MotoCorp" },
  { symbol: "BAJAJ-AUTO", name: "Bajaj Auto" }, { symbol: "TECHM", name: "Tech Mahindra" },
  { symbol: "INDUSINDBK", name: "IndusInd Bank" }, { symbol: "APOLLOHOSP", name: "Apollo Hospitals" },
  { symbol: "TATACONSUM", name: "Tata Consumer Products" }, { symbol: "BPCL", name: "Bharat Petroleum" },
  { symbol: "LTIM", name: "LTIMindtree" }, { symbol: "SHRIRAMFIN", name: "Shriram Finance" },
  { symbol: "TRENT", name: "Trent" }, { symbol: "DMART", name: "Avenue Supermarts" },
  { symbol: "PIDILITIND", name: "Pidilite Industries" }, { symbol: "DABUR", name: "Dabur India" },
  { symbol: "GAIL", name: "GAIL India" }, { symbol: "IOC", name: "Indian Oil Corp" },
  { symbol: "VEDL", name: "Vedanta" }, { symbol: "HAL", name: "Hindustan Aeronautics" },
  { symbol: "BEL", name: "Bharat Electronics" }, { symbol: "SIEMENS", name: "Siemens" },
  { symbol: "VBL", name: "Varun Beverages" }, { symbol: "PFC", name: "Power Finance Corp" },
  { symbol: "IRCTC", name: "IRCTC" }, { symbol: "ZOMATO", name: "Eternal (Zomato)" },
];

/** The active-equity universe the mover scanner ranks within. v1 is a curated liquid subset. */
export function getActiveEquityUniverse(): ActiveEquityUniverse {
  return {
    symbols: SYMBOLS,
    universeLabel: "liquid large/mid-cap NSE equities",
    coverage: "subset",
    limitation: "Ranked within a liquid large/mid-cap NSE-equity universe, not the full NSE list.",
  };
}
