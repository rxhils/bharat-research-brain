import type { ChartSpec, KnowledgeEntry } from "./types";
import { lookupKnowledge } from "./indiaMarketKnowledge";

// Build a cause -> transmission -> variable -> impact -> risk chain. Prefers the verified KB
// chain; falls back to a generic India transmission chain. Returns a flow chart spec too.
export function buildMechanism(topicOrQuery: string, fallbackTopic?: string): { chain: string; flow: ChartSpec | null; knowledge: KnowledgeEntry | null } {
  const kb = lookupKnowledge(topicOrQuery) || (fallbackTopic ? lookupKnowledge(fallbackTopic) : null);
  const chain = kb ? kb.chain : "driver moves -> transmission channel -> affected variable (rupee/yields/flows) -> sector/company impact -> risk/counterpoint";
  const steps = chain.split("->").map((s) => s.trim()).filter(Boolean);
  const flow: ChartSpec | null = steps.length >= 2
    ? { type: "flow", title: "Mechanism chain", dataSource: "maven_mechanism", data: steps.map((s, i) => ({ step: i + 1, label: s })) }
    : null;
  return { chain, flow, knowledge: kb };
}