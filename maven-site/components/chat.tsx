"use client";
import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ChatAnswer } from "@/lib/types";
import { useMaven } from "./ctx";
import { Pill } from "./ui";
import { useReducedMotionSafe } from "./motion";

const SUGGESTIONS = [
  "Why are banks leading this week?",
  "Explain FPI debt inflows like I am a retail investor.",
  "What sectors benefit from softer crude in India?",
  "Summarize today Indian market in plain English.",
];
const CHIPS = ["Nifty", "Banks", "FII Flows", "RIL", "Oil", "Macro"];

type Msg = { id: number; role: "user" | "assistant"; text?: string; answer?: ChatAnswer; loading?: boolean };

export function ChatMode() {
  const { subject } = useMaven();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [active, setActive] = useState<string[]>([]);
  const idRef = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (subject) setActive((a) => (a.includes(subject) ? a : [...a, subject])); }, [subject]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function send(q: string) {
    const text = q.trim();
    if (!text) return;
    setInput("");
    const uid = idRef.current++;
    const aid = idRef.current++;
    setMsgs((m) => [...m, { id: uid, role: "user", text }, { id: aid, role: "assistant", loading: true }]);
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, subject: active[0] ?? subject ?? null }),
      });
      const answer: ChatAnswer = await r.json();
      setTimeout(() => setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, answer } : x))), 700);
    } catch {
      setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, text: "Could not reach Maven." } : x)));
    }
  }

  const empty = msgs.length === 0;
  return (
    <div className="flex min-h-[62vh] flex-col">
      {empty ? (
        <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
          <h2 className="font-serif text-2xl text-ink">What do you want to understand?</h2>
          <p className="mt-2 max-w-md text-sm text-muted">Ask about a stock, a sector, flows or a macro move. Maven answers India-first - educational, never advice.</p>
          <div className="mt-6 grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="rounded-xl2 border border-hairline bg-panel/60 p-3 text-left text-sm text-muted transition-colors hover:border-border hover:text-ink">
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 space-y-4">
          {msgs.map((m) => (m.role === "user" ? <UserBubble key={m.id} text={m.text ?? ""} /> : <Assistant key={m.id} msg={m} onFollow={send} />))}
          <div ref={endRef} />
        </div>
      )}
      <Composer input={input} setInput={setInput} send={send} chips={CHIPS} active={active} setActive={setActive} />
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-emerald/15 px-4 py-2.5 text-sm text-ink">{text}</div>
    </motion.div>
  );
}

function Assistant({ msg, onFollow }: { msg: Msg; onFollow: (q: string) => void }) {
  if (msg.loading) return <ReasoningLoader />;
  if (msg.answer) return <AnswerCard a={msg.answer} onFollow={onFollow} />;
  return <div className="text-sm text-rose">{msg.text}</div>;
}

function ReasoningLoader() {
  const steps = ["Reviewing index moves", "Checking sector leadership", "Scanning flows and macro", "Composing the answer"];
  const [i, setI] = useState(0);
  const reduce = useReducedMotionSafe();
  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setI((x) => Math.min(x + 1, steps.length - 1)), 600);
    return () => clearInterval(t);
  }, [reduce]);
  return (
    <div className="flex items-center gap-3 rounded-xl2 border border-hairline bg-panel/60 px-4 py-3">
      <span className="h-2 w-2 animate-pulse rounded-full bg-emerald" />
      <AnimatePresence mode="wait">
        <motion.span key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.25 }} className="text-sm text-muted">
          {steps[i]}...
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

const BLOCK_META: Record<ChatAnswer["blocks"][number]["type"], { border: string; tag: string; label: string }> = {
  data: { border: "border-l-emerald-deep/50", tag: "text-muted", label: "Key data" },
  point: { border: "border-l-emerald/50", tag: "text-emerald", label: "Analysis" },
  risk: { border: "border-l-amber/60", tag: "text-amber", label: "Risk" },
  trigger: { border: "border-l-gold/60", tag: "text-gold-soft", label: "What would change the view" },
  takeaway: { border: "border-l-white/15", tag: "text-dim", label: "Final view" },
};

const VERDICT_TONE = {
  constructive: "border-emerald/40 bg-emerald/10 text-emerald",
  neutral: "border-gold/40 bg-gold/10 text-gold-soft",
  cautious: "border-amber/50 bg-amber/10 text-amber",
} as const;

function AnswerCard({ a, onFollow }: { a: ChatAnswer; onFollow: (q: string) => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="rounded-xl2 border border-border bg-panel/70 p-4">
      {(a.verdict || a.demo) && (
        <div className="mb-2.5 flex items-center gap-2">
          {a.verdict && (
            <span className={"inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium " + VERDICT_TONE[a.verdict.tone]}>
              <span className="text-[9px] font-semibold uppercase tracking-label opacity-70">Maven view</span>
              {a.verdict.label}
            </span>
          )}
          {a.demo && <Pill tone="gold">preview</Pill>}
        </div>
      )}
      <h3 className="font-serif text-lg leading-snug text-ink">{a.headline}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">{a.summary}</p>
      <motion.div initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: 0.07 } } }} className="mt-4 space-y-2.5">
        {a.blocks.map((b, i) => {
          const meta = BLOCK_META[b.type];
          return (
            <motion.div key={i} variants={{ hide: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }} className={"rounded-lg border-l-2 bg-panel2/50 py-2 pl-3 pr-3 " + meta.border}>
              <div className="flex items-baseline justify-between gap-2">
                <div className="text-xs font-medium text-ink">{b.title}</div>
                <div className={"shrink-0 text-[9px] font-semibold uppercase tracking-label " + meta.tag}>{meta.label}</div>
              </div>
              <div className="mt-0.5 text-xs leading-relaxed text-muted">{b.body}</div>
            </motion.div>
          );
        })}
      </motion.div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {a.citations.map((c, i) => (
          <span key={i} className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-muted">{c.label} - {c.time}</span>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {a.followups.map((f) => (
          <button key={f} onClick={() => onFollow(f)} className="rounded-full border border-hairline px-3 py-1.5 text-xs text-muted transition-colors hover:border-emerald/40 hover:text-ink">
            {f}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function Composer({ input, setInput, send, chips, active, setActive }: {
  input: string;
  setInput: (s: string) => void;
  send: (q: string) => void;
  chips: string[];
  active: string[];
  setActive: Dispatch<SetStateAction<string[]>>;
}) {
  const toggle = (c: string) => setActive((a) => (a.includes(c) ? a.filter((x) => x !== c) : [...a, c]));
  return (
    <div className="sticky bottom-0 mt-4 border-t border-hairline bg-bg/85 pt-3 backdrop-blur">
      <div className="mb-2 flex flex-wrap gap-1.5">
        {chips.map((c) => (
          <button
            key={c}
            onClick={() => toggle(c)}
            className={"rounded-full border px-2.5 py-1 text-[11px] transition-colors " + (active.includes(c) ? "border-emerald/50 bg-emerald/10 text-emerald" : "border-hairline text-muted hover:text-ink")}
          >
            {c}
          </button>
        ))}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2 rounded-xl2 border border-border bg-panel/70 p-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={1}
          placeholder="Ask about the Indian market..."
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
          className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-ink outline-none placeholder:text-dim"
        />
        <button type="submit" className="rounded-lg bg-emerald px-4 py-2 text-sm font-medium text-bg transition-opacity hover:opacity-90">Ask</button>
      </form>
      <div className="px-1 pb-1 pt-1.5 text-[10px] text-dim">Maven gives educational market context, not investment advice. Preview answers until DeepSeek is connected.</div>
    </div>
  );
}