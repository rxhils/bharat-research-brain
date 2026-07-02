"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/sse";
import type { Artifact, Job, RunNode } from "@/lib/types";
import { statusMeta } from "@/lib/constants";
import { fmtDuration } from "@/lib/format";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { NodeInspector } from "@/components/pipeline/NodeInspector";
import { LiveConsole } from "@/components/pipeline/LiveConsole";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CapabilityBanner } from "@/components/reels/CapabilityBanner";

export default function ReelRunPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { events, connected } = useEventStream(jobId);
  const [job, setJob] = useState<Job | null>(null);
  const [nodes, setNodes] = useState<RunNode[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.job(jobId).then((j) => { setJob(j); setNodes(j.nodes ?? []); }).catch(() => {});
    api.artifacts(jobId).then((a) => setArtifacts(a.artifacts)).catch(() => {});
  }, [jobId]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { if (events.length) api.nodes(jobId).then((r) => setNodes(r.nodes)).catch(() => {}); }, [events.length, jobId]);

  const onAction = useCallback(async (label: string, fn: () => Promise<unknown>) => {
    setToast(`${label}…`);
    try {
      const r: any = await fn();
      setToast(`${label}: ${r?.status ?? "done"}`);
      refresh();
    } catch (e: any) { setToast(`${label}: ${e?.data?.problems?.join(", ") || "failed"}`); }
    setTimeout(() => setToast(null), 3500);
  }, [refresh]);

  const selectedNode = nodes.find((n) => n.node_id === selected) ?? null;

  return (
    <div className="h-[calc(100vh-68px)] flex flex-col">
      <div className="px-6 py-3 border-b border-line flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/reels" className="btn btn-ghost px-2"><ArrowLeft size={15} /></Link>
          <div>
            <div className="text-sm font-semibold">{jobId}</div>
            <div className="text-[11px] text-ink-faint capitalize">reel · {job?.run_type}</div>
          </div>
          {job && <StatusBadge status={job.status} glow />}
        </div>
        {job?.instagram_post_url && (
          <a href={job.instagram_post_url} target="_blank" rel="noreferrer" className="btn btn-primary">View reel</a>
        )}
      </div>

      <div className="px-6 pt-3"><CapabilityBanner /></div>

      <div className="flex-1 grid grid-cols-[230px_1fr_360px] min-h-0">
        <div className="border-r border-line overflow-auto py-2">
          {nodes.filter((n) => n.in_graph === 1 || n.in_graph === true).sort((a, b) => a.ord - b.ord).map((n) => {
            const s = statusMeta(n.status);
            return (
              <button key={n.node_id} onClick={() => setSelected(n.node_id)}
                className={`w-full text-left px-4 py-2 flex items-center gap-2.5 border-l-2 transition-colors ${
                  selected === n.node_id ? "bg-teal/10 border-teal" : "border-transparent hover:bg-white/[0.03]"}`}>
                <span className="h-2 w-2 rounded-full shrink-0" style={{ background: s.color }} />
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] truncate">{n.node_name}</span>
                  <span className="block text-[10px] text-ink-faint truncate">{s.label} · {fmtDuration(n.duration_ms)}</span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="relative min-w-0">
          <PipelineGraph nodes={nodes} selectedId={selected} onSelect={setSelected} />
          {toast && <div className="absolute bottom-3 left-1/2 -translate-x-1/2 chip border-teal/40 text-teal bg-card shadow-card z-10">{toast}</div>}
        </div>

        <div className="border-l border-line min-w-0">
          <NodeInspector jobId={jobId} node={selectedNode} events={events} artifacts={artifacts} onAction={onAction} />
        </div>
      </div>

      <div className="h-[210px] border-t border-line">
        <LiveConsole events={events} connected={connected} />
      </div>
    </div>
  );
}
