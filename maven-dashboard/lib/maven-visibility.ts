import type { ChatAnswer } from "./chat-types";

// Maven is the product; the engine underneath is hidden infrastructure. These terms
// must NEVER reach the user. Defense-in-depth: the prompt avoids them, this sanitizes.
export const FORBIDDEN_VISIBLE_TERMS = [
  "DeepSeek", "V4 Pro", "OpenAI", "Anthropic", "Claude", "GPT", "LLM",
  "model provider", "API key", "server-side key", "preview answer", "preview mode",
  "illustrative", "mock answer", "demo answer", "fallback answer", "test response",
  "placeholder", "language model",
];

function esc(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function sanitizeVisibleText(text: string): string {
  let cleaned = text || "";
  for (const term of FORBIDDEN_VISIBLE_TERMS) {
    cleaned = cleaned.replace(new RegExp(esc(term), "gi"), "Maven");
  }
  // collapse an accidental "Maven Maven"
  return cleaned.replace(/\bMaven Maven\b/g, "Maven");
}

export function validateMavenOutput(text: string): { valid: boolean; violations: string[] } {
  const t = (text || "").toLowerCase();
  const violations = FORBIDDEN_VISIBLE_TERMS.filter((term) => t.includes(term.toLowerCase()));
  return { valid: violations.length === 0, violations };
}

/** Scrub every user-visible field of a Maven answer. */
export function sanitizeAnswer(a: ChatAnswer): ChatAnswer {
  return {
    ...a,
    headline: sanitizeVisibleText(a.headline),
    summary: sanitizeVisibleText(a.summary),
    blocks: a.blocks.map((b) => ({ ...b, title: sanitizeVisibleText(b.title), body: sanitizeVisibleText(b.body) })),
    followups: a.followups.map((f) => sanitizeVisibleText(f)),
  };
}