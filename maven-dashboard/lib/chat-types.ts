export type BlockType = "DATA" | "POINT" | "MACRO" | "CONTEXT" | "RISK" | "TAKEAWAY"
  | "data" | "point" | "macro" | "context" | "risk" | "takeaway";

export type AnswerBlock = { type: BlockType; title: string; body: string };

export type ChatAnswer = {
  headline: string;
  summary: string;
  blocks: AnswerBlock[];
  citations: { label: string; time: string }[];
  followups: string[];
  demo?: boolean;
};