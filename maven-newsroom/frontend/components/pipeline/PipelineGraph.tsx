"use client";
import { useMemo } from "react";
import ReactFlow, {
  Background, BackgroundVariant, Controls, Handle, Position, type Edge, type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { RunNode } from "@/lib/types";
import { statusMeta, isExternal, CLASS_ACCENT } from "@/lib/constants";
import { fmtDuration } from "@/lib/format";

function NodeCard({ data }: { data: { node: RunNode; selected: boolean } }) {
  const n = data.node;
  const s = statusMeta(n.status);
  const ext = isExternal(n);
  const live = n.status === "running" || n.status === "progress";
  return (
    <div
      className={`w-[230px] rounded-xl border bg-card-raised/95 px-3.5 py-3 transition-all ${
        data.selected ? "border-teal shadow-glow" : ext ? "border-mcp/40" : "border-line"
      } ${live ? "animate-pulseGlow" : ""}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0" />
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border"
          style={{ borderColor: `${CLASS_ACCENT[n.component_class as keyof typeof CLASS_ACCENT] || "#94A3B8"}55`,
                   color: CLASS_ACCENT[n.component_class as keyof typeof CLASS_ACCENT] || "#94A3B8" }}>
          {n.component_class === "Cprime" ? "C′" : n.component_class}
        </span>
        <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
      </div>
      <div className="mt-1.5 text-[13px] font-semibold leading-tight text-ink">{n.node_name}</div>
      <div className="text-[10px] text-ink-faint truncate">{n.component_type}{ext ? " · external" : ""}</div>
      <div className="mt-2 flex items-center justify-between">
        <span className={`text-[10px] ${s.text}`}>{s.label}</span>
        <span className="text-[10px] text-ink-faint mono">{fmtDuration(n.duration_ms)}</span>
      </div>
      {live && n.progress > 0 && (
        <div className="mt-1.5 h-1 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full bg-teal transition-all" style={{ width: `${n.progress}%` }} />
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0" />
    </div>
  );
}

const nodeTypes = { pipeline: NodeCard };

export function PipelineGraph({ nodes, selectedId, onSelect }: {
  nodes: RunNode[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  const graphNodes = useMemo<Node[]>(() => {
    const inGraph = nodes.filter((n) => n.in_graph === 1 || n.in_graph === true)
      .sort((a, b) => a.ord - b.ord);
    return inGraph.map((n, i) => ({
      id: n.node_id,
      type: "pipeline",
      position: { x: (i % 2) * 286, y: i * 96 },
      data: { node: n, selected: n.node_id === selectedId },
    }));
  }, [nodes, selectedId]);

  const edges = useMemo<Edge[]>(() => {
    const inGraph = nodes.filter((n) => n.in_graph === 1 || n.in_graph === true)
      .sort((a, b) => a.ord - b.ord);
    return inGraph.slice(0, -1).map((n, i) => {
      const next = inGraph[i + 1];
      const animated = n.status === "running" || n.status === "progress";
      return { id: `${n.node_id}-${next.node_id}`, source: n.node_id, target: next.node_id,
               animated, style: { stroke: animated ? "#1FB6A6" : "rgba(148,163,184,0.3)" } };
    });
  }, [nodes]);

  return (
    <ReactFlow
      nodes={graphNodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, node) => onSelect(node.id)}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.3}
      maxZoom={1.4}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#1b2430" />
      <Controls className="!bg-card !border-line !rounded-lg" showInteractive={false} />
    </ReactFlow>
  );
}
