"use client";
import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { motion, AnimatePresence, useMotionValue } from "framer-motion";
import { useReducedMotionSafe } from "./motion";
import { MavenChartRenderer } from "./maven-charts";
import type { MavenAskResponse } from "@/lib/maven-types";

const SUGGESTIONS = [
  { t: "Why are banks leading this week?", k: "Sector leadership" },
  { t: "Explain FPI debt inflows like I am a retail investor.", k: "Flows, simplified" },
  { t: "What sectors benefit from softer crude in India?", k: "Macro knock-on" },
  { t: "Summarize today Indian market in plain English.", k: "Market wrap" },
];
const CHIPS = ["Nifty", "Banks", "FII Flows", "RIL", "Oil", "Macro", "RBI"];
const EASE = [0.22, 1, 0.36, 1] as const;

type Msg = { id: number; role: "user" | "assistant"; text?: string; answer?: MavenAskResponse; loading?: boolean };

function MavenMark({ size = 26, draw = false }: { size?: number; draw?: boolean }) {
  const reduce = useReducedMotionSafe();
  const a = draw && !reduce;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" role="img" aria-label="Maven">
      <motion.path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"
        initial={a ? { pathLength: 0, opacity: 0 } : false} animate={a ? { pathLength: 1, opacity: 1 } : undefined} transition={{ duration: 0.9, ease: EASE }} />
      <motion.path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round"
        initial={a ? { pathLength: 0, opacity: 0 } : false} animate={a ? { pathLength: 1, opacity: 1 } : undefined} transition={{ duration: 0.8, delay: 0.45, ease: EASE }} />
      <motion.circle cx="89" cy="17" r="8" fill="#34d399"
        initial={a ? { scale: 0, opacity: 0 } : false} animate={a ? { scale: 1, opacity: 1 } : undefined} transition={{ duration: 0.4, delay: 1.05, ease: EASE }} />
    </svg>
  );
}

function Core({ size = 92 }: { size?: number }) {
  const reduce = useReducedMotionSafe();
  const ringMask = "radial-gradient(circle, transparent 55%, #000 57%, #000 70%, transparent 73%)";
  const ringMask2 = "radial-gradient(circle, transparent 72%, #000 74%, #000 82%, transparent 84%)";
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <motion.span className="absolute inset-0 rounded-full bg-emerald/20 blur-2xl" aria-hidden
        animate={reduce ? undefined : { scale: [1, 1.3, 1], opacity: [0.4, 0.85, 0.4] }} transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }} />
      <motion.span className="absolute rounded-full" aria-hidden
        style={{ width: size, height: size, background: "conic-gradient(from 0deg, rgba(52,211,153,0), rgba(52,211,153,0.85), rgba(201,169,97,0.45), rgba(52,211,153,0))", maskImage: ringMask, WebkitMaskImage: ringMask }}
        animate={reduce ? undefined : { rotate: 360 }} transition={{ duration: 16, repeat: Infinity, ease: "linear" }} />
      <motion.span className="absolute rounded-full" aria-hidden
        style={{ width: size, height: size, background: "conic-gradient(from 180deg, rgba(201,169,97,0), rgba(52,211,153,0.4), rgba(201,169,97,0))", maskImage: ringMask2, WebkitMaskImage: ringMask2 }}
        animate={reduce ? undefined : { rotate: -360 }} transition={{ duration: 24, repeat: Infinity, ease: "linear" }} />
      {!reduce && (
        <motion.div className="absolute inset-0" aria-hidden animate={{ rotate: 360 }} transition={{ duration: 9, repeat: Infinity, ease: "linear" }}>
          <span className="absolute left-1/2 top-0.5 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-emerald shadow-[0_0_12px_rgba(52,211,153,0.9)]" />
        </motion.div>
      )}
      <span className="relative grid place-items-center rounded-full border border-emerald/25" style={{ width: size * 0.56, height: size * 0.56, background: "radial-gradient(circle at 50% 32%, #15191d, #0a0b0e)" }}>
        <MavenMark size={Math.round(size * 0.32)} draw />
      </span>
    </div>
  );
}

