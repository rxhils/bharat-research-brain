import { API_BASE } from "./constants";
import type { Artifact, Job, Meta, NewsEvent, RegistryNode, RunNode, Scores } from "./types";

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
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(`POST ${path} -> ${res.status}`), { status: res.status, data });
  return data as T;
}

export const api = {
  base: API_BASE,
  health: () => get<{ status: string; db: Record<string, number> }>("/api/health"),
  meta: () => get<Meta>("/api/meta"),
  registry: (pipeline?: "carousel" | "reel") =>
    get<{ nodes: RegistryNode[]; graph_order: string[]; class_labels: Record<string, string> }>(
      `/api/nodes${pipeline ? `?pipeline=${pipeline}` : ""}`),
  jobs: (pipeline?: "carousel" | "reel") =>
    get<{ jobs: Job[] }>(`/api/jobs${pipeline ? `?pipeline=${pipeline}` : ""}`),
  job: (id: string) => get<Job>(`/api/jobs/${id}`),
  nodes: (id: string) => get<{ nodes: RunNode[] }>(`/api/jobs/${id}/nodes`),
  events: (id: string, afterSeq = 0) => get<{ events: NewsEvent[] }>(`/api/jobs/${id}/events?after_seq=${afterSeq}`),
  artifacts: (id: string) => get<{ artifacts: Artifact[] }>(`/api/jobs/${id}/artifacts`),
  scores: (id: string) => get<Scores>(`/api/jobs/${id}/scores`),
  artifactUrl: (id: string, name: string) => `${API_BASE}/api/jobs/${id}/artifact/${name}`,
  settings: () => get<Record<string, unknown>>("/api/settings"),
  // actions
  run: (date?: string) => post<{ job_id: string; status: string; reason?: string }>("/api/run", { date }),
  runReel: (date?: string) => post<{ job_id: string; status: string; reason?: string }>("/api/run", { date, pipeline: "reel" }),
  rerun: (id: string, node: string) => post(`/api/jobs/${id}/rerun/${node}`),
  rerunFrom: (id: string, node: string) => post(`/api/jobs/${id}/rerun-from/${node}`),
  regenerateImages: (id: string) => post(`/api/jobs/${id}/regenerate-images`),
  rewriteCaption: (id: string) => post(`/api/jobs/${id}/rewrite-caption`),
  recheckQuality: (id: string) => post(`/api/jobs/${id}/recheck-quality`),
  telegramPreview: (id: string) => post<{ status: string; delivered: boolean; token_configured: boolean; preview_url: string | null; message: string; paid_higgsfield_used?: boolean; template?: string | null }>(`/api/jobs/${id}/telegram-preview`),
  requestHiggsfield: (id: string, approved = false) => post<{ status: string; paid: boolean; message: string; allow_paid_generation?: boolean }>(`/api/jobs/${id}/request-higgsfield`, { approved }),
  approve: (id: string) => post(`/api/jobs/${id}/approve`),
  reject: (id: string, reason?: string) => post(`/api/jobs/${id}/reject`, { reason }),
  publish: (id: string) => post(`/api/jobs/${id}/publish`),
  updateSettings: (patch: unknown) => post("/api/settings", patch),
};
