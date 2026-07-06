"use client";
import { motion } from "framer-motion";
import { EASE, useReducedMotionSafe } from "./motion";
import type { Msg } from "./chat-view";

export type Conversation = { id: string; title: string; messages: Msg[]; updatedAt: number };

function relativeTime(ms: number): string {
  const diff = Date.now() - ms;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return day === 1 ? "yesterday" : `${day}d ago`;
}

export function ChatSidebar({ conversations, activeId, onSelect, onNew, onDelete }: {
  conversations: Conversation[]; activeId: string;
  onSelect: (id: string) => void; onNew: () => void; onDelete: (id: string) => void;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <div className="flex h-full flex-col">
      {/* Primary action - mirrors the composer's send button (emerald gradient, glow). */}
      <button type="button" onClick={onNew}
        className="mb-3 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-emerald to-emerald-deep px-3 py-2.5 text-sm font-medium text-bg shadow-[0_8px_24px_-10px_rgba(52,211,153,0.85)] motion-safe:transition-transform motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M12 5v14M5 12h14" /></svg>
        New chat
      </button>

      <div className="mb-1.5 px-1 text-[10px] uppercase tracking-wider text-dim">History</div>
      {/* One container fade on mount - NO per-row stagger (would read as slop on a nav list). */}
      <motion.div
        initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35, ease: EASE }}
        className="scroll-touch min-h-0 flex-1 space-y-1 overflow-y-auto pr-0.5">
        {conversations.length === 0 && (
          <div className="px-1 py-3 text-xs leading-relaxed text-dim">Your past conversations will appear here.</div>
        )}
        {conversations.map((c) => {
          const active = c.id === activeId;
          return (
            <div key={c.id}
              className={"group relative overflow-hidden rounded-lg border px-2.5 py-2 text-left transition-colors focus-within:border-emerald/40 " + (active
                ? "border-emerald/25 bg-emerald/[0.06]"
                : "border-transparent hover:border-hairline hover:bg-white/[0.03]")}>
              {/* Restrained active indicator: a single emerald hairline rule on the left edge. */}
              {active && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-emerald/80" aria-hidden />}
              <button type="button" onClick={() => onSelect(c.id)}
                className="block w-full text-left motion-safe:transition-transform motion-safe:duration-150 motion-safe:active:scale-[0.985]">
                <div className={"truncate pr-5 text-[13px] leading-snug " + (active ? "text-ink" : "text-ink/80")}>{c.title || "New chat"}</div>
                <div className="mt-0.5 text-[10px] text-dim">{relativeTime(c.updatedAt)}</div>
              </button>
              {/* Delete affordance: hidden until the row is hovered or anything inside it is focused (keyboard-reachable). */}
              <button type="button" onClick={() => onDelete(c.id)} aria-label="Delete conversation"
                className="absolute right-1 top-1 rounded-md p-1.5 text-dim opacity-0 transition-[opacity,color] hover:text-rose focus-visible:opacity-100 focus-visible:text-rose focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 group-hover:opacity-100">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </div>
          );
        })}
      </motion.div>
    </div>
  );
}
