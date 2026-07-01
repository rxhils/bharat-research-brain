export type ComponentClass = "A" | "B" | "C" | "Cprime" | "D" | "E" | "F" | "G";

export type NodeStatus =
  | "waiting" | "running" | "progress" | "completed" | "published"
  | "failed" | "retrying" | "blocked" | "approval_required" | "pending" | "skipped";

export interface RegistryNode {
  node_id: string;
  name: string;
  component_class: ComponentClass;
  component_type: string;
  intelligent: boolean;
  external: boolean;
  in_graph: boolean;
  actual_component: string;
  role: string;
  order: number;
}

export interface RunNode {
  node_id: string;
  node_name: string;
  component_class: ComponentClass;
  component_type: string;
  intelligent: boolean;
  actual_component: string;
  external: number | boolean;
  in_graph: number | boolean;
  role: string;
  status: NodeStatus | string;
  ord: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  retry_count: number;
  progress: number;
  input_artifact: string | null;
  output_artifact: string | null;
  summary: string | null;
  error: string | null;
}

export interface Scores {
  job_id: string;
  content_score: number | null;
  design_score: number | null;
  compliance_score: number | null;
  aesthetic_score: number | null;
  brand_score: number | null;
  publish_allowed: number | null;
  issues?: Record<string, string[]>;
}

export interface Job {
  job_id: string;
  run_type: string;
  date: string;
  status: string;
  current_node: string | null;
  market_status: string;
  scheduled_time: string;
  started_at: string | null;
  completed_at: string | null;
  approval_status: string | null;
  publish_status: string | null;
  instagram_post_id: string | null;
  instagram_post_url: string | null;
  summary: string | null;
  scores?: Scores | null;
  nodes?: RunNode[];
  thumbnails?: string[];
  artifact_count?: number;
}

export interface NewsEvent {
  event_id: string;
  seq: number;
  job_id: string;
  node_id: string;
  node_name: string;
  actual_component: string;
  component_class: ComponentClass | "";
  component_type: string;
  intelligent: number | boolean;
  event_type: string;
  status: string;
  message: string;
  progress: number;
  payload?: Record<string, unknown>;
  artifact_refs?: string[];
  timestamp: string;
}

export interface Artifact {
  artifact_id: string;
  job_id: string;
  node_id: string;
  artifact_type: "json" | "image" | "video" | "audio" | "log";
  name: string;
  path: string;
  preview_url: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface Meta {
  product: string;
  subtitle: string;
  date_ist: string;
  market: { open: boolean; reason: string };
  next_run: string;
  run_name: string;
  trigger_agent: string;
  thresholds: { content: number; design: number; compliance: number };
}
