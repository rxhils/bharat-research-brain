"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Send, X, RefreshCw, Mic, Zap, Scissors, Gauge, Image as ImageIcon,
  Film, ImagePlus, ShieldCheck, MessageSquare, CheckCircle2,
  LayoutTemplate, Palette, Sparkles, Wand2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { Card, EmptyState } from "@/components/ui/Card";
import { ScoreCard } from "@/components/ui/ScoreCard";

/* ---- small presentational helpers ------------------------------------- */
function Section({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <div className="eyebrow">{title}</div>
        {right}
      </div>
      {children}
    </Card>
  );
}
function Bar({ v, max = 10, color = "#2DD4BF" }: { v: number; max?: number; color?: string }) {
  return (
    <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden w-full">
      <div className="h-full rounded-full" style={{ width: `${Math.min(100, (v / max) * 100)}%`, background: color }} />
    </div>
  );
}
function Pill({ children, tone = "muted" }: { children: React.ReactNode; tone?: "ok" | "warn" | "muted" | "teal" }) {
  const cls = tone === "ok" ? "border-ok/40 text-ok bg-ok/10"
    : tone === "warn" ? "border-warn/40 text-warn bg-warn/10"
    : tone === "teal" ? "border-teal/40 text-teal bg-teal/10"
    : "border-line text-ink-faint";
  return <span className={`chip ${cls}`}>{children}</span>;
}

/* fetch a JSON artifact by filename */
function useArtifact<T = any>(jobId: string, name: string) {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let live = true;
    fetch(api.artifactUrl(jobId, name)).then((x) => (x.ok ? x.json() : null))
      .then((d) => live && setData(d)).catch(() => {});
    return () => { live = false; };
  }, [jobId, name]);
  return data;
}

/* status label from job + audit */
function statusLabel(job: Job | null, passed: boolean, hasScores: boolean): { text: string; tone: "ok" | "warn" | "muted" | "teal" } {
  if (job?.publish_status === "published") return { text: "Published", tone: "ok" };
  if (job?.approval_status === "approved") return { text: "Approved", tone: "teal" };
  if (job?.approval_status === "rejected") return { text: "Rejected", tone: "warn" };
  if (passed) return { text: "Ready for Approval", tone: "teal" };
  if (hasScores) return { text: "Needs Improvement", tone: "warn" };
  return { text: "Draft", tone: "muted" };
}

/** rejection feedback types (mirror backend FEEDBACK_TYPES) */
const FEEDBACK_BUTTONS: { type: string; label: string }[] = [
  { type: "weak_hook", label: "Weak Hook" },
  { type: "boring_script", label: "Boring Script" },
  { type: "bad_animation", label: "Bad Animation" },
  { type: "visuals_too_basic", label: "Visuals Too Basic" },
  { type: "too_slow", label: "Too Slow" },
  { type: "bad_voiceover", label: "Bad Voiceover" },
  { type: "bad_subtitles", label: "Bad Subtitles" },
  { type: "not_premium_enough", label: "Not Premium Enough" },
  { type: "wrong_story", label: "Wrong Story" },
  { type: "bad_data", label: "Bad Data / Needs Research" },
  { type: "try_different_style", label: "Try Different Style" },
  { type: "other", label: "Other Feedback" },
];

