"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight, Play, Loader2, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { Job, Meta } from "@/lib/types";
import { StatCard, EmptyState } from "@/components/ui/Card";
import { ScoreCard } from "@/components/ui/ScoreCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CLASS_ACCENT } from "@/lib/constants";

export default function DashboardPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [research, setResearch] = useState<any>(null);
  const [imgCount, setImgCount] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.jobs().then(async (r) => {
      const latest = r.jobs[0] ?? null;
      setJob(latest);
      if (latest) {
        api.artifacts(latest.job_id)
          .then((a) => setImgCount(a.artifacts.filter((x) => x.name.endsWith(".jpg")).length))
          .catch(() => {});
        fetch(api.artifactUrl(latest.job_id, "01_research.json"))
          .then((res) => (res.ok ? res.json() : null)).then(setResearch).catch(() => {});
      }
    }).catch(() => {});
  }, []);

  async function runClosingBell() {
    setRunning(true);
    try {
      const r = await api.run();
      router.push(`/run/${r.job_id}`);
    } catch { setRunning(false); }
  }

  const scores = job?.scores;
  const storiesFound = research?._meta?.candidate_count ?? research?.top_3_stories?.length ?? null;
  const storiesSelected = research?.top_3_stories?.length ?? null;
  const activeNode = job?.current_node ? job.current_node.replace(/_/g, " ") : "—";

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      {/* hero */}
      <div className="glass card-pad relative overflow-hidden mb-6">
        <div className="absolute -top-24 -right-16 h-64 w-64 rounded-full bg-teal/10 blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="eyebrow">{meta?.run_name ?? "Closing Bell Run"} · {meta?.next_run ?? "5:00 PM IST"}</div>
            <h2 className="text-2xl font-semibold tracking-tight mt-1.5">
              Post-market intelligence, generated and reviewed by your AI newsroom.
            </h2>
            <p className="text-sm text-ink-muted mt-1.5 max-w-xl">
              Watch the real Claude Code pipeline research the Indian market after close, build a
              3-slide carousel, gate it for quality &amp; compliance, and publish — every node visible.
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <button className="btn btn-primary" onClick={runClosingBell} disabled={running}>
              {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
              Run Closing Bell
            </button>
            {job && (
              <Link href={`/run/${job.job_id}`} className="btn btn-ghost">
                Open Latest Run <ArrowUpRight size={15} />
              </Link>
            )}
          </div>
        </div>
      </div>

      {!job ? (
        <EmptyState title="No runs yet" hint="Trigger a Closing Bell run to watch the pipeline live, or wait for the 5:00 PM IST schedule." />
      ) : (
        <>
          {/* top metrics */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-4">
            <div className="glass card-pad col-span-2 md:col-span-1">
              <div className="eyebrow">Current Run</div>
              <div className="text-lg font-semibold tracking-tight mt-2">{job.job_id}</div>
              <div className="mt-2"><StatusBadge status={job.status} glow /></div>
            </div>
            <StatCard label="Active Node" value={<span className="text-lg capitalize">{activeNode}</span>} hint={job.run_type} />
            <StatCard label="Stories Found" value={storiesFound ?? "—"} accent={CLASS_ACCENT.A} />
            <StatCard label="Stories Selected" value={storiesSelected ?? "—"} hint="importance≥7 · confidence≥8" />
            <StatCard label="Images Generated" value={imgCount ?? "—"} accent={CLASS_ACCENT.C} hint="nano_banana_pro" />
            <div className="glass card-pad">
              <div className="eyebrow">IG Publish</div>
              <div className="mt-2"><StatusBadge status={job.publish_status === "published" ? "published" : (job.publish_status || "waiting")} /></div>
              {job.instagram_post_url ? (
                <a href={job.instagram_post_url} target="_blank" rel="noreferrer"
                   className="mt-2 inline-flex items-center gap-1 text-xs text-teal hover:underline">
                  View post <ExternalLink size={12} />
                </a>
              ) : <div className="text-xs text-ink-faint mt-2">No permalink yet</div>}
            </div>
          </div>

          {/* scores */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <ScoreCard label="Content Quality" score={scores?.content_score} threshold={meta?.thresholds.content ?? 90} />
            <ScoreCard label="Design Quality" score={scores?.design_score} threshold={meta?.thresholds.design ?? 90} />
            <ScoreCard label="Compliance" score={scores?.compliance_score} threshold={meta?.thresholds.compliance ?? 95} />
            <ScoreCard label="Aesthetic (visual QA)" score={scores?.aesthetic_score} sub="Reviewer score" />
          </div>

          {/* market summary */}
          {job.summary && (
            <div className="glass card-pad mt-4">
              <div className="eyebrow mb-2">Market Summary · {job.date}</div>
              <p className="text-sm text-ink-muted leading-relaxed">{job.summary}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
