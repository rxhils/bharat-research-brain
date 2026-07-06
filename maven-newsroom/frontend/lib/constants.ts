import type { ComponentClass, NodeStatus } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/** Legacy Reels frameworks are HIDDEN (not deleted) — rebuilt as Native
 *  Photo Reel Slides. Flip to true only to debug the old pages. */
export const LEGACY_REELS_UI_ENABLED = false;

type NavGroup = {
  label: string;
  items: readonly { href: string; label: string; icon: string }[];
};

const CAROUSEL_GROUP: NavGroup = {
  label: "Carousel",
  items: [
    { href: "/dashboard", label: "Dashboard", icon: "LayoutDashboard" },
    { href: "/run", label: "Live Run", icon: "Activity" },
    { href: "/research", label: "Research Room", icon: "Newspaper" },
    { href: "/creative", label: "Creative Studio", icon: "Palette" },
    { href: "/review", label: "Review Room", icon: "ClipboardCheck" },
    { href: "/publish", label: "Publish Console", icon: "Send" },
    { href: "/archive", label: "Run Archive", icon: "Archive" },
  ],
};

const LEGACY_REELS_GROUPS: NavGroup[] = [
  {
    label: "Reels",
    items: [
      { href: "/reels", label: "Reels", icon: "Clapperboard" },
      { href: "/reels/run", label: "Reel Run", icon: "Activity" },
      { href: "/reels/research", label: "Research & Fit", icon: "Newspaper" },
      { href: "/reels/hooks", label: "Hooks & Angle", icon: "Zap" },
      { href: "/reels/script", label: "Script", icon: "FileText" },
      { href: "/reels/storyboard", label: "Storyboard", icon: "Film" },
      { href: "/reels/review", label: "Reel Review", icon: "ClipboardCheck" },
      { href: "/reels/publish", label: "Reel Publish", icon: "Send" },
      { href: "/reels/archive", label: "Reel Archive", icon: "Archive" },
    ],
  },
  {
    label: "Newsroom Reels",
    items: [
      { href: "/newsroom/reels", label: "Newsroom Reels", icon: "Clapperboard" },
    ],
  },
];

const PHOTO_REELS_GROUP: NavGroup = {
  label: "Photo Reels",
  items: [
    { href: "/newsroom/reels/slides", label: "Dashboard", icon: "LayoutDashboard" },
    { href: "/newsroom/reels/slides/run", label: "Daily Run", icon: "Activity" },
    { href: "/newsroom/reels/slides/studio", label: "Slide Studio", icon: "Palette" },
    { href: "/newsroom/reels/slides/review", label: "Review", icon: "ClipboardCheck" },
    { href: "/newsroom/reels/slides/export", label: "Export", icon: "Download" },
    { href: "/newsroom/reels/slides/archive", label: "Archive", icon: "Archive" },
  ],
};

const SYSTEM_GROUP: NavGroup = {
  label: "System",
  items: [{ href: "/settings", label: "Settings", icon: "Settings" }],
};

export const NAV_GROUPS: readonly NavGroup[] = [
  CAROUSEL_GROUP,
  ...(LEGACY_REELS_UI_ENABLED ? LEGACY_REELS_GROUPS : []),
  PHOTO_REELS_GROUP,
  SYSTEM_GROUP,
];

/** status -> {label, dot color, text color, ring} */
export const STATUS: Record<string, { label: string; color: string; text: string; ring: string }> = {
  waiting:           { label: "Waiting",   color: "#5B6B7E", text: "text-ink-faint",  ring: "border-line" },
  running:           { label: "Running",   color: "#1FB6A6", text: "text-teal",       ring: "border-teal/50" },
  progress:          { label: "Working",   color: "#1FB6A6", text: "text-teal",       ring: "border-teal/50" },
  completed:         { label: "Completed", color: "#27C281", text: "text-ok",         ring: "border-ok/40" },
  published:         { label: "Published", color: "#27C281", text: "text-ok",         ring: "border-ok/60" },
  failed:            { label: "Failed",    color: "#EF4444", text: "text-danger",     ring: "border-danger/50" },
  retrying:          { label: "Retrying",  color: "#F2994A", text: "text-warn",       ring: "border-warn/50" },
  blocked:           { label: "Blocked",   color: "#3B82F6", text: "text-info",       ring: "border-info/50" },
  approval_required: { label: "Approval",  color: "#3B82F6", text: "text-info",       ring: "border-info/50" },
  pending:           { label: "Pending",   color: "#8B5CF6", text: "text-mcp",        ring: "border-mcp/50" },
  skipped:           { label: "Skipped",   color: "#5B6B7E", text: "text-ink-faint",  ring: "border-line" },
  awaiting_approval: { label: "Approval",  color: "#3B82F6", text: "text-info",       ring: "border-info/50" },
  ingested:          { label: "Ingested",  color: "#27C281", text: "text-ok",         ring: "border-ok/40" },
};

export function statusMeta(s: string) {
  return STATUS[s] || STATUS.waiting;
}

export const CLASS_LABEL: Record<ComponentClass, string> = {
  A: "LLM Research Agent",
  B: "Deterministic Module",
  C: "External Generative MCP",
  Cprime: "Local DSP / Video",
  D: "External API Courier",
  E: "Orchestrator / State",
  F: "Claude Code Conductor",
  G: "Scheduled Run",
};

export const CLASS_ACCENT: Record<ComponentClass, string> = {
  A: "#22D3EE", B: "#94A3B8", C: "#8B5CF6", Cprime: "#1FB6A6",
  D: "#8B5CF6", E: "#3B82F6", F: "#27C281", G: "#F2994A",
};

export const TERMINAL_STATES = new Set(["completed", "published", "skipped", "failed"]);

export function isExternal(n: { external: number | boolean }) {
  return n.external === true || n.external === 1;
}
