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
  // reels studio
  reelCapabilities: () => get<{
    research_provider_available: boolean; research_providers: string[];
    llm_provider_available: boolean; llm_api_configured: boolean; content_engine: string;
    higgsfield_available: boolean;
    higgsfield_transport: "cli" | "rest" | "none";
    higgsfield_cli_installed: boolean; higgsfield_logged_in: boolean;
    tts_available: boolean; tts_mode: string;
    voiceover_production_ready: boolean; composio_available: boolean; ffmpeg_available: boolean;
    can_run_full_reel_from_backend: boolean; can_generate_real_clips: boolean;
    generation_mode: "real" | "simulation";
    missing: { capability: string; message: string }[];
  }>("/api/reels/capabilities"),
  reelGenerate: (id: string, simulate?: boolean) =>
    post<{ status: string; verdict?: string; preview_ready?: boolean; production_ready?: boolean; generation_mode?: string; scores?: any }>(`/api/reels/${id}/generate`, { simulate }),
  reelsLatest: () => get<{ job_id: string; status: string; created_at: string; version: number; parent_job_id: string | null; review_url: string; scores: Scores | null; stale: { stale: boolean; problems: string[] }; approval_status: string; publish_status: string }>("/api/reels/latest"),
  reelFeedback: (id: string, feedback_type: string, custom_feedback?: string) => post(`/api/jobs/${id}/feedback`, { feedback_type, custom_feedback }),
  reelImprove: (id: string, feedback_type: string, custom_feedback?: string) => post<{ status: string; new_job_id?: string; version?: number; review_url?: string; message?: string; needs?: string[] }>(`/api/jobs/${id}/improve`, { feedback_type, custom_feedback }),
  reelVersions: (id: string) => get<{ root_job_id: string; versions: any[]; feedback: any[] }>(`/api/jobs/${id}/versions`),
  // higgsfield-primary renderer
  reelClips: (id: string) => get<{ job_id: string; generation_status: string; approved_from_ui: boolean; estimated_cost_credits: number | null; actual_cost_credits: number | null; planned: any[]; clips: any[]; clips_on_disk: string[] }>(`/api/reels/${id}/clips`),
  approveGeneration: (id: string) => post<{ status: string; verdict?: string; preview_ready?: boolean; production_ready?: boolean; generation_mode?: string; scores?: any }>(`/api/reels/${id}/approve-generation`),
  regenerateScene: (id: string, shotId: string) => post(`/api/reels/${id}/regenerate-scene/${shotId}`),
  regenerateAllScenes: (id: string) => post(`/api/reels/${id}/regenerate-all-scenes`),
  improveAnimation: (id: string) => post<{ status: string; shots: number; estimated_cost_credits: number; message: string }>(`/api/reels/${id}/improve-animation`),
  reassembleReel: (id: string) => post<{ status: string; verdict?: string; scores?: any }>(`/api/reels/${id}/reassemble`),
  improveText: (id: string, action = "improve_text", moveUp = false) =>
    post<{ status: string; action?: string; verdict?: string; text_verdict?: string; text_scores?: any; scores?: any; credits_spent?: number; message?: string }>(
      `/api/reels/${id}/improve-text`, { action, move_subtitles_up: moveUp }),
  // pipeline diagram: free re-plan (no credits) + full-stack produce (gated)
  replan: (id: string) => post<{ status: string; selected_format?: string; format_hook?: string; format_hook_score?: number; hook_lab_blocked?: boolean; saveable_lesson?: string; script_blocked?: boolean; chosen_variant?: string; visual_pack?: string; watch_through_passed?: boolean; visual_taste_status?: string; verdict?: string }>(`/api/reels/${id}/replan`),
  produce: (id: string, confirm = false, simulate?: boolean) =>
    post<{ status: string; mode?: string; verdict?: string; scores?: any; production?: any }>(`/api/reels/${id}/produce`, { confirm, simulate }),
  approveAndPublish: (id: string) => post(`/api/reels/${id}/approve-publish`),
  reject: (id: string, reason?: string) => post(`/api/jobs/${id}/reject`, { reason }),
  publish: (id: string) => post(`/api/jobs/${id}/publish`),
  updateSettings: (patch: unknown) => post("/api/settings", patch),
};
