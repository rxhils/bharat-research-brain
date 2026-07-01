"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { EmptyState } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

export default function ArchivePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { api.jobs().then((r) => setJobs(r.jobs)).catch(() => {}).finally(() => setLoaded(true)); }, []);

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto">
      <div className="mb-4"><div className="eyebrow">Run Archive</div><h2 className="text-xl font-semibold tracking-tight mt-1">Past Closing Bell runs</h2></div>
      {loaded && jobs.length === 0 ? <EmptyState title="No runs yet" hint="Trigger a Closing Bell run from the Dashboard." /> : (
        <div className="glass overflow-hidden">
          <div className="grid grid-cols-[120px_1fr_120px_120px_140px_100px] gap-3 px-4 py-2.5 border-b border-line text-[11px] uppercase tracking-wider text-ink-faint">
            <span>Date</span><span>Run</span><span>Status</span><span>Scores</span><span>Publish</span><span></span>
          </div>
          {jobs.map((j) => (
            <div key={j.job_id} className="grid grid-cols-[120px_1fr_120px_120px_140px_100px] gap-3 px-4 py-3 border-b border-line/60 items-center hover:bg-white/[0.02]">
              <span className="text-sm">{j.date}</span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{j.job_id}</span>
                  <span className="text-[10px] text-ink-faint capitalize">{j.run_type}</span>
                </div>
                <div className="flex gap-1 mt-1">
                  {(j.thumbnails ?? []).map((t) => (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img key={t} src={api.artifactUrl(j.job_id, t)} alt="" className="h-9 w-7 rounded object-cover border border-line" />
                  ))}
                </div>
              </div>
              <StatusBadge status={j.status} />
              <span className="text-xs text-ink-muted mono">
                {j.scores ? `${j.scores.content_score ?? "—"}/${j.scores.design_score ?? "—"}/${j.scores.compliance_score ?? "—"}` : "—"}
              </span>
              <span>{j.instagram_post_url
                ? <a href={j.instagram_post_url} target="_blank" rel="noreferrer" className="text-xs text-teal inline-flex items-center gap-1">Published <ExternalLink size={11} /></a>
                : <span className="text-xs text-ink-faint">{j.publish_status ?? "—"}</span>}</span>
              <Link href={`/run/${j.job_id}`} className="btn btn-ghost border-line text-xs justify-self-end">Open</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