function Avatar({ thinking = false }: { thinking?: boolean }) {
  const reduce = useReducedMotionSafe();
  return (
    <div className="relative mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-emerald/25 sm:h-9 sm:w-9" style={{ background: "radial-gradient(circle at 50% 30%, #15191d, #0b0c0f)" }}>
      <span className="absolute inset-0 rounded-xl bg-emerald/10 blur-md" aria-hidden />
      {thinking && !reduce && (
        <motion.span className="absolute inset-0 rounded-xl ring-1 ring-emerald/50" aria-hidden animate={{ opacity: [0.2, 0.8, 0.2], scale: [1, 1.1, 1] }} transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }} />
      )}
      <span className="relative"><MavenMark size={17} /></span>
    </div>
  );
}

function AuroraBg() {
  const reduce = useReducedMotionSafe();
  const grid = "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.055) 1px, transparent 0)";
  const fade = "radial-gradient(ellipse 75% 60% at 50% 35%, #000 25%, transparent 78%)";
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <motion.div className="absolute left-[12%] top-[8%] h-[24rem] w-[24rem] rounded-full bg-emerald/[0.11] blur-[120px] sm:h-[32rem] sm:w-[32rem]"
        animate={reduce ? undefined : { x: [0, 60, -20, 0], y: [0, 40, 80, 0], scale: [1, 1.15, 1] }} transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="absolute right-[2%] top-[20%] h-[22rem] w-[22rem] rounded-full bg-emerald-deep/[0.10] blur-[120px] sm:h-[28rem] sm:w-[28rem]"
        animate={reduce ? undefined : { x: [0, -50, 20, 0], y: [0, 60, -30, 0], scale: [1, 1.22, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "easeInOut", delay: 1 }} />
      <motion.div className="absolute bottom-[2%] left-[30%] h-[20rem] w-[20rem] rounded-full bg-gold/[0.06] blur-[120px] sm:h-[24rem] sm:w-[24rem]"
        animate={reduce ? undefined : { x: [0, 40, -40, 0], y: [0, -30, 30, 0], scale: [1, 1.12, 1] }} transition={{ duration: 22, repeat: Infinity, ease: "easeInOut", delay: 2 }} />
      <div className="absolute inset-0" style={{ backgroundImage: grid, backgroundSize: "34px 34px", maskImage: fade, WebkitMaskImage: fade }} />
    </div>
  );
}

function GlassPanel({ children, className = "", tlSharp = false }: { children: React.ReactNode; className?: string; tlSharp?: boolean }) {
  return (
    <div className={"rounded-2xl bg-gradient-to-b from-emerald/25 via-white/[0.06] to-transparent p-px " + (tlSharp ? "rounded-tl-md " : "") + className}>
      <div className={"h-full rounded-2xl bg-panel/45 backdrop-blur-xl " + (tlSharp ? "rounded-tl-md" : "")}>{children}</div>
    </div>
  );
}

export function ChatView() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [active, setActive] = useState<string[]>([]);
  const idRef = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs]);

  async function send(q: string) {
    const text = q.trim();
    if (!text) return;
    setInput("");
    const uid = idRef.current++;
    const aid = idRef.current++;
    setMsgs((m) => [...m, { id: uid, role: "user", text }, { id: aid, role: "assistant", loading: true }]);
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: text }) });
      const answer: MavenAskResponse = await r.json();
      setTimeout(() => setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, answer } : x))), 600);
    } catch {
      setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, text: "Could not reach Maven." } : x)));
    }
  }

  const empty = msgs.length === 0;
  return (
    <div className={"relative mx-auto flex max-w-3xl flex-col" + (empty ? "" : " min-h-[58vh]")}>
      <AuroraBg />
      {empty ? <Hero onPick={send} /> : (
        <div className="flex-1 space-y-6">
          {msgs.map((m) => (m.role === "user" ? <UserBubble key={m.id} text={m.text ?? ""} /> : (
            <motion.div key={m.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }} className="flex gap-2.5 sm:gap-3">
              <Avatar thinking={!!m.loading} />
              <div className="min-w-0 flex-1">
                {m.loading ? <ReasoningLoader /> : m.answer ? <AnswerCard a={m.answer} onFollow={send} /> : <div className="pt-2 text-sm text-rose">{m.text}</div>}
              </div>
            </motion.div>
          )))}
          <div ref={endRef} />
        </div>
      )}
      <Composer input={input} setInput={setInput} send={send} active={active} setActive={setActive} empty={empty} />
    </div>
  );
}

