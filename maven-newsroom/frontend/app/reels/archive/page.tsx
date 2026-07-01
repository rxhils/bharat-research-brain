"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { EmptyState } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

export default function ReelArchivePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { api.jobs("reel").then((r) => setJobs(r.jobs)).catch(() => {}).finally(() => setLoaded(true)); }, []);

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto">
      <div className="mb-4"><div className="eyebrow">Reel Archive</div><h2 className="text-xl font-semibold tracking-tight mt-1">Past reels</h2></div>
      {loaded && jobs.length === 0 ? <EmptyState title="No reels yet" hint="Run a Reel from the Reels dashboard." /> : (
        <div className="glass overflow-hidden">
          <div className="grid grid-cols-[70px_1fr_120px_140px_140px_90px] gap-3 px-4 py-2.5 border-b border-line text-[11px] uppercase tracking-wider text-ink-faint">
            <span></span><span>Reel</span><span>Status</span><span>Scores</span><span>Publish</span><span></span>
          </div>
          {jobs.map((j) => (
            <div key={j.job_id} className="grid grid-cols-[70px_1fr_120px_140px_140px_90px] gap-3 px-4 py-3 border-b border-line/60 items-center hover:bg-white/[0.02]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={api.artifactUrl(j.job_id, "cover.jpg")} alt="" className="h-14 w-8 rounded object-cover border border-line bg-black/30" onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")} />
              <div className="min-w-0"><div className="text-sm font-medium truncate">{j.job_id}</div><div className="text-[11px] text-ink-faint truncate">{j.summary}</div></div>
              <StatusBadge status={j.status} />
              <span className="text-xs text-ink-muted mono">{j.scores ? `H${j.scores.content_score ?? "—"}/R${j.scores.aesthetic_score ?? "—"}/C${j.scores.compliance_score ?? "—"}` : "—"}</span>
              <span>{j.instagram_post_url ? <a href={j.instagram_post_url} target="_blank" rel="noreferrer" className="text-xs text-teal inline-flex items-center gap-1">Published <ExternalLink size={11} /></a> : <span className="text-xs text-ink-faint">{j.publish_status ?? "—"}</span>}</span>
              <Link href={`/reels/run/${j.job_id}`} className="btn btn-ghost border-line text-xs justify-self-end">Open</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
