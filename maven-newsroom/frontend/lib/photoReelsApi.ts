/** API client + types for the Native Photo Reel Slides framework
 *  (/api/photo-reels). Isolated from carousel and legacy reels clients. */
import { API_BASE } from "./constants";

export type PhotoReelsConfig = {
  module: string;
  enabled: boolean;
  primary_reels_mode: string;
  default_publish_mode: string;
  publish_modes: string[];
  allow_auto_reel_video_mode: boolean;
  legacy_reels_ui_enabled: boolean;
  legacy_reels_cron_enabled: boolean;
  reel_image_slides_cron_enabled: boolean;
  require_higgsfield_credit_confirmation: boolean;
  slide_count: number;
  slide_size: [number, number];
  styles: string[];
  pipeline_stages: { key: string; name: string }[];
};

export type Slide = {
  slide_number: number;
  role: string;
  title: string;
  body: string;
  visual_direction: string;
  source_note: string;
};

export type SlideImage = {
  slide_number: number;
  path: string;
  status: string;
  background_source: string;
  width: number;
  height: number;
  layout?: string;
  motif?: string;
  visual_elements?: string[];
};

export type DesignJudge = {
  passed?: boolean;
  overall_score?: number;
  scores?: Record<string, number>;
  issues?: string[];
  required_fixes?: string[];
  too_plain?: boolean;
};

export type ViralAudioPick = {
  title: string; artist: string; platform: string; why: string;
  match_score: number; business_safe: boolean; freshness: string;
  how_to_use: string;
};

export type DesignAction =
  | "make_more_visual" | "add_finance_graphic" | "change_motif"
  | "regenerate_background" | "redesign_layout" | "make_cover_stronger";

export type PackageDetail = {
  job_id: string;
  package: { status: string; permalink?: string | null; qa_passed?: boolean };
  data_mode?: string;
  top_sectors_or_themes: string[];
  selected_story: {
    headline?: string; summary?: string; sector_or_theme?: string;
    sources?: { name: string; url: string }[]; simulated?: boolean;
  };
  why_selected: string;
  slides: Slide[];
  caption: string;
  hashtags: string[];
  slide_prompts: { slide_number: number; model: string; prompt: string }[];
  generated_images: SlideImage[];
  style?: string;
  design_options?: Record<string, unknown>;
  design_judge?: DesignJudge;
  qa: {
    passed?: boolean; overall_score?: number;
    scores?: Record<string, number>; issues?: string[];
    required_fixes?: string[];
  };
  export: {
    status?: string; zip_path?: string; image_paths?: string[];
    cover_image?: string;
  };
  music: {
    music_source?: string; mood?: string; search_terms?: string[];
    tempo?: string; note?: string;
  };
  viral_audio?: {
    picks?: ViralAudioPick[];
    primary_pick?: ViralAudioPick | null;
    live_status?: string;
    registry_last_refreshed?: string | null;
    registry_stale?: boolean;
    compliance_note?: string;
  };
  instagram_manual_steps: string[];
  stages: Record<string, { name: string; done: boolean; status?: string | null }>;
  video_render?: { video_path?: string; duration_seconds?: number } | null;
};

export type PackageSummary = {
  job_id: string;
  status: string;
  headline?: string | null;
  qa_passed?: boolean | null;
  qa_score?: number | null;
  permalink?: string | null;
  created: string;
};

const B = `${API_BASE}/api/photo-reels`;

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const post = (path: string, body?: unknown) =>
  fetch(`${B}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });

export const photoReelsApi = {
  config: () => fetch(`${B}/config`).then((r) => j<PhotoReelsConfig>(r)),
  packages: () =>
    fetch(`${B}/packages`).then((r) => j<{ packages: PackageSummary[] }>(r)),
  latest: () => fetch(`${B}/packages/latest`).then((r) => j<PackageDetail>(r)),
  package: (id: string) =>
    fetch(`${B}/packages/${id}`).then((r) => j<PackageDetail>(r)),
  run: (opts?: {
    research_only?: boolean; allow_simulation?: boolean; style?: string;
    use_higgsfield?: boolean; credit_confirmed?: boolean;
  }) => post("/run", opts).then((r) => j<Record<string, unknown>>(r)),
  /** Launch a live SIMULATION of the photo-Reel agent pipeline (dashboard
   *  orchestrator). Emits events on the shared bus; never publishes. */
  simulate: () =>
    post("/simulate").then((r) => j<{ job_id: string; status: string }>(r)),
  stopCron: () => post("/cron/stop").then((r) => j<Record<string, unknown>>(r)),
  generateImages: (id: string, opts?: {
    use_higgsfield?: boolean; credit_confirmed?: boolean; style?: string;
  }) => post(`/packages/${id}/generate-images`, opts)
    .then((r) => j<Record<string, unknown>>(r)),
  regenerateSlide: (id: string, n: number, opts?: {
    title?: string; body?: string; style?: string;
  }) => post(`/packages/${id}/slides/${n}/regenerate`, opts)
    .then((r) => j<Record<string, unknown>>(r)),
  decision: (id: string, decision: "approve" | "reject" | "revise", reason?: string) =>
    post(`/packages/${id}/decision`, { decision, reason })
      .then((r) => j<Record<string, unknown>>(r)),
  refreshViralAudio: (id: string) =>
    post(`/packages/${id}/viral-audio/refresh`)
      .then((r) => j<Record<string, unknown>>(r)),
  designAction: (id: string, action: DesignAction, slide?: number) =>
    post(`/packages/${id}/design-action`, { action, slide })
      .then((r) => j<Record<string, unknown>>(r)),
  exportImages: (id: string) =>
    post(`/packages/${id}/export`).then((r) => j<Record<string, unknown>>(r)),
  markPosted: (id: string, permalink?: string) =>
    post(`/packages/${id}/mark-posted`, { permalink })
      .then((r) => j<Record<string, unknown>>(r)),
  renderVideo: (id: string) =>
    post(`/packages/${id}/render-video`).then((r) => j<Record<string, unknown>>(r)),
  slideUrl: (id: string, n: number) => `${B}/packages/${id}/slides/${n}.png`,
  zipUrl: (id: string) => `${B}/packages/${id}/zip`,
};