function Hero({ onPick }: { onPick: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  const up = { hide: reduce ? { opacity: 1 } : { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } } };
  return (
    <motion.div className="flex flex-col items-center justify-center py-5 text-center sm:py-7" initial="hide" animate="show"
      variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.1 } } }}>
      <motion.div variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, scale: 0.8 }, show: { opacity: 1, scale: 1, transition: { duration: 0.8, ease: EASE } } }}>
        <Core />
      </motion.div>
      <motion.h2 variants={up} className="mt-5 font-serif text-[1.9rem] leading-[1.12] text-ink sm:text-[2.7rem]">
        What do you want to{" "}
        <span className="bg-gradient-to-r from-emerald via-gold-soft to-emerald bg-clip-text italic text-transparent animate-shimmer" style={{ backgroundSize: "200% auto" }}>understand</span>?
      </motion.h2>
      <motion.p variants={up} className="mt-2.5 max-w-md px-2 text-[0.8rem] leading-relaxed text-ink/60 sm:text-sm">
        Ask about a stock, sector, flows or a macro move &mdash; Maven explains what moved and why it matters, India-first.
      </motion.p>
      <motion.div className="mt-6 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: 0.15 } } }}>
        {SUGGESTIONS.map((s) => <SuggestionCard key={s.t} s={s} onPick={onPick} />)}
      </motion.div>
    </motion.div>
  );
}

function SuggestionCard({ s, onPick }: { s: { t: string; k: string }; onPick: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  function move(e: React.MouseEvent<HTMLButtonElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    ry.set(((e.clientX - r.left) / r.width - 0.5) * 8);
    rx.set(-((e.clientY - r.top) / r.height - 0.5) * 8);
  }
  function leave() { rx.set(0); ry.set(0); }
  return (
    <motion.button onClick={() => onPick(s.t)}
      variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } } }}
      onMouseMove={reduce ? undefined : move} onMouseLeave={leave}
      style={reduce ? undefined : { rotateX: rx, rotateY: ry, transformPerspective: 700 }}
      whileHover={reduce ? undefined : { scale: 1.02 }} transition={{ type: "spring", stiffness: 280, damping: 20 }}
      className="group relative overflow-hidden rounded-2xl bg-gradient-to-b from-white/[0.08] to-transparent p-px text-left">
      <div className="relative overflow-hidden rounded-2xl bg-panel/55 p-3.5 backdrop-blur-md transition-colors group-hover:bg-panel/75">
        <span className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-gradient-to-r from-emerald/0 via-emerald to-emerald/0 transition-transform duration-500 group-hover:scale-x-100" aria-hidden />
        <span className="pointer-events-none absolute -right-12 -top-12 h-28 w-28 rounded-full bg-emerald/0 blur-2xl transition-colors duration-500 group-hover:bg-emerald/15" aria-hidden />
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-dim">
          <span className="h-1 w-1 rounded-full bg-emerald/80" />{s.k}
        </div>
        <div className="mt-1.5 flex items-start justify-between gap-3">
          <span className="text-[0.9rem] leading-snug text-ink">{s.t}</span>
          <span className="mt-0.5 shrink-0 text-emerald opacity-0 transition-all duration-300 group-hover:translate-x-0.5 group-hover:opacity-100" aria-hidden>&rarr;</span>
        </div>
      </div>
    </motion.button>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: EASE }} className="flex justify-end">
      <div className="max-w-[82%] rounded-2xl rounded-br-md border border-emerald/25 bg-gradient-to-br from-emerald/20 to-emerald/[0.06] px-4 py-2.5 text-sm leading-relaxed text-ink shadow-[0_12px_36px_-20px_rgba(52,211,153,0.7)]">
        {text}
      </div>
    </motion.div>
  );
}

function ReasoningLoader() {
  const steps = ["Reading market context", "Checking sector drivers", "Building mechanism chain", "Preparing Maven view"];
  const [i, setI] = useState(0);
  const reduce = useReducedMotionSafe();
  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setI((x) => Math.min(x + 1, steps.length - 1)), 750);
    return () => clearInterval(t);
  }, [reduce]);
  return (
    <GlassPanel tlSharp className="inline-block">
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex h-5 items-end gap-1" aria-hidden>
          {[0, 1, 2, 3].map((d) => (
            <motion.span key={d} className="w-1 rounded-full bg-emerald" animate={reduce ? { height: 8 } : { height: [5, 18, 5] }} transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut", delay: d * 0.13 }} />
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.span key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.25 }} className="text-sm text-ink/70">
            {steps[i]}&hellip;
          </motion.span>
        </AnimatePresence>
      </div>
    </GlassPanel>
  );
}

