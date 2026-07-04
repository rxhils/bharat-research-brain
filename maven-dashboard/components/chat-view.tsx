"use client";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useReducedMotionSafe } from "./motion";
import { MavenChartRenderer, MechanismStepper } from "./maven-charts";
import { MavenEvidenceSummaryCard, MavenLatestDataChecklist } from "./maven-evidence";
import { MavenSourcePanel } from "./maven-source-panel";
import { MavenReportCard } from "./maven-report";
import type { MavenAskResponse } from "@/lib/maven-types";

const SUGGESTIONS = [
  { t: "Summarize today's Indian market", k: "Market wrap" },
  { t: "Why are banks leading today?", k: "Sector leadership" },
  { t: "What sectors benefit from softer crude?", k: "Macro knock-on" },
  { t: "Compare HDFC Bank and ICICI Bank", k: "Comparison" },
];
const MODELS = [
  { id: "maven-v1", name: "Maven V1", tag: "Beta", desc: "Fast India-market context", live: true },
  { id: "maven-pro", name: "Maven Pro", tag: "Deep Research", desc: "Deeper source pack and document extraction", live: false },
] as const;
const EASE = [0.22, 1, 0.36, 1] as const;
const FLOW = ["flow", "flow_chart"];

export type Msg = { id: number; role: "user" | "assistant"; text?: string; answer?: MavenAskResponse; loading?: boolean; looksLikeReport?: boolean };
// Client-only heuristic mirroring reportModeDetector.ts's trigger words - used ONLY to pick which
// loading copy to show optimistically while waiting; the server is the sole source of truth for
// whether a response actually is report mode.
const REPORT_HINT = /\b(full research report|full report|deep research|deep dive|deeply|in detail|full view|detailed analysis|investment thesis|business breakdown|risks? in detail|complete report|research note|institutional[- ]?style report)\b/i;

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

function Core({ size = 96 }: { size?: number }) {
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
      <motion.div className="absolute left-[10%] top-[8%] h-[24rem] w-[24rem] rounded-full bg-emerald/[0.11] blur-[120px] sm:h-[32rem] sm:w-[32rem]"
        animate={reduce ? undefined : { x: [0, 60, -20, 0], y: [0, 40, 80, 0], scale: [1, 1.15, 1] }} transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="absolute right-[2%] top-[20%] h-[22rem] w-[22rem] rounded-full bg-emerald-deep/[0.10] blur-[120px] sm:h-[28rem] sm:w-[28rem]"
        animate={reduce ? undefined : { x: [0, -50, 20, 0], y: [0, 60, -30, 0], scale: [1, 1.22, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "easeInOut", delay: 1 }} />
      <motion.div className="absolute bottom-[2%] left-[28%] h-[20rem] w-[20rem] rounded-full bg-gold/[0.06] blur-[120px] sm:h-[24rem] sm:w-[24rem]"
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

export function ChatView({ initialMessages, onMessagesChange }: { initialMessages?: Msg[]; onMessagesChange?: (msgs: Msg[]) => void } = {}) {
  const [msgs, setMsgs] = useState<Msg[]>(initialMessages ?? []);
  const [input, setInput] = useState("");
  const [model, setModel] = useState<string>(MODELS[0].id);
  const idRef = useRef(1);
  const lastUserId = useRef(0);
  const turnRef = useRef<HTMLDivElement>(null);

  // On a new question, bring the latest exchange to the top so the answer reads top-down.
  useEffect(() => { turnRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [msgs.length]);
  // Let the parent (ChatShell) persist this conversation as it grows.
  useEffect(() => { onMessagesChange?.(msgs); }, [msgs]); // eslint-disable-line react-hooks/exhaustive-deps

  async function send(q: string) {
    const text = q.trim();
    if (!text) return;
    setInput("");
    const uid = idRef.current++;
    const aid = idRef.current++;
    lastUserId.current = uid;
    setMsgs((m) => [...m, { id: uid, role: "user", text }, { id: aid, role: "assistant", loading: true, looksLikeReport: REPORT_HINT.test(text) }]);
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: text, model }) });
      const answer: MavenAskResponse = await r.json();
      setTimeout(() => setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, answer } : x))), 600);
    } catch {
      setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, loading: false, text: "Could not reach Maven." } : x)));
    }
  }

  const empty = msgs.length === 0;
  return (
    <div className={"relative mx-auto flex max-w-[960px] flex-col" + (empty ? "" : " min-h-[58vh]")}>
      <AuroraBg />
      {empty ? <Hero onPick={send} /> : (
        <div className="flex-1 space-y-7 pb-6">
          {msgs.map((m) => (m.role === "user" ? (
            <div key={m.id} ref={m.id === lastUserId.current ? turnRef : undefined} className="scroll-mt-24">
              <UserBubble text={m.text ?? ""} />
            </div>
          ) : (
            <motion.div key={m.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }} className="flex gap-3">
              <Avatar thinking={!!m.loading} />
              <div className="min-w-0 flex-1">
                {m.loading ? <ReasoningLoader reportMode={m.looksLikeReport} /> : m.answer ? <AnswerCard a={m.answer} onFollow={send} /> : <div className="pt-2 text-sm text-rose">{m.text}</div>}
              </div>
            </motion.div>
          )))}
          {/* reserve room so the latest question can scroll to the top of the view */}
          <div style={{ minHeight: "42vh" }} aria-hidden />
        </div>
      )}
      <Composer input={input} setInput={setInput} send={send} empty={empty} model={model} setModel={setModel} />
    </div>
  );
}

