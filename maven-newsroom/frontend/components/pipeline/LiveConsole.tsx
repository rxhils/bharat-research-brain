"use client";
import { useEffect, useRef } from "react";
import type { NewsEvent } from "@/lib/types";
import { statusMeta } from "@/lib/constants";
import { fmtTime } from "@/lib/format";

const LEVEL: Record<string, string> = {
  "node.failed": "text-danger", "publish.failed": "text-danger", "quality.failed": "text-danger",
  "node.retrying": "text-warn", "approval.required": "text-info",
  "quality.passed": "text-ok", "publish.completed": "text-ok", "job.completed": "text-ok",
};

export function LiveConsole({ events, connected }: { events: NewsEvent[]; connected: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }); }, [events]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-line">
        <div className="flex items-center gap-2">
          <span className="eyebrow">Live Event Stream</span>
          <span className={`chip ${connected ? "border-ok/40 text-ok bg-ok/10" : "border-line text-ink-faint"}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-ok animate-pulse" : "bg-ink-faint"}`} />
            {connected ? "SSE live" : "connecting…"}
          </span>
        </div>
        <span className="text-[11px] text-ink-faint mono">{events.length} events</span>
      </div>
      <div ref={ref} className="flex-1 overflow-auto px-4 py-2.5 mono text-[12px] leading-relaxed">
        {events.length === 0 ? (
          <div className="text-ink-faint">Waiting for events…</div>
        ) : events.map((e) => (
          <div key={e.event_id} className="flex gap-2.5 hover:bg-white/[0.03] rounded px-1 -mx-1">
            <span className="text-ink-faint shrink-0">{fmtTime(e.timestamp)}</span>
            <span className={`shrink-0 ${LEVEL[e.event_type] || "text-teal/80"}`}>{e.event_type}</span>
            {e.node_name && <span className="text-ink-muted shrink-0">{e.node_name}</span>}
            <span className="text-ink truncate">{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
