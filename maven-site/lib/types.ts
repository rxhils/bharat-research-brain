export type Quote = {
  symbol: string;
  label: string;
  price: number | null;
  changePct: number | null;
  spark?: number[];
};
export type Sector = { name: string; changePct: number };
export type FlowSnapshot = { fiiCr: number; diiCr: number; asOf: string };
export type Pulse = {
  breadthAdv: number;
  breadthDec: number;
  flows: FlowSnapshot;
  topSectors: Sector[];
  themes: string[];
  headlines: { title: string; source: string; time: string }[];
};
export type MarketSnapshot = {
  live: boolean;
  asOf: string;
  source: string;
  indices: Quote[];
  sectors: Sector[];
  pulse: Pulse;
};
// Maven answer structure (educational research format, never advisory):
//  data    -> Key data / numbers   point -> Analysis / drivers
//  risk    -> Key risks            trigger -> What would change the view
//  takeaway -> Final view + educational disclaimer
export type BlockType = "data" | "point" | "risk" | "trigger" | "takeaway";
export type AnswerBlock = { type: BlockType; title: string; body: string };
// Maven View: a research stance, NOT a buy/sell call.
export type VerdictTone = "constructive" | "neutral" | "cautious";
export type Verdict = { label: string; tone: VerdictTone };
export type ChatAnswer = {
  verdict?: Verdict;
  headline: string;
  summary: string;
  blocks: AnswerBlock[];
  citations: { label: string; time: string }[];
  followups: string[];
  demo?: boolean;
};