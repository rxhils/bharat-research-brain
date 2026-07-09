"use client";
/** Agent handoff feed — plays each agent "speaking" as it completes, driven by
 *  the same live SSE event stream as the graph. Text is the real event message
 *  (templated from the latest real run); nothing is invented. */
import { AnimatePresence, motion } from "framer-motion";
import type { NewsEvent } from "@/lib/types";
import { CLASS_ACCENT } from "@/lib/constants";

const SPEAK_EVENTS = new Set([
  "job.created", "job.started", "node.completed", "quality.passed",
  "quality.failed", "approval.required", "job.completed",
  "job.skipped_market_closed",
]);

export function MessageFeed({ events }: { events: NewsEvent[] }) {
  const msgs = events.filter((e) => SPEAK_EVENTS.has(e.event_type));
  return (
    <div className="h-full overflow-auto p-4">
      <div className="eyebrow mb-2">Agent handoffs</div>
      {msgs.length === 0 && (
        <div className="text-[12px] text-ink-faint">
          Waiting for the first agent to speak…
        </div>
      )}
      <div className="space-y-2.5">
        <AnimatePresence initial={false}>
          {msgs.map((e, i) => {
            const accent =
              CLASS_ACCENT[e.component_class as keyof typeof CLASS_ACCENT] || "#94A3B8";
            const left = i % 2 === 0;
            return (
              <motion.div
                key={e.event_id}
                layout
                initial={{ opacity: 0, y: 8, x: left ? -10 : 10 }}
                animate={{ opacity: 1, y: 0, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.26 }}
                className={`flex ${left ? "justify-start" : "justify-end"}`}
              >
                <div
                  className="max-w-[86%] rounded-2xl border border-line bg-card px-3 py-2"
                  style={
                    left
                      ? { borderLeft: `3px solid ${accent}` }
                      : { borderRight: `3px solid ${accent}` }
                  }
                >
                  <div
                    className="text-[11px] font-semibold flex items-center gap-1.5"
                    style={{ color: accent }}
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full shrink-0"
                      style={{ background: accent }}
                    />
                    {e.node_name || e.node_id || "System"}
                    {e.status && (
                      <span className="text-ink-faint font-normal">· {e.status}</span>
                    )}
                  </div>
                  <div className="text-[12.5px] text-ink mt-0.5 leading-snug">
                    {e.message}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