function Hero({ onPick }: { onPick: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  const up = { hide: reduce ? { opacity: 1 } : { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } } };
  return (
    <motion.div className="flex flex-col items-center justify-center py-6 text-center sm:py-10" initial="hide" animate="show"
      variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.1 } } }}>
      <motion.div variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, scale: 0.8 }, show: { opacity: 1, scale: 1, transition: { duration: 0.8, ease: EASE } } }}>
        <Core />
      </motion.div>
      <motion.h2 variants={up} className="mt-6 font-serif text-[2rem] leading-[1.1] text-ink sm:text-5xl">
        Understand the <span className="italic text-emerald">Indian market</span>.
      </motion.h2>
      <motion.p variants={up} className="mt-3 max-w-lg px-2 text-sm leading-relaxed text-ink/60">
        Ask about stocks, sectors, flows, RBI policy, crude, rupee, or macro &mdash; Maven explains the mechanism.
      </motion.p>
      <motion.div className="mt-9 grid w-full max-w-2xl grid-cols-1 gap-3.5 sm:grid-cols-2" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: 0.15 } } }}>
        {SUGGESTIONS.map((s) => <SuggestionCard key={s.t} s={s} onPick={onPick} />)}
      </motion.div>
    </motion.div>
  );
}

function SuggestionCard({ s, onPick }: { s: { t: string; k: string }; onPick: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  // Calm, editorial hover: border warms to emerald and the surface lightens - no tilt, no scale.
  return (
    <motion.button onClick={() => onPick(s.t)}
      variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } } }}
      className="group relative overflow-hidden rounded-2xl border border-hairline bg-panel/45 p-4 text-left backdrop-blur-md transition-colors duration-300 hover:border-emerald/35 hover:bg-panel/65 focus-visible:border-emerald/50 focus-visible:outline-none">
      <span className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-gradient-to-r from-emerald/0 via-emerald to-emerald/0 transition-transform duration-500 group-hover:scale-x-100" aria-hidden />
      <span className="pointer-events-none absolute -right-12 -top-12 h-28 w-28 rounded-full bg-emerald/0 blur-2xl transition-colors duration-500 group-hover:bg-emerald/10" aria-hidden />
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-dim">
        <span className="h-1 w-1 rounded-full bg-emerald/80" />{s.k}
      </div>
      <div className="mt-2 flex items-start justify-between gap-3">
        <span className="text-[0.95rem] leading-snug text-ink">{s.t}</span>
        <span className="mt-0.5 shrink-0 text-emerald opacity-0 transition-all duration-300 group-hover:translate-x-0.5 group-hover:opacity-100" aria-hidden>&rarr;</span>
      </div>
    </motion.button>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: EASE }} className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-md border border-emerald/25 bg-gradient-to-br from-emerald/20 to-emerald/[0.06] px-4 py-2.5 text-sm leading-relaxed text-ink shadow-[0_12px_36px_-20px_rgba(52,211,153,0.7)]">
        {text}
      </div>
    </motion.div>
  );
}