function blockGlyph(type: string): { dot: string; label: string } {
  const t = (type || "").toLowerCase();
  if (t === "risk") return { dot: "bg-amber shadow-[0_0_8px_rgba(251,191,36,0.7)]", label: "text-amber" };
  if (t === "takeaway") return { dot: "bg-gold shadow-[0_0_8px_rgba(201,169,97,0.7)]", label: "text-gold-soft" };
  if (t === "data") return { dot: "bg-emerald-deep shadow-[0_0_8px_rgba(16,185,129,0.7)]", label: "text-emerald" };
  if (t === "macro") return { dot: "bg-gold-soft shadow-[0_0_8px_rgba(201,169,97,0.6)]", label: "text-gold-soft" };
  if (t === "context") return { dot: "bg-white/50", label: "text-muted" };
  return { dot: "bg-emerald shadow-[0_0_8px_rgba(52,211,153,0.8)]", label: "text-emerald" };
}

function AnswerCard({ a, onFollow }: { a: MavenAskResponse; onFollow: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  const answerType = a.answerType ?? a.type ?? "market_mechanism";
  const minimal = answerType === "greeting" || answerType === "out_of_scope";
  const blocks = a.blocks ?? [];
  const charts = a.charts ?? [];
  const keyData = a.keyData ?? [];
  const sources = a.sources ?? [];
  const limitations = a.limitations ?? [];
  const followUps = a.followUps ?? [];
  return (
    <motion.div initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: EASE }}>
      <GlassPanel tlSharp>
        <div className="relative overflow-hidden rounded-2xl rounded-tl-md p-4 sm:p-5">
          {!reduce && (
            <motion.span className="pointer-events-none absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" aria-hidden initial={{ x: "-130%" }} animate={{ x: "230%" }} transition={{ duration: 1.1, ease: EASE, delay: 0.15 }} />
          )}
          <span className="pointer-events-none absolute -right-20 -top-24 h-48 w-48 rounded-full bg-emerald/[0.08] blur-3xl" aria-hidden />
          <span className="pointer-events-none absolute left-0 top-5 bottom-5 w-px bg-gradient-to-b from-emerald/0 via-emerald/60 to-emerald/0" aria-hidden />

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-dim">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_8px_rgba(52,211,153,0.9)]" />Maven
            </div>
            <span className="shrink-0 rounded-md bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wider text-dim">India markets</span>
          </div>

          <h3 className="mt-2.5 font-serif text-[1.45rem] leading-snug text-ink sm:text-[1.6rem]">{a.headline}</h3>
          {a.summary && <p className="mt-2 text-sm leading-relaxed text-ink/70">{a.summary}</p>}

          {!minimal && keyData.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {keyData.map((d, i) => (
                <div key={i} className="rounded-lg border border-hairline bg-white/[0.02] px-2.5 py-1.5">
                  <div className="text-[9px] uppercase tracking-wider text-dim">{d.label}</div>
                  <div className="tnum text-sm text-ink">{d.value}{d.change && <span className={"ml-1 text-[11px] " + (d.change.trim().startsWith("-") ? "text-rose" : "text-emerald")}>{d.change}</span>}</div>
                </div>
              ))}
            </div>
          )}

          {!minimal && charts.length > 0 && <div className="mt-4"><MavenChartRenderer charts={charts} /></div>}

          {blocks.length > 0 && (
            <motion.div className="mt-5 space-y-2.5" initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.1, delayChildren: 0.05 } } }}>
              {blocks.map((b, i) => {
                const g = blockGlyph(b.type);
                return (
                  <motion.div key={i} variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, y: 12, filter: "blur(6px)" }, show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.5, ease: EASE } } }} className="rounded-xl border border-hairline bg-white/[0.02] p-3.5">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <span className={"h-1.5 w-1.5 shrink-0 rounded-full " + g.dot} />
                      <span className={"text-[10px] font-semibold uppercase tracking-[0.16em] " + g.label}>{b.type}</span>
                      <span className="text-[0.9rem] font-medium text-ink">{b.title}</span>
                    </div>
                    <p className="mt-1.5 pl-3.5 text-[0.83rem] leading-relaxed text-ink/65">{b.body}</p>
                  </motion.div>
                );
              })}
            </motion.div>
          )}

          {!minimal && sources.length > 0 && (
            <div className="mt-5 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-dim">Sources</span>
              {sources.map((s, i) => {
                const meta = s.date || s.recency;
                const dot = s.confidence === "verified" || s.confidence === "retrieved" ? "bg-emerald/70" : "bg-white/30";
                const inner = (
                  <span className="inline-flex items-center gap-1.5">
                    <span className={"h-1 w-1 rounded-full " + dot} aria-hidden />
                    {s.name}{meta ? " · " + meta : ""}
                  </span>
                );
                return s.url
                  ? <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="rounded-md border border-hairline bg-white/[0.03] px-2 py-0.5 text-[11px] text-muted transition-colors hover:border-emerald/40 hover:text-ink">{inner}</a>
                  : <span key={i} className="rounded-md border border-hairline bg-white/[0.03] px-2 py-0.5 text-[11px] text-muted">{inner}</span>;
              })}
            </div>
          )}

          {!minimal && limitations.length > 0 && (
            <div className="mt-2 text-[10px] leading-snug text-dim">Limitations: {limitations.join("; ")}</div>
          )}

          {followUps.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2 border-t border-hairline pt-4">
              {followUps.map((f) => (
                <button key={f} onClick={() => onFollow(f)} className="group inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white/[0.02] px-3 py-1.5 text-xs text-muted transition-colors hover:border-emerald/45 hover:text-ink">
                  {f}<span className="text-emerald opacity-0 transition-all duration-300 group-hover:translate-x-0.5 group-hover:opacity-100" aria-hidden>&rarr;</span>
                </button>
              ))}
            </div>
          )}

          {a.disclaimer && a.disclaimerLevel !== "none" && (
            <div className="mt-3 border-t border-hairline pt-3 text-[10px] leading-relaxed text-dim">{a.disclaimer}</div>
          )}
        </div>
      </GlassPanel>
    </motion.div>
  );
}

