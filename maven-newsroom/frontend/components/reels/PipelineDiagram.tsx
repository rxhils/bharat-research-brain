"use client";
import { useCallback, useEffect, useState } from "react";
import { GitBranch, ChevronDown, RefreshCw, Sparkles, AlertTriangle, Lock } from "lucide-react";
import { api } from "@/lib/api";

/** Maven Reels Pipeline diagram — PLAN (free) → PRODUCE (paid/gated) → PUBLISH + LEARN.
 *  Read-only visibility: node statuses map from on-disk artifacts. The only
 *  writes are explicit button actions (free re-plan, or paid actions behind a
 *  confirmation modal). No credits are ever spent without confirm. */

type Status = "not_started" | "running" | "passed" | "blocked" | "review_required" | "failed";

const SS: Record<Status, { dot: string; text: string; ring: string; label: string }> = {
  passed:          { dot: "bg-ok",     text: "text-ok",     ring: "border-ok/40 bg-ok/[0.06]",       label: "passed" },
  review_required: { dot: "bg-warn",   text: "text-warn",   ring: "border-warn/40 bg-warn/[0.06]",   label: "review" },
  blocked:         { dot: "bg-danger", text: "text-danger", ring: "border-danger/40 bg-danger/[0.06]", label: "blocked" },
  failed:          { dot: "bg-danger", text: "text-danger", ring: "border-danger/40 bg-danger/[0.06]", label: "failed" },
  running:         { dot: "bg-teal",   text: "text-teal",   ring: "border-teal/40 bg-teal/[0.06]",   label: "running" },
  not_started:     { dot: "bg-white/20", text: "text-ink-faint", ring: "border-line",                label: "—" },
};

type NodeDef = {
  key: string; label: string; file: string; paid?: boolean;
  status: (a: any, ctx: Ctx) => Status;
  summary?: (a: any) => string;
  score?: (a: any) => number | undefined;
  blockReason?: (a: any) => string | undefined;
  reroute?: (a: any) => string | undefined;
  detail?: (a: any) => React.ReactNode;
};
type Ctx = { publishStatus?: string | null; hasReel: boolean };

const has = (a: any) => a && typeof a === "object";
const num = (v: any) => (typeof v === "number" ? v : undefined);