function ReasoningLoader({ reportMode }: { reportMode?: boolean } = {}) {
  const steps = reportMode
    ? ["Building company evidence pack", "Checking latest filings and sources", "Validating financial metrics", "Preparing Maven research report"]
    : ["Reading market context", "Checking sector drivers", "Building mechanism chain", "Preparing Maven view"];
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
  // Deep Research Report Mode renders as its own premium report card - normal chat-card flow
  // below is completely unaffected for every other answer type.
  if (a.reportMode) return <MavenReportCard a={a} onFollow={onFollow} />;
  const reduce = useReducedMotionSafe();
  const answerType = a.answerType ?? a.type ?? "market_mechanism";
  const minimal = answerType === "greeting" || answerType === "out_of_scope";
  const blocks = a.blocks ?? [];
  const keyData = a.keyData ?? [];
  const sources = a.sources ?? [];
  const limitations = a.limitations ?? [];
  const followUps = a.followUps ?? [];
  const allCharts = a.charts ?? [];
  const flowChart = allCharts.find((c) => FLOW.includes((c.type || "").toLowerCase()));
  const dataCharts = allCharts.filter((c) => !FLOW.includes((c.type || "").toLowerCase()));
  return (
    <motion.div initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: EASE }}>
      <GlassPanel tlSharp>
        <div className="relative overflow-hidden rounded-2xl rounded-tl-md p-5 sm:p-7">
          {!reduce && (
            <motion.span className="pointer-events-none absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" aria-hidden initial={{ x: "-130%" }} animate={{ x: "230%" }} transition={{ duration: 1.1, ease: EASE, delay: 0.15 }} />
          )}
          <span className="pointer-events-none absolute -right-24 -top-28 h-56 w-56 rounded-full bg-emerald/[0.08] blur-3xl" aria-hidden />
          <span className="pointer-events-none absolute left-0 top-6 bottom-6 w-px bg-gradient-to-b from-emerald/0 via-emerald/60 to-emerald/0" aria-hidden />

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.26em] text-dim">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_8px_rgba(52,211,153,0.9)]" />Maven
            </div>
            <span className="shrink-0 rounded-md bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wider text-dim">India markets</span>
          </div>

          <h3 className="mt-3 font-serif text-[1.6rem] leading-snug text-ink sm:text-[1.85rem]">{a.headline}</h3>
          {a.summary && <p className="mt-2.5 text-[0.95rem] leading-relaxed text-ink/75">{a.summary}</p>}

          {!!a.introSections?.length && (
            <motion.div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2" initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: 0.05 } } }}>
              {a.introSections.map((sec, i) => (
                <motion.div key={i} variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: EASE } } }}
                  className="rounded-xl border border-hairline bg-white/[0.02] p-4">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                    <span className="text-[0.85rem] font-medium text-ink">{sec.title}</span>
                  </div>
                  <p className="mt-1.5 pl-3.5 text-[0.85rem] leading-relaxed text-ink/65">{sec.body}</p>
                </motion.div>
              ))}
            </motion.div>
          )}

          {!minimal && keyData.length > 0 && (
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {keyData.map((d, i) => (
                <div key={i} className="rounded-xl border border-hairline bg-white/[0.02] p-3.5">
                  <div className="text-[10px] uppercase tracking-wider text-dim">{d.label}</div>
                  <div className="mt-1.5 tnum text-xl text-ink">{d.value}</div>
                  {d.change && <div className={"mt-0.5 tnum text-xs " + (d.change.trim().startsWith("-") ? "text-rose" : "text-emerald")}>{d.change}</div>}
                </div>
              ))}
            </div>
          )}

          {!minimal && dataCharts.length > 0 && <div className="mt-6"><MavenChartRenderer charts={dataCharts} /></div>}
          {!minimal && flowChart?.data && flowChart.data.length > 0 && <div className="mt-4"><MechanismStepper steps={flowChart.data as { label?: string; step?: number }[]} /></div>}
          {!minimal && <MavenEvidenceSummaryCard evidence={a.evidence} />}
          {!minimal && <MavenLatestDataChecklist items={a.latestDataChecklist} />}

          {blocks.length > 0 && (
            <motion.div className="mt-6 space-y-3" initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.1, delayChildren: 0.05 } } }}>
              {blocks.map((b, i) => {
                const g = blockGlyph(b.type);
                return (
                  <motion.div key={i} variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, y: 12, filter: "blur(6px)" }, show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.5, ease: EASE } } }} className="rounded-xl border border-hairline bg-white/[0.02] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={"h-1.5 w-1.5 shrink-0 rounded-full " + g.dot} />
                      <span className={"text-[10px] font-semibold uppercase tracking-[0.16em] " + g.label}>{b.type}</span>
                      <span className="text-[0.95rem] font-medium text-ink">{b.title}</span>
                    </div>
                    <p className="mt-2 pl-3.5 text-[0.9rem] leading-relaxed text-ink/70">{b.body}</p>
                  </motion.div>
                );
              })}
            </motion.div>
          )}

          {!minimal && <MavenSourcePanel sources={sources} />}

          {!minimal && limitations.length > 0 && (
            <div className="mt-2.5 text-[10px] leading-snug text-dim">Limitations: {limitations.join("; ")}</div>
          )}

          {followUps.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2 border-t border-hairline pt-5">
              {followUps.map((f) => (
                <button key={f} onClick={() => onFollow(f)} className="group inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white/[0.02] px-3.5 py-1.5 text-xs text-muted transition-colors hover:border-emerald/45 hover:text-ink">
                  {f}<span className="text-emerald opacity-0 transition-all duration-300 group-hover:translate-x-0.5 group-hover:opacity-100" aria-hidden>&rarr;</span>
                </button>
              ))}
            </div>
          )}

          {a.disclaimer && a.disclaimerLevel !== "none" && (
            <div className="mt-4 border-t border-hairline pt-4 text-[10px] leading-relaxed text-dim">{a.disclaimer}</div>
          )}
        </div>
      </GlassPanel>
    </motion.div>
  );
}

