"use client";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { EASE, useReducedMotionSafe } from "./motion";
import { ChatView, type Msg } from "./chat-view";
import { ChatSidebar, type Conversation } from "./chat-sidebar";

const STORAGE_KEY = "maven_chat_history";
const MAX_CONVERSATIONS = 20;

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return []; // corrupt/unavailable storage - chat still works, just without history
  }
}

function saveConversations(list: Conversation[]) {
  try {
    const trimmed = [...list].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_CONVERSATIONS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch { /* storage full/unavailable - conversation just won't persist */ }
}

function titleFrom(msgs: Msg[]): string {
  const t = (msgs.find((m) => m.role === "user" && m.text)?.text || "").trim();
  return t.length > 48 ? t.slice(0, 48) + "…" : t;
}

// Chart datasets are the bulk of a stored message; strip them from persisted history so
// localStorage stays small. The text/blocks/sources still render correctly on restore.
function stripCharts(msgs: Msg[]): Msg[] {
  return msgs.map((m) => (m.answer ? { ...m, answer: { ...m.answer, charts: [] } } : m));
}

function newId(): string {
  return "c_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8);
}

export function ChatShell() {
  const reduce = useReducedMotionSafe();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  // Generated synchronously (not deferred) - `key` is never serialized into HTML, so a
  // different random id between the server pass and client hydration can't cause a mismatch.
  // Deferring it caused a spurious remount right after mount even with no history to resume.
  const [activeId, setActiveId] = useState<string>(() => newId());
  const [drawerOpen, setDrawerOpen] = useState(false);
  const hydrated = useRef(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const historyBtnRef = useRef<HTMLButtonElement>(null);
  const drawerWasOpen = useRef(false);

  useEffect(() => {
    const loaded = loadConversations();
    setConversations(loaded);
    if (loaded.length) setActiveId(loaded[0].id); // resume the most recent conversation, like Claude/ChatGPT do
    hydrated.current = true;
  }, []);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawerOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  // Dialog focus discipline: move focus into the drawer when it opens, and hand
  // it back to the History trigger when it closes (keyboard users keep their place).
  useEffect(() => {
    if (drawerOpen) {
      drawerWasOpen.current = true;
      drawerRef.current?.focus();
    } else if (drawerWasOpen.current) {
      drawerWasOpen.current = false;
      historyBtnRef.current?.focus();
    }
  }, [drawerOpen]);

  function handleMessagesChange(msgs: Msg[]) {
    if (!hydrated.current || msgs.length === 0) return;
    setConversations((prev) => {
      const idx = prev.findIndex((c) => c.id === activeId);
      const updated: Conversation = { id: activeId, title: titleFrom(msgs), messages: stripCharts(msgs), updatedAt: Date.now() };
      const next = idx === -1 ? [updated, ...prev] : prev.map((c, i) => (i === idx ? updated : c));
      saveConversations(next);
      return next;
    });
  }

  function handleNew() { setActiveId(newId()); setDrawerOpen(false); }
  function handleSelect(id: string) { setActiveId(id); setDrawerOpen(false); }
  function handleDelete(id: string) {
    setConversations((prev) => { const next = prev.filter((c) => c.id !== id); saveConversations(next); return next; });
    if (id === activeId) setActiveId(newId());
  }

  const active = conversations.find((c) => c.id === activeId);

  return (
    <div className="flex items-start gap-6">
      {/* The library earns its place: no rail at all until history exists. */}
      {conversations.length > 0 && (
        <aside className="sticky top-20 hidden h-[calc(100dvh-6rem)] w-60 shrink-0 lg:block">
          <ChatSidebar conversations={conversations} activeId={activeId} onSelect={handleSelect} onNew={handleNew} onDelete={handleDelete} />
        </aside>
      )}

      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div className="fixed inset-0 z-30 bg-black/60 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }} onClick={() => setDrawerOpen(false)} aria-hidden />
            <motion.div ref={drawerRef} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Chat history"
              initial={reduce ? { opacity: 0 } : { x: "-100%" }} animate={{ x: 0, opacity: 1 }} exit={reduce ? { opacity: 0 } : { x: "-100%" }}
              transition={{ duration: 0.22, ease: EASE }}
              style={{ paddingLeft: "max(0.75rem, var(--sal))", paddingTop: "max(0.75rem, var(--sat))", paddingBottom: "max(0.75rem, var(--sab))" }}
              className="fixed inset-y-0 left-0 z-40 w-72 max-w-[80vw] border-r border-hairline bg-panel/95 pr-3 backdrop-blur-xl lg:hidden">
              <ChatSidebar conversations={conversations} activeId={activeId} onSelect={handleSelect} onNew={handleNew} onDelete={handleDelete} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <div className="min-w-0 flex-1">
        {conversations.length > 0 && (
        <div className="mb-3 lg:hidden">
          <button ref={historyBtnRef} type="button" onClick={() => setDrawerOpen(true)} aria-haspopup="dialog" aria-expanded={drawerOpen}
            className={`inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white/[0.03] px-3 py-1.5 text-xs text-muted motion-safe:transition-[color,border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/40 hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60`}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 12h18M3 6h18M3 18h18" /></svg>
            History
          </button>
        </div>
        )}
        <ChatView key={activeId} initialMessages={active?.messages} onMessagesChange={handleMessagesChange} />
      </div>
    </div>
  );
}
