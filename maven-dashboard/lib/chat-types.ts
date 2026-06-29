export type AnswerBlock = { type: "point" | "risk" | "takeaway"; title: string; body: string };
export type ChatAnswer = {
  headline: string;
  summary: string;
  blocks: AnswerBlock[];
  citations: { label: string; time: string }[];
  followups: string[];
  demo?: boolean;
};