function Composer({ input, setInput, send, active, setActive, empty }: {
  input: string; setInput: (s: string) => void; send: (q: string) => void; active: string[]; setActive: Dispatch<SetStateAction<string[]>>; empty: boolean;
}) {
  const toggle = (c: string) => setActive((a) => (a.includes(c) ? a.filter((x) => x !== c) : [...a, c]));
  return (
    <div className={(empty ? "mt-10 sm:mt-14 " : "sticky bottom-0 mt-6 ") + "z-10 bg-gradient-to-t from-bg via-bg/95 to-transparent pt-4"} style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}>
      {!empty && (
        <div className="mb-2.5 flex flex-nowrap gap-1.5 overflow-x-auto pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {CHIPS.map((c) => (
            <button key={c} onClick={() => toggle(c)}
              className={"shrink-0 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] transition-all " + (active.includes(c) ? "border-emerald/50 bg-emerald/12 text-emerald shadow-[0_0_14px_-4px_rgba(52,211,153,0.6)]" : "border-hairline text-muted hover:border-border hover:text-ink")}>
              {c}
            </button>
          ))}
        </div>
      )}
      <div className="rounded-2xl bg-gradient-to-b from-emerald/25 via-white/[0.06] to-transparent p-px transition-all focus-within:from-emerald/50">
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2 rounded-2xl bg-panel/80 p-2 backdrop-blur-md">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} placeholder="Ask Maven about the Indian market&hellip;"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            className="max-h-36 flex-1 resize-none bg-transparent px-2.5 py-2 text-base leading-relaxed text-ink outline-none placeholder:text-dim sm:text-sm" />
          <motion.button type="submit" whileTap={{ scale: 0.92 }} aria-label="Ask Maven"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-emerald to-emerald-deep text-bg shadow-[0_8px_24px_-8px_rgba(52,211,153,0.8)] transition-opacity hover:opacity-90">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </motion.button>
        </form>
      </div>
      <div className="px-1 pb-1 pt-2 text-[10px] leading-relaxed text-dim">
        Maven gives educational market context for Indian markets - mechanisms, not investment advice.
      </div>
    </div>
  );
}