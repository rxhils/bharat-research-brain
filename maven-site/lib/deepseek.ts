import type { ChatAnswer, MarketSnapshot } from "./types";
import { SYSTEM_PROMPT, RETRIEVAL_PACK, explainSystem } from "./india-context";

// Server-only DeepSeek client (OpenAI-compatible). Reads the key from the env at call
// time so it is NEVER bundled to the client. Returns null on missing key or any error
// so callers fall back to the mock - the app never breaks.
export function deepseekEnabled(): boolean {
  return !!process.env.DEEPSEEK_API_KEY;
}

async function chat(messages: { role: string; content: string }[], maxTokens = 900): Promise<string | null> {
  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) return null;
  const base = (process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com").replace(/\/$/, "");
  // V4 Pro is the research default; "deepseek-chat" is deprecated (sunset 2026-07-24).
  // Override with DEEPSEEK_MODEL (e.g. deepseek-v4-flash for the fast path).
  const model = process.env.DEEPSEEK_MODEL || "deepseek-v4-pro";
  try {
    const r = await fetch(base + "/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
      body: JSON.stringify({
        model,
        messages,
        temperature: 0.3,
        max_tokens: maxTokens,
        response_format: { type: "json_object" },
      }),
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
    "\n\nReturn ONLY JSON: {\"verdict\":{\"label\":string,\"tone\":\"constructive\"|\"neutral\"|\"cautious\"}," +
    "\"headline\":string,\"summary\":string," +
    "\"blocks\":[{\"type\":\"data\"|\"point\"|\"risk\"|\"trigger\"|\"takeaway\",\"title\":string,\"body\":string}]," +
    "\"citations\":[{\"label\":string,\"time\":string}],\"followups\":[string]}. " +
    "Include key numbers as 'data' blocks, drivers as 'point', risks as 'risk', what-would-change-the-view as 'trigger', and end with one 'takeaway'.";
  const out = safeParse(
    await chat([
      { role: "system", content: SYSTEM_PROMPT + "\n\n" + RETRIEVAL_PACK },
      { role: "user", content: user },
    ]),
  );
  if (!out || typeof out.headline !== "string" || !Array.isArray(out.blocks)) return null;
  const types = ["data", "point", "risk", "trigger", "takeaway"];
  const tones = ["constructive", "neutral", "cautious"];
  const verdict =
    out.verdict && out.verdict.label
      ? { label: String(out.verdict.label), tone: tones.includes(out.verdict.tone) ? out.verdict.tone : "neutral" }
      : undefined;
  return {
    verdict,
    headline: String(out.headline),
    summary: String(out.summary ?? ""),
    blocks: out.blocks
      .filter((b: any) => b && b.title)
      .map((b: any) => ({ type: types.includes(b.type) ? b.type : "point", title: String(b.title), body: String(b.body ?? "") })),
    citations: Array.isArray(out.citations)
      ? out.citations.map((c: any) => ({ label: String(c.label ?? "source"), time: String(c.time ?? "") }))
      : [],
    followups: Array.isArray(out.followups) ? out.followups.map((f: any) => String(f)).slice(0, 4) : [],
    demo: false,
  };
}

export type Reason = { title: string; body: string };

export async function deepseekExplain(snap: MarketSnapshot): Promise<Reason[] | null> {
  const ctx =
    "Indices: " +
    snap.indices.map((i) => i.label + " " + (i.changePct != null ? i.changePct.toFixed(2) + "%" : "NA")).join(", ") +
    ". Top sectors: " +
    snap.sectors.slice(0, 6).map((s) => s.name + " " + s.changePct.toFixed(2) + "%").join(", ") +
    ".";
  const out = safeParse(
    await chat(
      [
        { role: "system", content: explainSystem() },
        { role: "user", content: ctx + "\n\nReturn ONLY JSON {\"reasons\":[{\"title\":string,\"body\":string}]} with 3-5 reasons." },
      ],
      600,
    ),
  );
  if (!out || !Array.isArray(out.reasons)) return null;
  return out.reasons
    .filter((r: any) => r && r.title)
    .map((r: any) => ({ title: String(r.title), body: String(r.body ?? "") }))
    .slice(0, 5);
}