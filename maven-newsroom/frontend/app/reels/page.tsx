"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight, Clapperboard, Loader2, Play, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { StatCard, EmptyState } from "@/components/ui/Card";
import { ScoreCard } from "@/components/ui/ScoreCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CapabilityBanner } from "@/components/reels/CapabilityBanner";

export default function ReelsDashboard() {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [quality, setQuality] = useState<any>(null);
  const [freshVideo, setFreshVideo] = useState<any>(null);
  const [research, setResearch] = useState<any>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const load = (id: string) => {
      api.job(id).then(setJob).catch(() => {});
      fetch(api.artifactUrl(id, "16_quality.json"))
        .then((x) => x.ok ? x.json() : null).then(setQuality).catch(() => {});
      fetch(api.artifactUrl(id, "12_higgsfield_generation.json"))
        .then((x) => x.ok ? x.json() : null).then(setFreshVideo).catch(() => {});
      fetch(api.artifactUrl(id, "01_research.json"))
        .then((x) => x.ok ? x.json() : null).then(setResearch).catch(() => {});
    };
    api.reelsLatest().then((l) => load(l.job_id)).catch(() =>
      api.jobs("reel").then((r) => {
        const latest = r.jobs.find((j) => !j.job_id.includes("-sim-")) ?? r.jobs[0] ?? null;
        if (latest) load(latest.job_id);
      }).catch(() => {}));
  }, []);

  async function runReel() {
    setRunning(true);
    // every click = a NEW unique job (fresh folder, fresh research required)
    try { const r = await api.runReel(); router.push(`/reels/run/${r.job_id}`); }
    catch { setRunning(false); }
  }

  const s = quality?.scores ?? {};
  const hasVideo = (job?.thumbnails ?? []).length > 0 || job?.publish_status === "published";

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      <CapabilityBanner />
      <div className="glass card-pad relative overflow-hidden mb-6">
        <div className="absolute -top-24 -right-16 h-64 w-64 rounded-full bg-mcp/10 blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="eyebrow flex items-center gap-1.5"><Clapperboard size={13} /> Reels · retention-first</div>
            <h2 className="text-2xl font-semibold tracking-tight mt-1.5">
              One market event → a 20–35s reel people actually watch, save and share.
            </h2>
            <p className="text-sm text-ink-muted mt-1.5 max-w-xl">
              A separate pipeline from the carousel: Viral Fit Gate → Hook Lab → Retention Editor →
              premium stills + ffmpeg motion → AI voiceover → Reel Auditor → Reels Courier.
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2.5">
              <button className="btn btn-primary" onClick={runReel} disabled={running}>
                {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} Run Reel
              </button>
              {job && <Link href={`/reels/run/${job.job_id}`} className="btn btn-ghost">Open latest <ArrowUpRight size={15} /></Link>}
            </div>
            <div className="text-[11px] text-ink-faint text-right max-w-xs space-y-0.5">
              <div><span className="text-teal">Renderer: Higgsfield Animated Clips</span>
                {freshVideo && <> · {freshVideo.generation_status} (~{freshVideo.estimated_cost_credits}cr)</>}
              </div>
              {research && (
                <div>
                  Data Mode: <span className="text-ink">{
                    research.data_window === "intraday" ? "Intraday"
                    : research.data_window === "post_market" ? "Post-market"
                    : "Latest trading day"}</span>
                  {" · "}Research: <span className={research.research_status === "completed" ? "text-ok" : "text-danger"}>{research.research_status}</span>
                  {research.sources_used?.length > 0 && <> · {research.sources_used.join(", ")}</>}
                </div>
              )}
              {research?.research_status === "failed" && (
                <div className="text-danger">Research failed: {research.error}</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {!job ? (
        <EmptyState title="No reels yet" hint="Run a Reel to watch the 22-node pipeline live." />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="glass card-pad">
              <div className="eyebrow">Latest reel</div>
              <div className="text-lg font-semibold mt-2">{job.job_id}</div>
              <div className="mt-2"><StatusBadge status={job.status} glow /></div>
            </div>
            <StatCard label="Chosen hook" value={<span className="text-sm leading-snug">{job.summary || "—"}</span>} />
            <StatCard label="Scenes" value={quality?.scores ? (job.artifact_count ?? "—") : "—"} hint="9:16 stills" />
            <div className="glass card-pad">
              <div className="eyebrow">Publish</div>
              <div className="mt-2"><StatusBadge status={job.publish_status === "published" ? "published" : (job.publish_status || "waiting")} /></div>
              {job.instagram_post_url ? (
                <a href={job.instagram_post_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-teal">View reel <ExternalLink size={12} /></a>
              ) : <div className="text-xs text-ink-faint mt-2">Not published</div>}
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <ScoreCard label="Hook" score={s.hook} threshold={85} />
            <ScoreCard label="Retention" score={s.retention} threshold={85} />
            <ScoreCard label="Visual" score={s.visual} threshold={85} sub={s.visual ? undefined : "needs the real video"} />
            <ScoreCard label="Compliance" score={s.compliance} threshold={95} />
          </div>
        </>
      )}
    </div>
  );
}
