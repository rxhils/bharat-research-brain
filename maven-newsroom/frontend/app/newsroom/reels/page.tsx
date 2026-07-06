"use client";
import { useCallback, useEffect, useState } from "react";
import { Clapperboard, HardDrive, Play, RefreshCw } from "lucide-react";
import { StatCard, EmptyState } from "@/components/ui/Card";
import { newsroomReelsApi as api } from "@/lib/newsroomReelsApi";
import type { NewsroomReelsStatus } from "@/lib/newsroomReelsTypes";

/**
 * Maven Newsroom Reels — daily review dashboard (Remotion + FFmpeg pipeline,
 * no Higgsfield). Fully isolated from the legacy /reels Higgsfield pages.
 */
export default function NewsroomReelsDashboard() {
  const [status, setStatus] = useState<NewsroomReelsStatus | null>(null);
  const [run, setRun] = useState<any>(null);
  const [reels, setReels] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [showAgents, setShowAgents] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.status().then(setStatus).catch((e) => setError(String(e)));
    api.runs().then((r) => setRun(r.runs[0] ?? null)).catch(() => {});
    api.reels().then((r) => setReels(r.reels)).catch(() => {});
    api.agents().then((r) => setAgents(r.agents)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function startRun() {
    setBusy(true);
    try { await api.createRun(); load(); } catch (e) { setError(String(e)); }
    setBusy(false);
  }

  async function decide(renderId: string, decision: "approve" | "reject" | "revise") {
    let reason: string | undefined;
    if (decision !== "approve") {
      reason = window.prompt(`Why ${decision}? (weak hook / bad crop / too risky / boring / bad subtitles ...)`) ?? undefined;
      if (reason === undefined) return;
    }
    try { await api.decision(renderId, decision, reason); load(); }
    catch (e) { setError(String(e)); }
  }

  const qaPassed = reels.filter((r) => r.qa_passed).length;
  const approved = reels.filter((r) => r.decision === "approve").length;

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      <div className="glass card-pad relative overflow-hidden mb-6">
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="eyebrow flex items-center gap-1.5"><Clapperboard size={13} /> Newsroom Reels · Remotion + FFmpeg · no Higgsfield</div>
            <h2 className="text-2xl font-semibold tracking-tight mt-1.5">
              15 approval-ready Reels/day from Indian finance podcasts.
            </h2>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex gap-2">
              <button className="btn btn-primary" onClick={startRun} disabled={busy}>
                <Play size={15} /> Start daily run
              </button>
              <button className="btn btn-ghost" onClick={load}><RefreshCw size={15} /></button>
            </div>
            <div className="text-[11px] text-ink-faint flex items-center gap-1.5">
              <HardDrive size={12} /> {status?.storage_root ?? "E:\\MavenReels"} ·{" "}
              {status ? (status.storage_ok ? `${status.free_gb} GB free` : "STORAGE BLOCKED") : "…"}
            </div>
          </div>
        </div>
      </div>

      {error && <div className="glass card-pad mb-4 text-sm text-danger">{error}</div>}

      <div className="glass card-pad mb-6">
        <button className="w-full flex items-center justify-between text-sm font-semibold"
                onClick={() => setShowAgents(!showAgents)}>
          <span>Framework Agents ({agents.length})</span>
          <span className="text-ink-faint text-xs">{showAgents ? "hide" : "show"}</span>
        </button>
        {showAgents && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-4">
            {agents.map((a) => (
              <div key={a.key} className="border border-white/5 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold">{a.name}</div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    a.errors_24h > 0 ? "bg-danger/20 text-danger"
                    : a.last_activity_at ? "bg-ok/20 text-ok" : "bg-white/5 text-ink-faint"}`}>
                    {a.errors_24h > 0 ? `${a.errors_24h} errors` : a.last_activity_at ? "active" : "idle"}
                  </span>
                </div>
                <div className="text-[11px] text-ink-muted mt-1">{a.role}</div>
                {a.last_message && (
                  <div className="text-[10px] text-ink-faint mt-1.5 line-clamp-2">
                    {a.last_activity_at?.slice(0, 16).replace("T", " ")} · {a.last_message}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <StatCard label="Target" value={`${run?.progress?.reels_ready ?? 0} / ${run?.target_reels ?? 15}`} hint="reels ready" />
        <StatCard label="Podcasts" value={`${run?.progress?.podcasts_selected ?? 0} / ${run?.target_podcasts ?? 3}`} />
        <StatCard label="Rendered" value={reels.length} />
        <StatCard label="QA passed" value={qaPassed} />
        <StatCard label="Approved" value={approved} />
      </div>

      {reels.length === 0 ? (
        <EmptyState title="No reels yet" hint="Start a daily run — reels appear here as they pass QA, latest first." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {reels.map((r) => (
            <div key={r.render_id} className="glass card-pad flex flex-col gap-2">
              <video src={api.videoUrl(r.render_id)} controls preload="metadata"
                     className="w-full rounded-lg aspect-[9/16] bg-black object-contain max-h-96" />
              <div className="text-sm font-semibold leading-snug">{r.hook_text ?? "—"}</div>
              <div className="text-[11px] text-ink-faint">{r.source_name} · {r.episode_title}</div>
              <div className="text-[11px] text-ink-muted line-clamp-2">{r.transcript_excerpt}</div>
              <div className="flex flex-wrap gap-2 text-[11px]">
                <span>rel {r.indian_relevance_score ?? "—"}</span>
                <span>viral {r.virality_score ?? "—"}</span>
                <span>risk {r.compliance_risk_score ?? "—"}</span>
                <span>watch {r.final_render_watch_score ?? "—"}</span>
                <span className={r.qa_passed ? "text-ok" : "text-danger"}>
                  QA {r.qa_passed ? "PASS" : "FAIL"}
                </span>
              </div>
              {r.decision ? (
                <div className="text-xs">Decision: <b>{r.decision}</b>{r.decision_reason ? ` — ${r.decision_reason}` : ""}</div>
              ) : (
                <div className="flex gap-2 mt-1">
                  <button className="btn btn-primary text-xs" disabled={!r.qa_passed}
                          onClick={() => decide(r.render_id, "approve")}>Approve</button>
                  <button className="btn btn-ghost text-xs" onClick={() => decide(r.render_id, "reject")}>Reject</button>
                  <button className="btn btn-ghost text-xs" onClick={() => decide(r.render_id, "revise")}>Revise</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