function ModelSelector({ model, setModel, direction = "up" }: { model: string; setModel: (id: string) => void; direction?: "up" | "down" }) {
  const reduce = useReducedMotionSafe();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = MODELS.find((m) => m.id === model) ?? MODELS[0];
  const down = direction === "down";
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={open}
        className="group inline-flex items-center gap-2 rounded-full border border-hairline bg-white/[0.03] py-1.5 pl-2 pr-3 text-xs text-ink transition-colors hover:border-emerald/40">
        <span className="grid h-5 w-5 place-items-center rounded-full border border-emerald/25 bg-panel"><MavenMark size={12} /></span>
        <span className="font-medium">{current.name}</span>
        <span className="hidden text-[10px] text-dim sm:inline">{current.tag}</span>
        <motion.svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="text-dim"
          animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25, ease: EASE }}><path d="M6 9l6 6 6-6" /></motion.svg>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div role="listbox"
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: down ? -6 : 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: down ? -6 : 6 }}
            transition={{ duration: 0.18, ease: EASE }}
            className={"absolute left-0 z-30 w-72 max-w-[calc(100vw-2rem)] rounded-2xl bg-gradient-to-b from-emerald/25 via-white/[0.06] to-transparent p-px shadow-[0_20px_60px_-20px_rgba(0,0,0,0.85)] " + (down
              // empty state: downward into blank space; on wide (>=1536px) screens open up-and-left into the roomy left margin, clear of the prompt cards and never below the fold
              ? "top-full mt-2 origin-top-left 2xl:left-auto 2xl:right-full 2xl:top-auto 2xl:bottom-0 2xl:mt-0 2xl:mr-2 2xl:w-64 2xl:origin-bottom-right"
              : "bottom-full mb-2 origin-bottom-left")}>
            <div className="rounded-2xl bg-panel/95 p-1.5 backdrop-blur-xl">
              <div className="px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-dim">Model</div>
              <motion.div initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.05 } } }}>
                {MODELS.map((m) => {
                  const selected = m.id === model;
                  return (
                    <motion.button key={m.id} type="button" role="option" aria-selected={selected} disabled={!m.live}
                      variants={{ hide: reduce ? { opacity: 1 } : { opacity: 0, x: -6 }, show: { opacity: 1, x: 0, transition: { duration: 0.3, ease: EASE } } }}
                      onClick={() => { if (m.live) { setModel(m.id); setOpen(false); } }}
                      className={"flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors " + (m.live ? "hover:bg-white/[0.05]" : "cursor-not-allowed opacity-60")}>
                      <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-emerald/25 bg-panel"><MavenMark size={15} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-ink">{m.name}</span>
                          <span className="rounded-full border border-hairline px-1.5 py-px text-[9px] uppercase tracking-wider text-dim">{m.tag}</span>
                          {!m.live && <span className="rounded-full bg-gold/15 px-1.5 py-px text-[9px] uppercase tracking-wider text-gold-soft">Soon</span>}
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-ink/55">{m.desc}</span>
                      </span>
                      {selected && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" className="mt-1 shrink-0" aria-hidden><path d="M20 6L9 17l-5-5" /></svg>}
                    </motion.button>
                  );
                })}
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Composer({ input, setInput, send, empty, model, setModel }: {
  input: string; setInput: (s: string) => void; send: (q: string) => void; empty: boolean; model: string; setModel: (id: string) => void;
}) {
  // Row is placed ABOVE the input on the conversation view (opens up over messages) and BELOW the
  // input on the empty state (opens down into the blank space, clear of the prompt cards).
  const selectorRow = (
    <div className="flex items-center justify-between px-1">
      <ModelSelector model={model} setModel={setModel} direction={empty ? "down" : "up"} />
      <span className="hidden items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] text-dim sm:inline-flex">
        <span className="h-1 w-1 rounded-full bg-emerald/80 shadow-[0_0_6px_rgba(52,211,153,0.75)]" aria-hidden />India markets
      </span>
    </div>
  );
  return (
    <div className={(empty ? "mt-8 sm:mt-10 " : "sticky bottom-0 mt-6 ") + "z-10 bg-gradient-to-t from-bg via-bg/95 to-transparent pt-4"} style={{ paddingBottom: "max(0.6rem, env(safe-area-inset-bottom))" }}>
      {!empty && <div className="mb-2.5">{selectorRow}</div>}
      <div className="rounded-2xl bg-gradient-to-b from-emerald/30 via-white/[0.06] to-transparent p-px transition-all duration-300 focus-within:from-emerald/60 focus-within:shadow-[0_0_34px_-10px_rgba(52,211,153,0.55)]">
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2 rounded-2xl bg-panel/80 p-2 backdrop-blur-md">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} placeholder="Ask Maven about Nifty, sectors, flows, macro, or Indian stocks&hellip;"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            className="max-h-36 flex-1 resize-none bg-transparent px-2.5 py-2 text-base leading-relaxed text-ink outline-none placeholder:text-dim sm:text-sm" />
          <motion.button type="submit" whileTap={input.trim() ? { scale: 0.92 } : undefined} aria-label="Ask Maven" disabled={!input.trim()}
            className={"grid h-9 w-9 shrink-0 place-items-center rounded-xl transition-all duration-200 " + (input.trim()
              ? "bg-gradient-to-br from-emerald to-emerald-deep text-bg shadow-[0_8px_24px_-8px_rgba(52,211,153,0.85)] hover:opacity-90"
              : "cursor-not-allowed bg-white/[0.06] text-dim")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </motion.button>
        </form>
      </div>
      {empty && <div className="mt-2.5">{selectorRow}</div>}
      <div className="px-1 pb-1 pt-2 text-[10px] leading-relaxed text-dim">
        Maven gives educational market context for Indian markets - mechanisms, not investment advice.
      </div>
    </div>
  );
}