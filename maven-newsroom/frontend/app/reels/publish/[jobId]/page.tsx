"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Check, Circle, Clock, ExternalLink, Copy } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { Card } from "@/components/ui/Card";

export default function ReelPublishPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [arts, setArts] = useState<string[]>([]);
  useEffect(() => {
    api.job(jobId).then(setJob).catch(() => {});
    api.artifacts(jobId).then((a) => setArts(a.artifacts.map((x) => x.name))).catch(() => {});
  }, [jobId]);

  const published = job?.publish_status === "published";
  const url = job?.instagram_post_url;
  const hasReel = arts.includes("reel.mp4");
  const steps = [
    { label: "Reel built (reel.mp4)", done: hasReel },
    { label: "Quality gate passed", done: job?.scores?.publish_allowed === 1 },
    { label: "Human approval confirmed", done: job?.approval_status === "approved" },
    { label: "Reel uploaded to a public URL", done: published, pending: !published },
    { label: "Reel container created", done: published, pending: !published },
    { label: "Reel published (media_type=REELS)", done: published, pending: !published },
    { label: "Instagram media ID received", done: !!job?.instagram_post_id },
    { label: "Permalink received", done: !!url },
    { label: "Signal Tracker armed", done: published, pending: !published },
  ];

  return (
    <div className="px-6 py-6 max-w-4xl mx-auto space-y-5">
      <div>
        <div className="eyebrow">Reel Publish · Reels Courier (Composio → IG Reels)</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">Publishing status · {jobId}</h2>
      </div>

      {published && url ? (
        <div className="glass card-pad border-ok/40">
          <div className="flex items-center gap-2 text-ok"><Check size={16} /><span className="font-semibold">Reel published</span></div>
          <div className="mt-3 flex gap-2">
            <a href={url} target="_blank" rel="noreferrer" className="btn btn-primary"><ExternalLink size={14} />Open Reel</a>
            <button className="btn btn-ghost border-line" onClick={() => navigator.clipboard.writeText(url)}><Copy size={14} />Copy URL</button>
          </div>
        </div>
      ) : (
        <div className="glass card-pad border-mcp/30 text-sm text-ink-muted">
          Not published. Real Instagram Reels publishing runs in the <span className="text-mcp">Claude Code conductor</span> (Composio) — never claimed without a real media ID.
        </div>
      )}

      <Card>
        <div className="eyebrow mb-3">Publish checklist</div>
        <div className="space-y-1.5">
          {steps.map((s) => (
            <div key={s.label} className="flex items-center gap-2.5 text-sm">
              {s.done ? <Check size={15} className="text-ok" /> : s.pending ? <Clock size={15} className="text-mcp" /> : <Circle size={15} className="text-ink-faint" />}
              <span className={s.done ? "text-ink" : "text-ink-muted"}>{s.label}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
