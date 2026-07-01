"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Check, Circle, Clock, ExternalLink, Copy } from "lucide-react";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/sse";
import type { Job } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { fmtTime } from "@/lib/format";

export default function PublishPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { events } = useEventStream(jobId);
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => { api.job(jobId).then(setJob).catch(() => {}); }, [jobId, events.length]);

  const published = job?.publish_status === "published";
  const url = job?.instagram_post_url;
  const sc = job?.scores;
  const has = (re: RegExp) => events.some((e) => re.test(e.event_type) || re.test(e.message));

  const steps: { label: string; done: boolean; pending?: boolean }[] = [
    { label: "Preflight started", done: has(/publish\.started|preflight/i) || published },
    { label: "Quality gate confirmed", done: sc?.publish_allowed === 1 },
    { label: "Human approval confirmed", done: job?.approval_status === "approved" },
    { label: "Images validated", done: (job?.artifact_count ?? 0) > 0 },
    { label: "Images uploaded via Composio workbench", done: published, pending: !published },
    { label: "Carousel container created", done: published, pending: !published },
    { label: "Media published", done: published, pending: !published },
    { label: "Instagram media ID received", done: !!job?.instagram_post_id },
    { label: "Permalink received", done: !!url },
    { label: "Run Vault updated", done: published },
  ];

  return (
    <div className="px-6 py-6 max-w-4xl mx-auto space-y-5">
      <div>
        <div className="eyebrow">Publish Console · IG Courier (Composio → Instagram)</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">Publishing status · {jobId}</h2>
      </div>

      {published && url ? (
        <div className="glass card-pad border-ok/40">
          <div className="flex items-center gap-2 text-ok"><Check size={16} /><span className="font-semibold">Published successfully</span></div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <a href={url} target="_blank" rel="noreferrer" className="btn btn-primary"><ExternalLink size={14} />Open Instagram</a>
            <button className="btn btn-ghost border-line" onClick={() => navigator.clipboard.writeText(url)}><Copy size={14} />Copy URL</button>
          </div>
          <dl className="mt-3 text-xs text-ink-muted space-y-1">
            <div>Media ID: <span className="mono">{job?.instagram_post_id}</span></div>
            <div>Permalink: <span className="mono">{url}</span></div>
          </dl>
        </div>
      ) : (
        <div className="glass card-pad border-mcp/30">
          <div className="text-sm text-ink-muted">
            Not published. Real Instagram publishing runs in the <span className="text-mcp">Claude Code conductor</span> (Composio MCP) — the backend cannot reach Instagram directly, so it never claims a publish without a real media ID.
          </div>
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

      <Card>
        <div className="eyebrow mb-2">Publish events</div>
        <div className="mono text-[12px] space-y-1 max-h-64 overflow-auto">
          {events.filter((e) => /publish|approval/.test(e.event_type)).map((e) => (
            <div key={e.event_id} className="flex gap-2"><span className="text-ink-faint">{fmtTime(e.timestamp)}</span><span className="text-teal/80">{e.event_type}</span><span className="text-ink truncate">{e.message}</span></div>
          ))}
          {events.filter((e) => /publish|approval/.test(e.event_type)).length === 0 && <span className="text-ink-faint">No publish events yet.</span>}
        </div>
      </Card>
    </div>
  );
}
