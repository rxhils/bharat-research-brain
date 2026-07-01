"use client";
import { useEffect, useState } from "react";
import {
  RotateCw, FastForward, Image as ImageIcon, FileText, RefreshCw, ShieldCheck, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { statusMeta, CLASS_LABEL, isExternal } from "@/lib/constants";
import { fmtDuration, fmtTime } from "@/lib/format";
import type { Artifact, NewsEvent, RunNode } from "@/lib/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ClassBadge } from "@/components/ui/ClassBadge";
import { JsonViewer } from "@/components/ui/JsonViewer";

const TABS = ["Overview", "Live Logs", "Input", "Output", "Artifacts", "Errors", "Replay"] as const;
type Tab = (typeof TABS)[number];

export function NodeInspector({ jobId, node, events, artifacts, onAction }: {
  jobId: string; node: RunNode | null; events: NewsEvent[]; artifacts: Artifact[];
  onAction: (label: string, fn: () => Promise<unknown>) => void;
}) {
  const [tab, setTab] = useState<Tab>("Overview");
  const [outJson, setOutJson] = useState<unknown>(null);

  useEffect(() => {
    setOutJson(null);
    if (node?.output_artifact && node.output_artifact.endsWith(".json") && (tab === "Output" || tab === "Input")) {
      fetch(api.artifactUrl(jobId, node.output_artifact)).then((r) => r.ok ? r.json() : null).then(setOutJson).catch(() => {});
    }
  }, [node, tab, jobId]);

  if (!node) {
    return <div className="h-full grid place-items-center text-ink-faint text-sm px-6 text-center">
      Select a node in the graph to inspect its type, logs, I/O, artifacts and replay controls.
    </div>;
  }

  const nodeEvents = events.filter((e) => e.node_id === node.node_id);
  const nodeArtifacts = artifacts.filter((a) => a.node_id === node.node_id);
  const ext = isExternal(node);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 border-b border-line">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-[15px] font-semibold tracking-tight">{node.node_name}</div>
            <div className="text-[11px] text-ink-faint mono mt-0.5">{node.actual_component}</div>
          </div>
          <StatusBadge status={node.status} glow />
        </div>
        <div className="mt-2.5"><ClassBadge cls={node.component_class} intelligent={node.intelligent} /></div>
      </div>

      <div className="flex gap-1 px-2 py-2 border-b border-line overflow-x-auto">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition-colors ${
              tab === t ? "bg-teal/15 text-teal" : "text-ink-muted hover:text-ink hover:bg-white/5"}`}>
            {t}{t === "Live Logs" && nodeEvents.length ? ` (${nodeEvents.length})` : ""}
            {t === "Artifacts" && nodeArtifacts.length ? ` (${nodeArtifacts.length})` : ""}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4">
        {tab === "Overview" && (
          <dl className="space-y-2.5 text-sm">
            <Row k="Type">{node.component_type} · {CLASS_LABEL[node.component_class as keyof typeof CLASS_LABEL]}</Row>
            <Row k="Intelligent">{node.intelligent ? "Yes — genuine LLM reasoning" : "No — deterministic / service"}</Row>
            <Row k="Role">{node.role}</Row>
            <Row k="Status"><span className={statusMeta(node.status).text}>{statusMeta(node.status).label}</span></Row>
            <Row k="Started">{fmtTime(node.started_at)}</Row>
            <Row k="Completed">{fmtTime(node.completed_at)}</Row>
            <Row k="Duration">{fmtDuration(node.duration_ms)}</Row>
            <Row k="Retries">{node.retry_count ?? 0}</Row>
            <Row k="Progress">{node.progress ?? 0}%</Row>
            {ext && <Row k="Boundary"><span className="text-mcp">External — requires Claude Code conductor</span></Row>}
            {node.summary && <div className="pt-2"><div className="eyebrow mb-1">Result</div><p className="text-ink-muted">{node.summary}</p></div>}
          </dl>
        )}

        {tab === "Live Logs" && (
          <div className="mono text-[12px] space-y-1">
            {nodeEvents.length === 0 ? <Empty>No log events for this node yet.</Empty> :
              nodeEvents.map((e) => (
                <div key={e.event_id} className="flex gap-2">
                  <span className="text-ink-faint">{fmtTime(e.timestamp)}</span>
                  <span className="text-teal/80">{e.event_type}</span>
                  <span className="text-ink truncate">{e.message}</span>
                </div>
              ))}
          </div>
        )}

        {tab === "Input" && (
          node.input_artifact || outJson ? <JsonViewer data={outJson ?? { upstream: node.input_artifact }} maxHeight="60vh" />
            : <Empty>Upstream input is the prior node&apos;s artifact.</Empty>
        )}

        {tab === "Output" && (
          outJson ? <JsonViewer data={outJson} maxHeight="60vh" />
            : node.output_artifact ? <Empty>Output artifact: {node.output_artifact}</Empty>
            : <Empty>No output artifact recorded.</Empty>
        )}

        {tab === "Artifacts" && (
          nodeArtifacts.length === 0 ? <Empty>No artifacts from this node.</Empty> :
          <div className="space-y-2">
            {nodeArtifacts.map((a) => (
              <a key={a.artifact_id} href={api.artifactUrl(jobId, a.name)} target="_blank" rel="noreferrer"
                className="flex items-center gap-2.5 rounded-lg border border-line px-3 py-2 hover:bg-white/[0.04]">
                {a.artifact_type === "image" ? <ImageIcon size={15} className="text-teal" /> : <FileText size={15} className="text-ink-muted" />}
                <span className="text-sm flex-1 truncate">{a.name}</span>
                <span className="text-[10px] text-ink-faint uppercase">{a.artifact_type}</span>
              </a>
            ))}
          </div>
        )}

        {tab === "Errors" && (
          node.error ? <JsonViewer data={node.error} /> :
          <Empty>No errors. {node.retry_count ? `Retried ${node.retry_count}×.` : ""}</Empty>
        )}

        {tab === "Replay" && (
          <div className="grid grid-cols-1 gap-2">
            <Btn icon={RotateCw} label="Rerun This Node" onClick={() => onAction("Rerun", () => api.rerun(jobId, node.node_id))} />
            <Btn icon={FastForward} label="Rerun From Here" onClick={() => onAction("Rerun from here", () => api.rerunFrom(jobId, node.node_id))} />
            <Btn icon={ImageIcon} label="Regenerate Images Only" onClick={() => onAction("Regenerate images", () => api.regenerateImages(jobId))} />
            <Btn icon={FileText} label="Rewrite Caption Only" onClick={() => onAction("Rewrite caption", () => api.rewriteCaption(jobId))} />
            <Btn icon={ShieldCheck} label="Recheck Quality" onClick={() => onAction("Recheck quality", () => api.recheckQuality(jobId))} />
            {ext && <p className="text-[11px] text-mcp mt-1">External nodes (Nano Studio, IG Courier) require the Claude Code conductor — these queue the action and mark the node pending; nothing is faked.</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="flex gap-3"><dt className="w-24 shrink-0 text-ink-faint text-xs pt-0.5">{k}</dt><dd className="text-ink-muted flex-1">{children}</dd></div>;
}
function Empty({ children }: { children: React.ReactNode }) {
  return <div className="text-ink-faint text-sm">{children}</div>;
}
function Btn({ icon: Icon, label, onClick }: { icon: any; label: string; onClick: () => void }) {
  return <button onClick={onClick} className="btn btn-ghost justify-start border-line"><Icon size={15} />{label}</button>;
}