/* ------------------------------- PLAN (free) ------------------------------- */
const PLAN: NodeDef[] = [
  { key: "sentinel", label: "Market Sentinel", file: "01_research.json",
    status: (a) => !has(a) ? "not_started" : (a.research_status === "failed" ? "failed" : "passed"),
    summary: (a) => `${(a?.stories?.length ?? a?.candidates?.length ?? 0)} stories · ${a?.data_mode ?? a?.data_window ?? "—"}` },
  { key: "dup", label: "Duplicate Check", file: "02_duplicate_check.json",
    status: (a) => !has(a) ? "not_started" : (a.duplicate_risk === "high" ? "blocked" : "passed"),
    summary: (a) => `risk: ${a?.duplicate_risk ?? "—"}` },
  { key: "storygate", label: "Story Gate", file: "02_viral_fit.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `fit ${a?.chosen?.viral_fit ?? "—"}` },
  { key: "format", label: "Story + Format Selector", file: "35_story_format.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `${a?.selected_format_name ?? a?.selected_format ?? "—"}`,
    detail: (a) => (
      <DL rows={[
        ["Selected format", a?.selected_format_name],
        ["Why it can go viral", a?.why_this_format_can_go_viral],
        ["Save reason", a?.save_reason], ["Share reason", a?.share_reason],
        ["Compliance risk", a?.compliance_risk],
      ]} />) },
  { key: "director", label: "Format Director", file: "36_format_director.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => a?.first_frame ? String(a.first_frame).slice(0, 40) : "—" },
  { key: "variants", label: "3-Variant Blueprint Lab", file: "37_reel_variants.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `winner ${a?.chosen_variant ?? "—"} · ${(a?.variants?.length ?? 0)} variants`,
    detail: (a) => (
      <div className="space-y-1.5">
        {(a?.variants ?? []).map((v: any) => (
          <div key={v.variant} className={`flex items-center gap-2 rounded border px-2 py-1 ${v.variant === a.chosen_variant ? "border-teal/40 bg-teal/[0.06]" : "border-line"}`}>
            <span className="chip border-line">{v.variant}</span>
            <span className="text-ink truncate flex-1">{v.hook}</span>
            <span className="text-ink-faint">score {v.viral_score}</span>
            <span className="text-mcp">~{v.estimated_cost_credits}cr</span>
            {v.variant === a.chosen_variant && <span className="chip border-teal/40 text-teal">winner</span>}
          </div>
        ))}
        <div className="text-ink-faint">{a?.chosen_reason}</div>
      </div>) },
  { key: "hook", label: "Hook Lab", file: "38_hooks_format.json",
    status: (a) => !has(a) ? "not_started" : (a.hook_lab_blocked ? "blocked" : "passed"),
    summary: (a) => a?.selected_hook ? `"${a.selected_hook}"` : "—",
    score: (a) => num(a?.hook_score), blockReason: (a) => a?.blocked_reason,
    reroute: (a) => a?.hook_lab_blocked ? "Generate 3 New Variants / Improve Hook" : undefined,
    detail: (a) => (
      <div className="space-y-1.5">
        <DL rows={[["Selected hook", a?.selected_hook], ["Bucket", a?.hook_bucket],
          ["Score", `${a?.hook_score} (min ${a?.min_required})`]]} />
        {a?.hook_lab_blocked && <div className="text-danger">⚠ {a.blocked_reason}</div>}
        {Array.isArray(a?.backup_hooks) && (
          <details><summary className="cursor-pointer text-ink-faint">backup hooks</summary>
            <ul className="mt-1 space-y-0.5">{a.backup_hooks.map((h: any, i: number) =>
              <li key={i} className="text-ink-muted">• {h.hook} <span className="text-ink-faint">({h.bucket} {h.score})</span></li>)}</ul>
          </details>)}
      </div>) },
  { key: "script", label: "Scriptroom", file: "39_script_saveable.json",
    status: (a) => !has(a) ? "not_started" : (a.script_blocked ? "blocked" : "passed"),
    summary: (a) => a?.saveable_lesson ? `lesson: ${a.saveable_lesson}` : "—",
    blockReason: (a) => a?.blocked_reason, reroute: (a) => a?.script_blocked ? "story not Reel-worthy today" : undefined,
    detail: (a) => (
      <DL rows={[["Narration", a?.narration], ["Saveable lesson", a?.saveable_lesson],
        ["Mental model", a?.saveable_lesson_key], ["Words", a?.word_count],
        ...(a?.script_blocked ? [["Blocked", a?.blocked_reason] as [string, any]] : [])]} />) },
  { key: "pack", label: "Visual Pack Scout", file: "40_visual_pack.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => a?.pack?.name ?? a?.selected_pack ?? "—",
    detail: (a) => (
      <DL rows={[["Pack", a?.pack?.name], ["Environment", a?.pack?.environment],
        ["Palette", a?.pack?.palette], ["Why it fits", a?.why_this_pack]]} />) },
  { key: "popup", label: "Popup Planner", file: "41_popup_plan.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `${(a?.cards?.length ?? 0)} cards` },
  { key: "watch", label: "Watch-Through Editor", file: "42_watch_through.json",
    status: (a) => !has(a) ? "not_started" : (a.passed ? "passed" : "review_required"),
    summary: (a) => a?.verdict ?? "—", blockReason: (a) => !a?.passed ? a?.verdict : undefined,
    detail: (a) => (
      <div className="space-y-1">
        {(a?.checkpoints ?? []).map((c: any, i: number) => (
          <div key={i} className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${c.pass ? "bg-ok" : "bg-danger"}`} />
            <span className="text-ink-faint w-10">{typeof c.at_s === "number" ? `${c.at_s}s` : c.at_s}</span>
            <span className="text-ink-muted flex-1">{c.question}</span>
            <span className="text-ink-faint truncate max-w-[40%]">{c.detail}</span>
          </div>))}
        {Array.isArray(a?.rewrite_beatboard) && a.rewrite_beatboard.length > 0 &&
          <div className="text-warn mt-1">rewrite: {a.rewrite_beatboard.join("; ")}</div>}
      </div>) },
  { key: "blueprint", label: "Higgsfield Blueprint", file: "31_higgsfield_blueprint.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `${(a?.scenes?.length ?? 0)} scenes · ${a?.text_driver ?? "—"}`,
    detail: (a) => (
      <div className="space-y-1">
        {(a?.scenes ?? []).map((s: any) => (
          <div key={s.scene_id} className="flex items-center gap-2">
            <span className="text-ink-faint w-14">{s.scene_id}</span>
            <span className={`chip ${s.requires_text_fidelity ? "border-teal/40 text-teal" : "border-line"}`}>{s.scene_type}</span>
            {s.exact_text ? <span className="text-ink truncate">"{s.exact_text}"</span>
              : <span className="text-ink-faint truncate">{s.voiceover_line}</span>}
          </div>))}
      </div>) },
  { key: "prouter", label: "Production Router", file: "32_production_routing.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `${(a?.routes?.length ?? 0)} scenes routed`,
    detail: (a) => (
      <div className="space-y-1">
        {(a?.routes ?? []).map((r: any) => (
          <div key={r.scene_id} className="flex items-center gap-2">
            <span className="text-ink-faint w-14">{r.scene_id}</span>
            <span className="text-ink">{r.selected_model_or_tool}</span>
            <span className="text-mcp ml-auto">confirm before spend</span>
          </div>))}
        {a?.excluded && <div className="text-ink-faint mt-1">excluded: {(a.excluded || []).slice(0, 3).join(", ")}</div>}
      </div>) },
  { key: "prompts", label: "Production Prompts", file: "33_production_prompts.json",
    status: (a) => !has(a) ? "not_started" : "passed",
    summary: (a) => `${(a?.prompts?.length ?? 0)} prompts` },
];

/* ---------------------------- PRODUCE (paid) ------------------------------- */
const PRODUCE: NodeDef[] = [
  { key: "agent", label: "Production Agent", file: "34_production_result.json", paid: true,
    status: (a) => !has(a) ? "not_started" : (a.mode === "blocked" ? "blocked" : a.mode === "production" ? "passed" : "passed"),
    summary: (a) => a?.mode === "blocked" ? "needs UI confirmation" : `${a?.mode ?? "—"} · ${(a?.text_cards?.length ?? 0)} cards`,
    blockReason: (a) => a?.mode === "blocked" ? "real production requires localhost-UI confirmation" : undefined },
  { key: "editbay", label: "Edit Bay", file: "17_final_reel.json", paid: false,
    status: (a, ctx) => ctx.hasReel ? "passed" : (has(a) ? "passed" : "not_started"),
    summary: (_a, ) => "local stitch/mux" },
  { key: "sqi", label: "Scene Quality Inspector", file: "13_scene_quality.json",
    status: (a) => !has(a) ? "not_started" : (a.passed ? "passed" : "failed"),
    summary: (a) => a?.overall_scene_quality_score != null ? `${a.overall_scene_quality_score}/100` : "—",
    score: (a) => num(a?.overall_scene_quality_score) },
  { key: "svi", label: "Scene Vision Inspector", file: "30_scene_vision_inspection.json",
    status: (a) => !has(a) ? "not_started" : (a.vision_review_available ? (a.overall_passed ? "passed" : "review_required") : (a.vision_review_required ? "review_required" : "passed")),
    summary: (a) => `${a?.frames_extracted?.length ?? 0} frames` },
  { key: "taste", label: "Visual Taste Reviewer", file: "43_visual_taste.json",
    status: (a) => !has(a) ? "not_started" : (a.review_required ? "review_required" : a.passed ? "passed" : "failed"),
    summary: (a) => a?.review_required ? "review required (no vision model)" : (a?.passed ? "premium" : "gate failed"),
    blockReason: (a) => a?.review_required ? a?.note : (a?.passed === false ? a?.verdict : undefined),
    reroute: (a) => a?.reroute_to,
    detail: (a) => a?.review_available ? <DL rows={[
      ["Typography", a?.scores?.typography], ["First frame", a?.scores?.first_frame],
      ["Realism", a?.scores?.realism], ["Popup design", a?.scores?.popup_design],
      ["AI-slop risk", a?.scores?.ai_slop_risk], ["Verdict", a?.verdict]]} />
      : <div className="text-warn">{a?.note}</div> },
  { key: "eic", label: "Editor-in-Chief", file: "29_editor_in_chief.json",
    status: (a) => !has(a) ? "not_started" : (a.passed ? "passed" : "failed"),
    summary: (a) => a?.overall_score != null ? `overall ${a.overall_score}` : "—",
    score: (a) => num(a?.overall_score), reroute: (a) => a?.reroute_to,
    blockReason: (a) => !a?.passed && a?.required_fixes?.length ? a.required_fixes.join("; ") : undefined,
    detail: (a) => (
      <div className="space-y-1.5">
        <div className="flex flex-wrap gap-1">
          {Object.entries(a?.scores ?? {}).map(([k, v]: any) =>
            <span key={k} className="chip border-line">{k.replace(/_/g, " ")}: {v}</span>)}
        </div>
        {a?.required_fixes?.length > 0 && <div className="text-danger">fixes: {a.required_fixes.join("; ")}</div>}
        {a?.reroute_to && <div className="text-warn">reroute → {a.reroute_to}</div>}
      </div>) },
];

/* ------------------------- PUBLISH + LEARN --------------------------------- */
const PUBLISH: NodeDef[] = [
  { key: "courier", label: "Reels Courier", file: "", paid: true,
    status: (_a, ctx) => ctx.publishStatus === "published" ? "passed" : "not_started",
    summary: (_a) => "Instagram Reels + Story" },
  { key: "signal", label: "Signal Tracker", file: "",
    status: (_a, ctx) => ctx.publishStatus === "published" ? "review_required" : "not_started",
    summary: () => "real metrics after publish" },
  { key: "learn", label: "Learning Loop", file: "",
    status: (_a, ctx) => ctx.publishStatus === "published" ? "passed" : "not_started",
    summary: () => "metrics → format/hook/pack boosts" },
];

function DL({ rows }: { rows: [string, any][] }) {
  return (
    <dl className="space-y-1">
      {rows.filter(([, v]) => v != null && v !== "").map(([k, v]) => (
        <div key={k} className="grid grid-cols-[110px_1fr] gap-2">
          <dt className="text-ink-faint">{k}</dt><dd className="text-ink-muted">{String(v)}</dd>
        </div>))}
    </dl>);
}

export function PipelineDiagram({ jobId, publishStatus, hasReel }:
  { jobId: string; publishStatus?: string | null; hasReel: boolean }) {
  const [arts, setArts] = useState<Record<string, any>>({});
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const files = [...PLAN, ...PRODUCE, ...PUBLISH].map((n) => n.file).filter(Boolean);
  const load = useCallback(() => {
    files.forEach((f) => fetch(api.artifactUrl(jobId, f)).then((x) => x.ok ? x.json() : null)
      .then((d) => setArts((p) => ({ ...p, [f]: d }))).catch(() => {}));
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  const ctx: Ctx = { publishStatus, hasReel };
  const stOf = (n: NodeDef): Status => n.status(arts[n.file], ctx);

  // overall banner
  const planNodes = PLAN.map((n) => ({ n, s: stOf(n) }));
  const planBlocked = planNodes.find((x) => x.s === "blocked" || x.s === "failed");
  const planDone = PLAN.every((n) => stOf(n) !== "not_started") && !planBlocked;
  const agent = arts["34_production_result.json"];
  const taste = arts["43_visual_taste.json"];
  const eic = arts["29_editor_in_chief.json"];
  let banner = { text: "Planning in progress…", tone: "muted" as "muted" | "ok" | "warn" | "danger" | "teal" };
  if (planBlocked) {
    const why = planBlocked.n.blockReason?.(arts[planBlocked.n.file]);
    banner = { text: `Blocked before spending credits: ${why || planBlocked.n.label}`, tone: "danger" };
  } else if (publishStatus === "published") {
    banner = { text: "Published — learning metrics pending.", tone: "ok" };
  } else if (eic && eic.passed) {
    banner = { text: "Passed all gates — ready for approval.", tone: "ok" };
  } else if (taste?.review_required) {
    banner = { text: "Vision review required before publishing.", tone: "warn" };
  } else if (agent?.mode === "blocked") {
    banner = { text: "Generation requires UI confirmation.", tone: "teal" };
  } else if (planDone) {
    banner = { text: "Planning complete — ready for paid generation.", tone: "teal" };
  }
  const bTone = { ok: "border-ok/40 bg-ok/[0.06] text-ok", warn: "border-warn/40 bg-warn/[0.06] text-warn",
    danger: "border-danger/40 bg-danger/[0.06] text-danger", teal: "border-teal/40 bg-teal/[0.06] text-teal",
    muted: "border-line text-ink-muted" }[banner.tone];

  // why-blocked panel content
  const blocker = planNodes.find((x) => x.s === "blocked") ??
    (agent?.mode === "blocked" ? { n: PRODUCE[0], s: "blocked" as Status } : undefined) ??
    (taste?.review_required ? { n: PRODUCE.find((p) => p.key === "taste")!, s: "review_required" as Status } : undefined);

  const run = useCallback(async (key: string, label: string, paid: boolean, fn: () => Promise<any>) => {
    if (paid && !window.confirm("This may spend Higgsfield credits. Continue?")) return;
    setBusy(key); setToast(`${label}…`);
    try { const r = await fn(); setToast(`${label}: ${r?.status ?? r?.verdict ?? "done"}`); load(); }
    catch (e: any) { setToast(`${label} failed${e?.data ? ": " + JSON.stringify(e.data).slice(0, 80) : ""}`); }
    setBusy(null); setTimeout(() => setToast(null), 5000);
  }, [load]);

  const Node = ({ n }: { n: NodeDef }) => {
    const s = stOf(n); const a = arts[n.file]; const st = SS[s];
    const expandable = !!n.detail && s !== "not_started";
    return (
      <div className={`rounded-lg border ${st.ring} overflow-hidden`}>
        <button disabled={!expandable} onClick={() => setOpen(open === n.key ? null : n.key)}
          className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-left ${expandable ? "hover:bg-white/[0.02]" : "cursor-default"}`}>
          <span className={`w-2 h-2 rounded-full shrink-0 ${st.dot}`} />
          <span className="text-xs font-medium text-ink truncate">{n.label}</span>
          {n.paid && <Lock size={10} className="text-mcp shrink-0" />}
          {n.score?.(a) != null && <span className={`chip ${st.ring} ${st.text} shrink-0`}>{n.score!(a)}</span>}
          <span className={`ml-auto text-[10px] ${st.text} shrink-0`}>{st.label}</span>
          {expandable && <ChevronDown size={12} className={`shrink-0 transition-transform ${open === n.key ? "rotate-180" : ""}`} />}
        </button>
        {n.summary?.(a) && s !== "not_started" && (
          <div className="px-2.5 pb-1.5 text-[11px] text-ink-faint truncate">{n.summary(a)}</div>)}
        {open === n.key && expandable && (
          <div className="px-2.5 pb-2.5 pt-1 text-[11px] border-t border-line/60">{n.detail!(a)}</div>)}
      </div>);
  };

  const Phase = ({ title, tag, tagTone, nodes }: { title: string; tag: string; tagTone: string; nodes: NodeDef[] }) => (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <div className="text-xs font-semibold tracking-wide text-ink">{title}</div>
        <span className={`chip ${tagTone}`}>{tag}</span>
      </div>
      <div className="grid sm:grid-cols-2 gap-1.5">{nodes.map((n) => <Node key={n.key} n={n} />)}</div>
    </div>);

  return (
    <div className="glass card-pad space-y-4">
      <div className="eyebrow flex items-center gap-1.5"><GitBranch size={13} /> Maven Reels Pipeline</div>

      <div className={`rounded-lg border px-3 py-2 text-sm ${bTone}`}>{banner.text}</div>

      {blocker && (
        <div className="rounded-lg border border-danger/30 bg-danger/[0.04] px-3 py-2 text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-danger font-medium"><AlertTriangle size={12} /> Why blocked?</div>
          <div className="text-ink-muted">
            <b>{blocker.n.label}</b>: {blocker.n.blockReason?.(arts[blocker.n.file]) ?? "gate not cleared"}.
          </div>
          {blocker.n.reroute?.(arts[blocker.n.file]) && (
            <div className="text-ink-faint">Fix: {blocker.n.reroute!(arts[blocker.n.file])} — {blocker.n.paid ? <span className="text-mcp">paid</span> : <span className="text-ok">free</span>}.</div>)}
        </div>)}

      <div className="space-y-4">
        <Phase title="1 · PLAN" tag="Free · No Credits" tagTone="border-ok/40 text-ok bg-ok/10" nodes={PLAN} />
        <div className="flex items-center gap-2 text-[11px] text-mcp"><Lock size={11} /> Credits are only spent below, after every free gate above passes.</div>
        <Phase title="2 · PRODUCE" tag="Paid · UI-Gated" tagTone="border-mcp/40 text-mcp bg-mcp/10" nodes={PRODUCE} />
        <Phase title="3 · PUBLISH + LEARN" tag="Approval-gated" tagTone="border-teal/40 text-teal bg-teal/10" nodes={PUBLISH} />
      </div>

      {/* actions */}
      <div className="border-t border-line pt-3 space-y-2">
        <div className="eyebrow">Free planning actions</div>
        <div className="flex flex-wrap gap-1.5">
          {[["replan", "Re-run Plan"], ["variants", "Generate 3 New Variants"], ["hook", "Improve Hook"],
            ["script", "Rewrite Script"], ["pack", "Change Visual Pack"], ["watch", "Re-run Watch-Through"]].map(([k, l]) => (
            <button key={k} disabled={busy === k} onClick={() => run(k, l, false, () => api.replan(jobId))}
              className="btn btn-ghost border-line text-xs">
              {busy === k ? <RefreshCw size={13} className="animate-spin" /> : <RefreshCw size={13} />}{l}</button>))}
        </div>
        <div className="eyebrow mt-2 flex items-center gap-1.5"><Lock size={11} className="text-mcp" /> Paid / gated actions</div>
        <div className="flex flex-wrap gap-1.5">
          <button disabled={busy === "produce"} onClick={() => run("produce", "Confirm Higgsfield Generation", true, () => api.produce(jobId, true))}
            className="btn btn-ghost border-mcp/40 text-mcp text-xs">
            {busy === "produce" ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}Confirm Higgsfield Generation ⚠</button>
          <button disabled={busy === "regenall"} onClick={() => run("regenall", "Regenerate All Scenes", true, () => api.regenerateAllScenes(jobId))}
            className="btn btn-ghost border-mcp/40 text-mcp text-xs">
            {busy === "regenall" ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}Regenerate Scenes ⚠</button>
          <button disabled={busy === "anim"} onClick={() => run("anim", "Improve Animation", true, () => api.improveAnimation(jobId))}
            className="btn btn-ghost border-mcp/40 text-mcp text-xs">
            {busy === "anim" ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}Try Different Model ⚠</button>
        </div>
        {toast && <div className="text-xs text-teal">{toast}</div>}
      </div>

      <p className="text-[11px] text-mcp border-t border-line pt-2">
        Framework principle: this pipeline only spends credits after the story, format, hook,
        script, and blueprint pass the free planning gates.
      </p>
    </div>);
}
