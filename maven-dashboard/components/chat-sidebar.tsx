"use client";
import { motion } from "framer-motion";
import { EASE, useReducedMotionSafe } from "./motion";
import type { Msg } from "./chat-view";

export type Conversation = { id: string; title: string; messages: Msg[]; updatedAt: number };

type Bucket = "TODAY" | "THIS WEEK" | "EARLIER";
const BUCKET_ORDER: Bucket[] = ["TODAY", "THIS WEEK", "EARLIER"];

// Date-group headers (mono, uppercase) replace the old per-row relative timestamps.
function bucketOf(ms: number): Bucket {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const todayStart = start.getTime();
  if (ms >= todayStart) return "TODAY";
  if (ms >= todayStart - 6 * 86_400_000) return "THIS WEEK"; // trailing 7 days, today excluded
  return "EARLIER";
}

export function ChatSidebar({ conversations, activeId, onSelect, onNew, onDelete, railId = "chat-active-rail" }: {
  conversations: Conversation[]; activeId: string;
  onSelect: (id: string) => void; onNew: () => void; onDelete: (id: string) => void;
  // Distinct per mounted instance (desktop aside vs. mobile drawer) so the two
  // don't share one layout animation while both are in the DOM.
  railId?: string;
}) {
  const reduce = useReducedMotionSafe();
  // Newest first, then partitioned into date buckets (order preserved within each).
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
  const groups: Record<Bucket, Conversation[]> = { TODAY: [], "THIS WEEK": [], EARLIER: [] };
  for (const c of sorted) groups[bucketOf(c.updatedAt)].push(c);
  const railTransition = reduce ? { duration: 0 } : ({ type: "spring", stiffness: 400, damping: 34 } as const);

  return (
    <div className="flex h-full flex-col">
      {/* Primary action - mirrors the composer's send button (emerald gradient, glow). */}
      <button type="button" onClick={onNew}
        className="mb-3 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-emerald to-emerald-deep px-3 py-2.5 text-sm font-medium text-bg shadow-[0_8px_24px_-10px_rgba(52,211,153,0.85)] motion-safe:transition-transform motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M12 5v14M5 12h14" /></svg>
        New chat
      </button>

      {/* One container fade on mount - NO per-row stagger (would read as slop on a nav list). */}
      <motion.div
        initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35, ease: EASE }}
        className="scroll-touch min-h-0 flex-1 space-y-3 overflow-y-auto pr-0.5">
        {conversations.length === 0 && (
          <div className="px-1 py-3 text-xs leading-relaxed text-dim">Your past conversations will appear here.</div>
        )}
        {BUCKET_ORDER.filter((b) => groups[b].length > 0).map((bucket) => (
          <div key={bucket} className="space-y-1">
            <div className="px-1 font-mono text-[10px] uppercase tracking-[0.18em] text-dim">{bucket}</div>
            {groups[bucket].map((c) => {
              const active = c.id === activeId;
              return (
                <div key={c.id}
                  className={"group relative overflow-hidden rounded-lg border px-2.5 py-2 text-left transition-colors focus-within:border-emerald/40 " + (active
                    ? "border-emerald/25 bg-emerald/[0.06]"
                    : "border-transparent hover:border-hairline hover:bg-white/[0.03]")}>
                  {/* Active indicator slides between rows via shared layout (spring); freezes under reduced motion. */}
                  {active && <motion.span layoutId={railId} transition={railTransition} className="absolute inset-y-1.5 left-0 w-px rounded-full bg-emerald/80" aria-hidden />}
                  <button type="button" onClick={() => onSelect(c.id)}
                    className="block w-full text-left motion-safe:transition-transform motion-safe:duration-150 motion-safe:active:scale-[0.985]">
                    <div className={"truncate pr-5 text-[13px] leading-snug " + (active ? "text-ink" : "text-ink/80")}>{c.title || "New chat"}</div>
                  </button>
                  {/* Delete affordance: hidden until the row is hovered or anything inside it is focused (keyboard-reachable). */}
                  <button type="button" onClick={() => onDelete(c.id)} aria-label="Delete conversation"
                    className="absolute right-1 top-1 rounded-md p-1.5 text-dim opacity-0 transition-[opacity,color] hover:text-rose focus-visible:opacity-100 focus-visible:text-rose focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 group-hover:opacity-100">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                </div>
              );
            })}
          </div>
        ))}
      </motion.div>
    </div>
  );
}
