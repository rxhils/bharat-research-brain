import { API_BASE } from "./constants";
import type { NewsroomReelsStatus } from "./newsroomReelsTypes";

/** Isolated API client for the Newsroom Reels module (/api/newsroom-reels/*).
 * Never calls the existing /api/reels/* (Higgsfield) endpoints. */
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}

export const newsroomReelsApi = {
  status: () => get<NewsroomReelsStatus>("/api/newsroom-reels/status"),
  runs: () => get<{ runs: any[] }>("/api/newsroom-reels/runs"),
  createRun: () => post<any>("/api/newsroom-reels/runs"),
  reels: () => get<{ reels: any[] }>("/api/newsroom-reels/reels"),
  decision: (renderId: string, decision: "approve" | "reject" | "revise", reason?: string) =>
    post<any>(`/api/newsroom-reels/reels/${renderId}/decision`, { decision, reason }),
  videoUrl: (renderId: string) => `${API_BASE}/api/newsroom-reels/reels/${renderId}/video`,
  queues: () => get<{ queues: any[] }>("/api/newsroom-reels/queues"),
  agents: () => get<{ agents: any[] }>("/api/newsroom-reels/agents"),
};