export default function ReelReviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [arts, setArts] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [customFb, setCustomFb] = useState("");
  const [parentQuality, setParentQuality] = useState<any>(null);

  const quality = useArtifact(jobId, "16_quality.json");
  const caption = useArtifact(jobId, "14_caption.json");
  const hooks = useArtifact(jobId, "04_hooks.json");
  const viral = useArtifact(jobId, "02_viral_fit.json");
  const angle = useArtifact(jobId, "03_angle.json");
  const script = useArtifact(jobId, "06_script_edited.json");
  const storyboard = useArtifact(jobId, "07_storyboard.json");
  const assets = useArtifact(jobId, "08_assets.json");
  const template = useArtifact(jobId, "07_template.json");
  const variation = useArtifact(jobId, "08_motion_variation.json");
  const picker = useArtifact(jobId, "09_asset_picker.json");
  const direction = useArtifact(jobId, "09_higgsfield_creative_direction.json");
  const shotPlan = useArtifact(jobId, "10_higgsfield_shot_plan.json");
  const sceneQuality = useArtifact(jobId, "13_scene_quality.json");
  const [clips, setClips] = useState<any>(null);
  useEffect(() => {
    api.reelClips(jobId).then(setClips).catch(() => setClips(null));
  }, [jobId]);

  const refresh = useCallback(() => { api.job(jobId).then(setJob).catch(() => {}); }, [jobId]);
  useEffect(() => {
    refresh();
    api.artifacts(jobId).then((a) => setArts(a.artifacts.map((x) => x.name))).catch(() => {});
  }, [jobId, refresh]);

  // version comparison: fetch the parent version's auditor scores
  const parentId = (job as any)?.parent_job_id as string | undefined;
  useEffect(() => {
    if (!parentId) { setParentQuality(null); return; }
    fetch(api.artifactUrl(parentId, "16_quality.json"))
      .then((x) => (x.ok ? x.json() : null)).then(setParentQuality).catch(() => {});
  }, [parentId]);

  /** rejection/improvement: feedback → Improvement Director → new version */
  const improve = useCallback(async (type: string) => {
    setBusy(`fb:${type}`); setToast("Creating improved version…");
    try {
      const r = await api.reelImprove(jobId, type, customFb || undefined);
      if (r.status === "improving" && r.new_job_id) {
        setToast(`v${r.version} rendering — opening it now…`);
        router.push(`/reels/review/${r.new_job_id}`);
      } else if (r.status === "needs_conductor" && r.new_job_id) {
        setToast(`v${r.version} created — ${r.message ?? "needs the Claude Code conductor"}`);
        router.push(`/reels/review/${r.new_job_id}`);
      } else {
        setToast(r.message ?? r.status);
      }
    } catch { setToast("Improvement failed"); }
    setBusy(null);
    setTimeout(() => setToast(null), 6000);
  }, [jobId, customFb, router]);

  const act = useCallback(async (key: string, label: string, fn: () => Promise<any>) => {
    setBusy(key); setToast(`${label}…`);
    try {
      const r = await fn();
      setToast(r?.status === "requires_conductor"
        ? `${label}: needs Claude Code conductor (queued, nothing faked)`
        : `${label}: ${r?.message ?? r?.status ?? "done"}`);
      refresh();
      api.artifacts(jobId).then((a) => setArts(a.artifacts.map((x) => x.name))).catch(() => {});
    } catch (e: any) {
      setToast(e?.data?.problems ? `Blocked: ${e.data.problems.join(", ")}` : `${label} failed`);
    }
    setBusy(null);
    setTimeout(() => setToast(null), 5000);
  }, [refresh, jobId]);

  const s = quality?.scores ?? {};
  const gates = quality?.gates ?? { hook: 90, retention: 90, edit_quality: 90, visual_quality: 90, subtitle: 90, voiceover: 85, compliance: 95, brand: 90 };
  const passed = !!quality?.passed;
  const hasScores = !!quality?.scores;
  const verdict = quality?.verdict ?? "";
  const hasReel = arts.includes("reel.mp4");
  const hasCover = arts.includes("cover.jpg");
  const plates = ["asset_bg_dark.jpg", "asset_bg_panel.jpg", "asset_bg_end.jpg"].filter((p) => arts.includes(p));
  const label = statusLabel(job, passed, hasScores);

  const Btn = ({ k, label: l, icon, onClick, tone = "ghost", disabled }: {
    k: string; label: string; icon: React.ReactNode; onClick: () => void; tone?: "ghost" | "primary" | "danger"; disabled?: boolean;
  }) => (
    <button disabled={disabled || busy === k} onClick={onClick}
      className={`btn ${tone === "primary" ? "btn-primary" : tone === "danger" ? "btn-ghost border-danger/40 text-danger" : "btn-ghost border-line"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}>
      {busy === k ? <RefreshCw size={15} className="animate-spin" /> : icon}{l}
    </button>
  );

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-5">
      {/* header + status */}
      <div className="flex items-center justify-between">
        <div>
          <div className="eyebrow">Reel Review · Reel Auditor → Approval → Publish Gate</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">{job?.summary || "Approve the reel"} · {jobId}</h2>
        </div>
        <div className="flex items-center gap-2">
          {((job as any)?.version ?? 1) > 1 && <Pill tone="teal">v{(job as any).version}</Pill>}
          {(job as any)?.is_latest ? <Pill tone="ok">Latest</Pill> : null}
          <Pill tone={label.tone}>{label.text}</Pill>
          {verdict && <Pill tone={passed ? "ok" : "warn"}>{verdict}</Pill>}
        </div>
      </div>

      <div className="grid lg:grid-cols-[380px_1fr] gap-5">
        {/* left: preview + cover + plates */}
        <div className="space-y-3">
          {hasReel ? (
            <video controls className="w-full rounded-xl border border-line bg-black" style={{ aspectRatio: "9/16" }}
              src={api.artifactUrl(jobId, "reel.mp4")} poster={hasCover ? api.artifactUrl(jobId, "cover.jpg") : undefined} />
          ) : clips && clips.generation_status !== "not_planned" ? (
            <div className="w-full rounded-xl border border-teal/30 bg-teal/[0.04] flex flex-col items-center justify-center gap-4 p-6 text-center" style={{ aspectRatio: "9/16" }}>
              <Sparkles size={28} className="text-teal" />
              <div className="text-sm text-ink">
                {clips.generation_status === "requires_user_action"
                  ? "Nothing is generating yet — the animated scenes wait for your approval."
                  : clips.generation_status === "approved_awaiting_conductor"
                  ? "Approved ✓ — the Claude Code conductor generates the scenes next."
                  : `Scene generation: ${clips.generation_status}`}
              </div>
              {clips.generation_status === "requires_user_action" && (
                <button className="btn btn-primary"
                  onClick={() => {
                    if (window.confirm(`This will use Higgsfield credits to generate animated video scenes (~${clips.estimated_cost_credits}cr). Continue?`))
                      act("gen-top", "Generate Scenes", () => api.approveGeneration(jobId));
                  }}>
                  <Sparkles size={15} /> Generate Animated Scenes (~{clips.estimated_cost_credits}cr) ⚠
                </button>
              )}
              <p className="text-[11px] text-ink-faint">
                The cover frame is extracted from the Higgsfield hook scene after
                generation — unique to this reel&apos;s creative direction.
              </p>
            </div>
          ) : hasCover ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={api.artifactUrl(jobId, "cover.jpg")} alt="cover" className="w-full rounded-xl border border-line" style={{ aspectRatio: "9/16", objectFit: "cover" }} />
          ) : (
            <EmptyState title="No reel yet" hint="Approve scene generation to build this reel." />
          )}
          {/* legacy static plates only shown for old Remotion-era runs */}
          {!clips && (hasCover || plates.length > 0) && (
            <>
              <div className="grid grid-cols-4 gap-2">
                {hasCover && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={api.artifactUrl(jobId, "cover.jpg")} alt="cover" title="Cover" className="rounded-lg border border-line" style={{ aspectRatio: "9/16", objectFit: "cover" }} />
                )}
                {plates.map((p) => (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img key={p} src={api.artifactUrl(jobId, p)} alt={p} title={p.replace(".jpg", "")} className="rounded-lg border border-line opacity-80" style={{ aspectRatio: "9/16", objectFit: "cover" }} />
                ))}
              </div>
              <p className="text-[11px] text-mcp">Legacy run: cover + {plates.length} static plates (Remotion renderer).</p>
            </>
          )}
          {hasReel && hasCover && clips && (
            <div className="flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={api.artifactUrl(jobId, "cover.jpg")} alt="cover" title="Cover (from Higgsfield hook scene)" className="rounded-lg border border-line w-20" style={{ aspectRatio: "9/16", objectFit: "cover" }} />
              <p className="text-[11px] text-ink-faint">Cover — extracted from this reel&apos;s Higgsfield hook scene (theme-specific, unique per reel).</p>
            </div>
          )}
        </div>

        {/* right: 9 scores + actions */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <ScoreCard label="Hook" score={s.hook} threshold={gates.hook} />
            <ScoreCard label="Retention" score={s.retention} threshold={gates.retention} />
            <ScoreCard label="Edit" score={s.edit_quality} threshold={gates.edit_quality} />
            <ScoreCard label="Visual" score={s.visual_quality} threshold={gates.visual_quality} sub={s.visual_quality ? undefined : "needs the real video"} />
            <ScoreCard label="Subtitle" score={s.subtitle} threshold={gates.subtitle} />
            <ScoreCard label="Voiceover" score={s.voiceover} threshold={gates.voiceover} />
            <ScoreCard label="Compliance" score={s.compliance} threshold={gates.compliance} />
            <ScoreCard label="Brand" score={s.brand} threshold={gates.brand} />
            <ScoreCard label="Cost Eff." score={s.cost_efficiency} threshold={gates.cost_efficiency ?? 85} sub={s.cost_efficiency ? "library reuse" : undefined} />
            <ScoreCard label="Uniqueness" score={s.visual_uniqueness} threshold={gates.visual_uniqueness ?? 85} sub="vs last 5 reels" />
            <ScoreCard label="Freshness" score={s.freshness} threshold={gates.freshness ?? 95} sub="data currency + sources" />
          </div>

          {!passed && hasScores && (
            <Card className="border-warn/30">
              <div className="eyebrow mb-2 text-warn">Not ready to publish — exact reasons</div>
              <ul className="text-sm text-ink-muted space-y-1.5">
                {(quality?.suggested_buttons ?? []).map((sb: any, i: number) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <span>• {sb.gate} scored {sb.score} (needs ≥ {sb.min})</span>
                    <span className="chip border-teal/40 text-teal bg-teal/10 shrink-0">→ {sb.click}</span>
                  </li>
                ))}
                {(quality?.suggested_buttons ?? []).length === 0 &&
                  (quality?.fixes_required ?? []).map((f: string, i: number) => <li key={i}>• {f}</li>)}
              </ul>
            </Card>
          )}

          {/* version comparison: old score vs new score */}
          {parentQuality?.scores && quality?.scores && (
            <Card>
              <div className="eyebrow mb-2">v{(job as any)?.version ?? 2} vs previous — what changed</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                {Object.keys(quality.scores).filter((k) => k !== "publish").map((k) => {
                  const oldS = parentQuality.scores[k], newS = quality.scores[k];
                  if (oldS == null || newS == null) return null;
                  const up = newS > oldS, down = newS < oldS;
                  return (
                    <div key={k} className="rounded-lg border border-line px-2.5 py-1.5">
                      <div className="text-[10px] uppercase tracking-wide text-ink-faint">{k.replace(/_/g, " ")}</div>
                      <div className={up ? "text-ok" : down ? "text-danger" : "text-ink-muted"}>
                        {oldS} → {newS}{up ? " ↑" : down ? " ↓" : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* action bench */}
          <Card>
            <div className="eyebrow mb-3">Creative revisions</div>
            <div className="grid grid-cols-2 gap-2">
              <Btn k="hook" label="Rewrite Hook" icon={<Zap size={15} />} onClick={() => act("hook", "Rewrite Hook", () => api.rerun(jobId, "hook_lab"))} />
              <Btn k="script" label="Shorten Script" icon={<Scissors size={15} />} onClick={() => act("script", "Shorten Script", () => api.rerun(jobId, "script_room"))} />
              <Btn k="pacing" label="Improve Pacing" icon={<Gauge size={15} />} onClick={() => act("pacing", "Improve Pacing", () => api.rerun(jobId, "retention_editor"))} />
              <Btn k="assets" label="Regenerate Assets" icon={<ImageIcon size={15} />} onClick={() => act("assets", "Regenerate Assets", () => api.rerun(jobId, "scene_studio"))} />
              <Btn k="video" label="Re-render Video" icon={<Film size={15} />} onClick={() => act("video", "Re-render Video", () => api.rerun(jobId, "motion_graphics"))} />
              <Btn k="voice" label="Regenerate Voiceover" icon={<Mic size={15} />} onClick={() => act("voice", "Regenerate Voiceover", () => api.rerun(jobId, "voice_studio"))} />
              <Btn k="cover" label="Regenerate Cover" icon={<ImagePlus size={15} />} onClick={() => act("cover", "Regenerate Cover", () => api.rerun(jobId, "cover_studio"))} />
              <Btn k="audit" label="Re-run Auditor" icon={<ShieldCheck size={15} />} onClick={() => act("audit", "Re-run Auditor", () => api.recheckQuality(jobId))} />
              <Btn k="tmpl" label="Change Template" icon={<LayoutTemplate size={15} />} onClick={() => act("tmpl", "Change Template", () => api.rerun(jobId, "template_selector"))} />
              <Btn k="motion" label="Change Motion Style" icon={<Palette size={15} />} onClick={() => act("motion", "Change Motion Style", () => api.rerun(jobId, "motion_variation"))} />
              <Btn k="pick" label="Pick Different Assets" icon={<ImageIcon size={15} />} onClick={() => act("pick", "Pick Assets", () => api.rerun(jobId, "asset_picker"))} />
              <Btn k="higgs" label="Request New Higgsfield ⚠" icon={<Sparkles size={15} />} onClick={() => {
                if (window.confirm("This requests PAID Higgsfield generation. Approve 1 new asset generation? Nothing is charged until the conductor runs it."))
                  act("higgs", "Higgsfield request", () => api.requestHiggsfield(jobId, true));
                else act("higgs", "Higgsfield request", () => api.requestHiggsfield(jobId, false));
              }} />
              <Btn k="regenall" label="Regenerate All Scenes ⚠" icon={<Film size={15} />} onClick={() => {
                if (window.confirm(`This will use Higgsfield credits to regenerate ALL animated scenes (~${clips?.estimated_cost_credits ?? "?"}cr). Continue?`))
                  act("regenall", "Regenerate All Scenes", () => api.regenerateAllScenes(jobId));
              }} />
              <Btn k="anim" label="Improve Animation Quality ⚠" icon={<Wand2 size={15} />} onClick={() => {
                if (window.confirm("This rebuilds all prompts at HIGH motion intensity, then regenerating the scenes will use Higgsfield credits. Continue?"))
                  act("anim", "Improve Animation Quality", () => api.improveAnimation(jobId));
              }} />
              <Btn k="reasm" label="Reassemble Reel" icon={<RefreshCw size={15} />} onClick={() => act("reasm", "Reassemble Reel", () => api.reassembleReel(jobId))} />
            </div>

            <div className="eyebrow mb-3 mt-5">Approval &amp; publish (Telegram-mirror)</div>
            <div className="grid gap-2">
              <Btn k="tg" label="Send Preview to Telegram" icon={<MessageSquare size={15} />} onClick={() => act("tg", "Telegram preview", () => api.telegramPreview(jobId))} />
              <Btn k="approve" label="Approve" icon={<CheckCircle2 size={15} />} onClick={() => act("approve", "Approve", () => api.approve(jobId))} disabled={!passed || job?.approval_status === "approved"} />
              <Btn k="publish" label="Approve & Publish Reel" tone="primary" icon={<Send size={15} />} onClick={() => act("publish", "Publish", () => api.approveAndPublish(jobId))} disabled={!passed} />
              <Btn k="reject" label="Reject" tone="danger" icon={<X size={15} />} onClick={() => act("reject", "Reject", () => api.reject(jobId))} />
            </div>
            {toast && <div className="mt-3 text-xs text-teal">{toast}</div>}
            <p className="text-[11px] text-mcp mt-2">Real publishing runs in the Claude Code conductor (Composio Reels, <code>media_type=REELS</code>). Never faked — the backend only preflights and queues.</p>
          </Card>

          {/* improvement studio: reject-with-feedback → new version */}
          <Card>
            <div className="flex items-center justify-between mb-1">
              <div className="eyebrow">Improvement Studio — reject with feedback, get a better version</div>
            </div>
            <p className="text-[11px] text-ink-faint mb-3">
              Each button files feedback, runs the Reel Improvement Director, and builds
              a new <b>version</b> (v{(((job as any)?.version ?? 1) + 1)}) that replaces this one as latest.
            </p>
            <button disabled={busy === "fb:improve_animations_quality"}
              onClick={() => improve("improve_animations_quality")}
              className="btn btn-primary w-full mb-2">
              {busy === "fb:improve_animations_quality" ? <RefreshCw size={15} className="animate-spin" /> : <Wand2 size={15} />}
              Improve Animations &amp; Quality
            </button>
            <div className="grid grid-cols-2 gap-2">
              {FEEDBACK_BUTTONS.map((f) => (
                <button key={f.type} disabled={busy === `fb:${f.type}`}
                  onClick={() => improve(f.type)}
                  className="btn btn-ghost border-line text-xs">
                  {busy === `fb:${f.type}` ? <RefreshCw size={13} className="animate-spin" /> : null}
                  {f.label}
                </button>
              ))}
            </div>
            <textarea value={customFb} onChange={(e) => setCustomFb(e.target.value)}
              placeholder="Optional: describe exactly what to improve (sent with any button above)…"
              className="mt-3 w-full rounded-lg bg-white/[0.03] border border-line p-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-teal/50"
              rows={2} />
            <p className="text-[11px] text-mcp mt-2">
              Story/data changes and new voiceover need the Claude Code conductor — versions
              that need it are created and clearly marked, never faked.
            </p>
          </Card>
        </div>
      </div>

      {/* production & cost strategy */}
      <Section title="Production & Cost Strategy"
        right={picker ? <Pill tone={picker.paid_generation_required ? "warn" : "ok"}>{picker.paid_generation_required ? "paid generation needed" : "0 new generations · library reuse"}</Pill> : undefined}>
        <div className="grid sm:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="eyebrow mb-1">Template</div>
            <div className="text-ink">{template?.selected_template ?? "—"}</div>
            {template?.template_reason && <div className="text-[11px] text-ink-faint mt-1">{template.template_reason}</div>}
          </div>
          <div>
            <div className="eyebrow mb-1">Motion Variation</div>
            <div className="flex items-center gap-2 text-ink">
              {variation?.accent_color && <span className="inline-block w-4 h-4 rounded" style={{ background: variation.accent_color }} />}
              {variation?.variation_id ?? "—"}
            </div>
            {variation?.hook_animation && <div className="text-[11px] text-ink-faint mt-1">{variation.hook_animation} · {variation.transition_style}</div>}
          </div>
          <div>
            <div className="eyebrow mb-1">Assets Used</div>
            {picker?.selected_assets?.length ? (
              <ul className="text-ink-muted text-xs space-y-0.5">
                {picker.selected_assets.map((a: any) => <li key={a.slot}>• {a.asset_id} <span className="text-ink-faint">({a.category})</span></li>)}
              </ul>
            ) : <div className="text-ink-faint">—</div>}
          </div>
          <div>
            <div className="eyebrow mb-1">Paid Higgsfield</div>
            <Pill tone={picker?.paid_generation_required ? "warn" : "ok"}>{picker?.paid_generation_required ? "required (gated)" : "none"}</Pill>
            <div className="text-[11px] text-ink-faint mt-1">Est. cost: {picker?.estimated_cost ?? "0 (library reuse)"}</div>
            {picker?.requires_approval && <div className="text-[11px] text-warn mt-1">⚠ needs approval before any generation</div>}
          </div>
        </div>
      </Section>

      {/* Higgsfield Scenes — the reel's actual video (primary renderer) */}
      {clips && clips.generation_status !== "not_planned" && (
        <Section title="Higgsfield Animated Scenes — primary renderer"
          right={<Pill tone={
            clips.generation_status === "completed" ? "ok" :
            clips.generation_status === "partial" ? "warn" :
            clips.approved_from_ui ? "teal" : "muted"
          }>{clips.generation_status}</Pill>}>
          <div className="flex flex-wrap items-center gap-4 text-xs text-ink-faint mb-3">
            {direction?.selected_direction?.name && <span>Direction: <span className="text-ink">{direction.selected_direction.name}</span></span>}
            {shotPlan?.shot_count && <span>{shotPlan.shot_count} shots · {shotPlan.total_duration}s</span>}
            <span>Est: {clips.estimated_cost_credits}cr</span>
            {clips.actual_cost_credits != null && <span>Actual: {clips.actual_cost_credits}cr</span>}
            {sceneQuality && <span>Scene quality: <span className={sceneQuality.passed ? "text-ok" : "text-warn"}>{sceneQuality.overall_scene_quality_score}/100</span></span>}
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {(clips.planned ?? []).map((p: any) => {
              const onDisk = (clips.clips_on_disk ?? []).includes(p.shot_id);
              const sq = (sceneQuality?.scene_quality ?? []).find((r: any) => r.shot_id === p.shot_id);
              return (
                <div key={p.shot_id} className={`rounded-lg border p-1.5 text-center text-[11px] ${onDisk ? (sq?.passed === false ? "border-warn/40 bg-warn/10" : "border-teal/40 bg-teal/10") : "border-line"}`}>
                  {onDisk ? (
                    <video muted loop playsInline className="w-full rounded mb-1" style={{ aspectRatio: "9/16", objectFit: "cover" }}
                      src={api.artifactUrl(jobId, `${p.shot_id}.mp4`)}
                      onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                      onMouseLeave={(e) => (e.target as HTMLVideoElement).pause()} />
                  ) : (
                    <div className="w-full rounded mb-1 bg-white/[0.03] flex items-center justify-center text-ink-faint" style={{ aspectRatio: "9/16" }}>awaiting</div>
                  )}
                  <div className="font-mono text-ink-faint">{p.shot_id}</div>
                  {p.model && <div className="text-[10px] text-ink-faint truncate" title={`${p.scene_complexity ?? ""} → ${p.model}`}>{p.model}{p.estimated_cost != null ? ` · ${p.estimated_cost}cr` : ""}</div>}
                  {sq && <div className={sq.passed ? "text-ok" : "text-warn"}>{sq.score}/100</div>}
                  {onDisk && sq?.passed === false && (
                    <button className="mt-1 text-[10px] text-warn underline"
                      onClick={() => {
                        if (window.confirm(`This will use Higgsfield credits to regenerate ${p.shot_id}. Continue?`))
                          act(`regen-${p.shot_id}`, `Regenerate ${p.shot_id}`, () => api.regenerateScene(jobId, p.shot_id));
                      }}>regenerate</button>
                  )}
                </div>
              );
            })}
          </div>
          {!clips.approved_from_ui && clips.generation_status === "requires_user_action" && (
            <button className="btn btn-primary w-full mt-3"
              onClick={() => {
                if (window.confirm(`This will use Higgsfield credits to generate animated video scenes (~${clips.estimated_cost_credits}cr). Continue?`))
                  act("gen", "Generate Scenes", () => api.approveGeneration(jobId));
              }}>
              <Sparkles size={15} /> Generate Animated Scenes (~{clips.estimated_cost_credits}cr) ⚠
            </button>
          )}
          <p className="text-[11px] text-mcp mt-2">
            Higgsfield animated clips generated per scene using lowest-cost suitable
            model — no static plates, no slideshows. The local assembler adds voiceover,
            music, subtitles and branding. Generation executes via the Claude Code
            conductor after your approval — never automatically.
          </p>
        </Section>
      )}

      {/* full artifact surface */}
      <div className="grid lg:grid-cols-2 gap-5">
        {/* Viral Fit */}
        <Section title="Viral Fit Gate" right={viral?.chosen?.viral_fit != null ? <Pill tone="teal">fit {viral.chosen.viral_fit}</Pill> : undefined}>
          {viral ? (
            <div className="space-y-3">
              <div className="text-sm text-ink">{viral?.chosen?.story?.headline ?? viral?.selected_story?.headline ?? "—"}</div>
              {viral?.why_this_story_can_work_as_a_reel && <p className="text-xs text-ink-faint">{viral.why_this_story_can_work_as_a_reel}</p>}
              {Array.isArray(viral?.chosen?.dimensions ?? viral?.chosen?.scores) && (
                <div className="grid gap-1.5">
                  {Object.entries((viral?.chosen?.dimensions ?? viral?.chosen?.scores) as Record<string, number>).map(([k, v]) => (
                    <div key={k} className="grid grid-cols-[110px_1fr_28px] items-center gap-2 text-xs">
                      <span className="text-ink-faint capitalize">{k.replace(/_/g, " ")}</span><Bar v={Number(v)} /><span className="text-ink-muted text-right">{v}</span>
                    </div>
                  ))}
                </div>
              )}
              {Array.isArray(viral?.rejected_stories) && viral.rejected_stories.length > 0 && (
                <details className="text-xs text-ink-faint"><summary className="cursor-pointer">Rejected stories ({viral.rejected_stories.length})</summary>
                  <ul className="mt-2 space-y-1">{viral.rejected_stories.slice(0, 5).map((r: any, i: number) => <li key={i}>• {r.headline ?? r.story?.headline ?? "—"} {r.reason ? `— ${r.reason}` : ""}</li>)}</ul>
                </details>
              )}
            </div>
          ) : <EmptyState title="No viral-fit artifact" />}
        </Section>

        {/* Hooks */}
        <Section title="Hook Lab" right={hooks?.hook_score != null ? <Pill tone="teal">score {hooks.hook_score}</Pill> : undefined}>
          {hooks ? (
            <div className="space-y-2">
              <div className="rounded-lg border border-teal/30 bg-teal/[0.06] p-2.5">
                <div className="text-[11px] text-teal mb-1">Chosen · on-screen</div>
                <div className="text-sm text-ink">{hooks?.on_screen_hook ?? hooks?.chosen?.text ?? "—"}</div>
              </div>
              {Array.isArray(hooks?.hooks) && (
                <details className="text-xs text-ink-faint"><summary className="cursor-pointer">All {hooks.hooks.length} hooks across categories</summary>
                  <ul className="mt-2 space-y-1.5">{hooks.hooks.slice(0, 15).map((h: any, i: number) => (
                    <li key={i} className="flex items-start gap-2"><span className="chip border-line shrink-0">{h.category ?? "—"}</span><span className="text-ink-muted">{h.text}{h.strength != null ? ` (${h.strength})` : ""}</span></li>
                  ))}</ul>
                </details>
              )}
            </div>
          ) : <EmptyState title="No hooks artifact" />}
        </Section>

        {/* Angle */}
        <Section title="Angle Studio" right={angle?.angle_score != null ? <Pill tone="teal">score {angle.angle_score}</Pill> : undefined}>
          {angle ? (
            <div className="space-y-2">
              <div className="text-sm text-ink">{angle?.selected_angle ?? angle?.chosen?.angle ?? angle?.chosen?.text ?? "—"}</div>
              {angle?.angle_type && <Pill>{angle.angle_type}</Pill>}
              {Array.isArray(angle?.candidates) && (
                <details className="text-xs text-ink-faint"><summary className="cursor-pointer">{angle.candidates.length} candidate angles</summary>
                  <ul className="mt-2 space-y-1">{angle.candidates.slice(0, 12).map((c: any, i: number) => <li key={i}>• <span className="text-ink-muted">{c.angle ?? c.text}</span> {c.type ? `— ${c.type}` : ""}</li>)}</ul>
                </details>
              )}
            </div>
          ) : <EmptyState title="No angle artifact" />}
        </Section>

        {/* Script timeline */}
        <Section title="Script Room" right={script?.total_seconds != null ? <Pill tone={script.total_seconds >= 15 && script.total_seconds <= 20 ? "ok" : "warn"}>{script.total_seconds}s</Pill> : undefined}>
          {script?.segments ? (
            <div className="space-y-2">
              {script.segments.map((seg: any, i: number) => (
                <div key={i} className="grid grid-cols-[64px_1fr] gap-2 text-xs">
                  <span className="text-teal font-mono">{seg.label ?? `seg ${i + 1}`}<br /><span className="text-ink-faint">{seg.seconds}s</span></span>
                  <span className="text-ink-muted">{seg.narration}</span>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No script artifact" />}
        </Section>

        {/* Storyboard */}
        <Section title="Motion Storyboard" right={storyboard?.scene_count != null ? <Pill>{storyboard.scene_count} scenes · {storyboard.total_duration}s</Pill> : undefined}>
          {storyboard?.scenes ? (
            <div className="grid gap-1.5">
              {storyboard.scenes.map((sc: any, i: number) => (
                <div key={i} className="grid grid-cols-[90px_46px_1fr] items-center gap-2 text-xs">
                  <span className="chip border-line justify-center">{sc.kind}</span>
                  <span className="text-ink-faint font-mono">{sc.duration}s</span>
                  <span className="text-ink-muted truncate">{sc.on_screen || sc.visual || "—"}</span>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No storyboard artifact" />}
        </Section>

        {/* Assets + caption */}
        <Section title="Assets & Caption">
          <div className="space-y-3">
            {assets?.assets && (
              <div className="text-xs text-ink-muted">
                <div className="eyebrow mb-1">Asset Director</div>
                <ul className="space-y-1">{(Array.isArray(assets.assets) ? assets.assets : Object.values(assets.assets)).slice(0, 6).map((a: any, i: number) => (
                  <li key={i}>• {typeof a === "string" ? a : (a.id ?? a.name ?? a.role ?? JSON.stringify(a).slice(0, 60))}</li>
                ))}</ul>
              </div>
            )}
            {caption?.caption && (
              <div>
                <div className="eyebrow mb-1">Caption</div>
                <p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed max-h-40 overflow-auto">{caption.caption}</p>
              </div>
            )}
            {!assets && !caption?.caption && <EmptyState title="No assets / caption yet" />}
          </div>
        </Section>
      </div>
    </div>
  );
}
