import type { ChatAnswer } from "./chat-types";
import { SYSTEM_PROMPT, RETRIEVAL_PACK } from "./india-context";

// Server-only DeepSeek client (OpenAI-compatible). The key is read from the env at call
// time so it is NEVER bundled to the client. Returns null on missing key/any error so
// callers fall back to the mock - the page never breaks.
export function deepseekEnabled(): boolean {
  return !!(process.env.DEEPSEEK_API_KEY || process.env.DEEPSEEK || process.env.deepseek);
}

async function chat(messages: { role: string; content: string }[], maxTokens = 900): Promise<string | null> {
  const key = process.env.DEEPSEEK_API_KEY || process.env.DEEPSEEK || process.env.deepseek;
  if (!key) return null;
  const base = (process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com").replace(/\/$/, "");
  const model = process.env.DEEPSEEK_MODEL || "deepseek-chat";
  try {
    const r = await fetch(base + "/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
      body: JSON.stringify({ model, messages, temperature: 0.3, max_tokens: maxTokens, response_format: { type: "json_object" } }),
      cache: "no-store",
    });
    if (!r.ok) return null;
    const j: any = await r.json();
    return j?.choices?.[0]?.message?.content ?? null;
  } catch {
    return null;
  }
}

function safeParse(s: string | null): any | null {
  if (!s) return null;
  try { return JSON.parse(s); } catch {}
  const m = s.match(/\{[\s\S]*\}/);
  if (m) { try { return JSON.parse(m[0]); } catch {} }
  return null;
}

export async function deepseekAnswer(query: string, subject?: string): Promise<ChatAnswer | null> {
  if (!query.trim()) return null;
  const user =
    (subject ? "Active subject: " + subject + "\n" : "") +
    "Question: " + query +
    "\n\nReturn ONLY JSON: {\"headline\":string,\"summary\":string,\"blocks\":[{\"type\":\"point\"|\"risk\"|\"takeaway\",\"title\":string,\"body\":string}],\"citations\":[{\"label\":string,\"time\":string}],\"followups\":[string]}";
  const out = safeParse(
    await chat([
      { role: "system", content: SYSTEM_PROMPT + "\n\n" + RETRIEVAL_PACK },
      { role: "user", content: user },
    ]),
  );
  if (!out || typeof out.headline !== "string" || !Array.isArray(out.blocks)) return null;
  const types = ["point", "data", "macro", "context", "risk", "takeaway", "DATA", "POINT", "MACRO", "CONTEXT", "RISK", "TAKEAWAY"];
  return {
    headline: String(out.headline),
    summary: String(out.summary ?? ""),
    blocks: out.blocks
      .filter((b: any) => b && b.title)
      .map((b: any) => ({ type: types.includes(b.type) ? b.type : "point", title: String(b.title), body: String(b.body ?? "") })),
    citations: Array.isArray(out.citations) ? out.citations.map((c: any) => ({ label: String(c.label ?? "source"), time: String(c.time ?? "") })) : [],
    followups: Array.isArray(out.followups) ? out.followups.map((f: any) => String(f)).slice(0, 4) : [],
    demo: false,
  };
}