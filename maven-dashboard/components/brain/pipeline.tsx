"use client";

// /brain — the agent roster redesigned as a pipeline diagram (wave-4 audit).
// The 5 LIVE agents render as connected stages (Price Ingest → Daily Mark →
// Exposure/Regime → Quarterly Rebalance → F+ Scorer) with a hairline connector
// rail, numbered mono stage labels and mono cadence chips. The 6 OFFLINE
// research agents sit in a visually recessed band below (on mobile, collapsed
// into one disclosure row). Signature moment: ONE tracer pulse travels the
// connector on scroll-into-view, lighting each stage dot in sequence and
// terminating at the gold F+ Scorer node — a single pass, JS motion-value
// driven (.brand-motion) so it plays under OS reduced-motion; no infinite loop.
//
// Honesty rules kept from the original explainer: live status only overlays
// real agent_run_log rows from /api/agents; until a nightly run records
// heartbeats the documented design is shown, and the footnote says so. The
// polling is gated — one fetch on mount, and it only keeps polling while the
// board actually reports an in-progress run.
//
// Agent copy is verbatim from the original roster (components/agents.tsx) —
// real facts only, nothing invented.

import { AnimatePresence, animate, motion, useInView, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { AgentBoard, AgentRun } from "@/lib/types";
import { EASE, SectionEyebrow, useReducedMotionSafe } from "@/components/motion";
import { GlassPanel } from "@/components/glass-panel";

type Doc = {
  name: string;
  one: string; // one-line summary
  long: string; // plain-English explanation
  cadence?: string; // when it runs (live agents)
  offlineReason?: string; // why it is offline
  // Real backend agent_run_log.agent_name this stage maps to (the presentation
  // names above do NOT equal the backend ids). Only set where the mapping is
  // certain from the backend agents' ClassVar `name` — a wrong id would light
  // the wrong stage, so unmapped stages simply show their documented cadence.
  // Backend ids: prices, universe, ranking, risk, sector, macro, fundamentals,
  // earnings, fii_dii, delivery, outcome, promoter, meta_auditor, report.
  agentId?: string;
};

const LIVE: Doc[] = [
  {
    name: "Price Ingest",
    agentId: "prices",
    one: "Grabs the official closing price of every stock.",
    long: "After the market closes, this pulls the end-of-day price for all ~500 stocks. "
      + "Every other number — your portfolio value, the stops, the rankings — is built on "
      + "these prices. Free permitted source (yfinance EOD); no live broker feed required.",
    cadence: "Daily, after close",
  },
  {
    name: "Daily Mark",
    agentId: "risk",
    one: "Re-prices your holdings and applies the safety stop.",
    long: "Re-values your open positions at today's close, updates the equity curve and "
      + "drawdown, and automatically sells any holding that has fallen 15% below your entry "
      + "(cut-on-breakdown). This is the daily risk check.",
    cadence: "Daily",
  },
  {
    name: "Exposure / Regime",
    one: "Decides how much to keep in cash vs stocks.",
    long: "Checks whether the whole market (Nifty 500) is above or below its 200-day "
      + "average. Healthy → fully invested (100%). Weakening → 50%. Dangerous → 25%, the rest "
      + "in cash. This is what cut the drawdown through the COVID crash in the backtest.",
    cadence: "Weekly",
  },
  {
    name: "Quarterly Rebalance",
    one: "Rebuilds the 25-stock book every quarter.",
    long: "Every ~63 trading days it re-ranks the whole universe with the Enhanced F+ score, sells "
      + "names that dropped out, buys new leaders, and keeps existing winners (hold buffer). "
      + "Redeploys cash at the current exposure level.",
    cadence: "Quarterly",
  },
  {
    name: "Enhanced F+ Composite Scorer",
    agentId: "ranking",
    one: "The actual brain that picks the stocks.",
    long: "Scores every stock on vol-adjusted momentum + quality + low-volatility (the Enhanced F+ "
      + "composite), capped at 4 per sector, and the top 25 become the book. This is the "
      + "exact logic that passed every backtest (commit 6ced078) — nothing else picks names.",
    cadence: "At each rebalance",
  },
];

const OFFLINE: Doc[] = [
  {
    name: "News",
    one: "Scans market news headlines per stock.",
    long: "Would read recent headlines for each holding and tag relevance. The NewsAPI key "
      + "is set, but the client is not yet wired into the live pipeline.",
    offlineReason: "NewsAPI client not wired",
  },
  {
    name: "Sentiment (FinBERT)",
    one: "Rates news positive / negative with a finance AI.",
    long: "Would run headlines through FinBERT (a finance language model) to score tone. "
      + "Needs the model + a GPU machine running; not provisioned on the cloud yet.",
    offlineReason: "FinBERT / GPU not running",
  },
  {
    name: "Fundamentals",
    agentId: "fundamentals",
    one: "Reads revenue, profit and debt from financials.",
    long: "Would pull quarterly financials and trend them. The FMP key is valid, but the "
      + "client is not wired into the live decision.",
    offlineReason: "FMP client pending",
  },
  {
    name: "FII / DII Flows",
    agentId: "fii_dii",
    one: "Tracks big foreign / domestic fund buying & selling.",
    long: "Would read end-of-day institutional flow data. Requires operator-downloaded "
      + "exchange CSVs (we never scrape the NSE site).",
    offlineReason: "needs operator CSV uploads",
  },
  {
    name: "Macro",
    agentId: "macro",
    one: "Watches USD/INR, crude, India VIX and rates.",
    long: "Tracks the big-picture backdrop. Some data exists, but macro is not part of the "
      + "live Enhanced F+ signal — only the market-regime check (in Exposure) is.",
    offlineReason: "not in the live signal",
  },
  {
    name: "Meta-Auditor",
    agentId: "meta_auditor",
    one: "Checks every claim has a real source.",
    long: "Would reject any agent claim with no evidence or stale data. Only runs when the "
      + "AI research agents above are online.",
    offlineReason: "runs only with the AI agents",
  },
];

/** Roster counts, consumed by the hero stat strip so the figures can never
 *  drift from the actual roster. */
export const LIVE_COUNT = LIVE.length;
export const OFFLINE_COUNT = OFFLINE.length;

const SCORER_INDEX = LIVE.length - 1; // the Enhanced F+ Composite Scorer node

// Composed press: these buttons fade border+bg on hover, so plain PRESS (which
// sets transition-property:transform) would kill the color fade — keep both.
const CARD_PRESS =
  "motion-safe:transition-[color,background-color,border-color,transform,box-shadow] motion-safe:duration-150 motion-safe:active:scale-[0.99]";

/** Rotating-chevron affordance (replaces the old 10px "click to explain"). */
function Chevron({ open, className = "" }: { open: boolean; className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={`h-3.5 w-3.5 shrink-0 text-dim transition-transform duration-200 ${open ? "rotate-180" : ""} ${className}`}
    >
      <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Real-run status badge — rendered ONLY when a live agent_run_log row
 *  overrides the documented status (the dot + section header carry the rest). */
function RunBadge({ run }: { run: AgentRun }) {
  const cls =
    run.status === "running" ? "bg-amber/15 text-amber"
    : run.status === "error" ? "bg-rose/15 text-rose"
    : run.status === "done" ? "bg-emerald/15 text-emerald"
    : "bg-white/5 text-dim";
  return (
    <span className={`rounded-md px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide ${cls}`}>
      {run.status}
    </span>
  );
}

/** Stage status dot. Static glow, no infinite pulse (house discipline). Before
 *  the tracer reaches a stage the dot is unlit; a real run row overrides. */
function StageDot({ lit, gold, run }: { lit: boolean; gold?: boolean; run?: AgentRun }) {
  let cls = lit
    ? gold
      ? "bg-gold shadow-[0_0_8px_rgba(201,169,97,0.7)]"
      : "bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.55)]"
    : "bg-white/15";
  if (run) {
    if (run.status === "running") cls = "bg-amber shadow-[0_0_6px_rgba(251,191,36,0.55)]";
    else if (run.status === "done") cls = "bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.55)]";
    else if (run.status === "error") cls = "bg-rose shadow-[0_0_6px_rgba(251,113,133,0.45)]";
    else if (run.status === "offline") cls = "bg-dim";
  }
  return (
    <span
      aria-hidden
      className={`brand-motion h-2 w-2 shrink-0 rounded-full transition-[background-color,box-shadow] duration-300 ${cls}`}
    />
  );
}

/** One live pipeline stage — numbered mono label, dot, cadence chip, and a
 *  chevron-affordance expander with a slight y-settle on the reveal. */
function StageCard({ doc, i, run, lit, done }: {
  doc: Doc; i: number; run?: AgentRun; lit: boolean; done: boolean;
}) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotionSafe();
  const scorer = i === SCORER_INDEX;
  const shell = scorer
    ? `border-gold/25 bg-gold/[0.04] hover:border-gold/40 ${done ? "shadow-[0_0_30px_-12px_rgba(201,169,97,0.5)]" : ""}`
    : "border-hairline bg-bg/40 hover:border-white/10 hover:bg-panel/60";
  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      aria-expanded={open}
      className={`h-full w-full rounded-xl border p-3 text-left ${shell} ${CARD_PRESS}`}
    >
      <div className="flex items-start gap-2">
        <span className="tnum pt-px font-mono text-[10px] font-semibold text-dim">
          0{i + 1}
        </span>
        <span className="pt-[5px]"><StageDot lit={lit} gold={scorer} run={run} /></span>
        <span className={`min-w-0 flex-1 text-sm font-medium leading-snug ${scorer ? "text-gold-soft" : "text-ink"}`}>
          {doc.name}
        </span>
        {run && <RunBadge run={run} />}
        <span className="pt-0.5"><Chevron open={open} /></span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">{doc.one}</p>
      {doc.cadence && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span
            className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] ${
              scorer ? "border-gold/20 bg-gold/[0.06] text-gold-soft/90" : "border-emerald/15 bg-emerald/5 text-emerald/80"
            }`}
          >
            {doc.cadence}
          </span>
        </div>
      )}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="detail"
            initial={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            animate={reduce ? { opacity: 1 } : { height: "auto", opacity: 1 }}
            exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: EASE }}
            className="overflow-hidden"
          >
            {/* y-settle so the reveal feels authored, not just height:auto */}
            <motion.div
              initial={reduce ? false : { y: 6 }}
              animate={{ y: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="mt-2 border-t border-hairline pt-2"
            >
              <p className="text-xs leading-relaxed text-muted">{doc.long}</p>
              {run?.headlineOutput && (
                <p className="mt-1.5 font-mono text-[11px] text-emerald">{run.headlineOutput}</p>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </button>
  );
}

/** Recessed research-layer card — smaller, desaturated, clearly subordinate. */
function OfflineCard({ doc, run }: { doc: Doc; run?: AgentRun }) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotionSafe();
  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      aria-expanded={open}
      className={`w-full rounded-lg border border-hairline bg-bg/25 p-2.5 text-left opacity-85 hover:border-white/10 hover:opacity-100 ${CARD_PRESS}`}
    >
      <div className="flex items-start gap-2">
        <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-white/20" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-medium text-muted">{doc.name}</span>
            <span className="flex items-center gap-1.5">
              {run && run.status !== "offline" && <RunBadge run={run} />}
              <Chevron open={open} />
            </span>
          </div>
          <p className="mt-0.5 text-[11px] leading-relaxed text-dim">{doc.one}</p>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                key="detail"
                initial={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
                animate={reduce ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
                transition={{ duration: 0.26, ease: EASE }}
                className="overflow-hidden"
              >
                <motion.div
                  initial={reduce ? false : { y: 5 }}
                  animate={{ y: 0 }}
                  transition={{ duration: 0.28, ease: EASE }}
                  className="mt-2 border-t border-hairline pt-2"
                >
                  <p className="text-[11px] leading-relaxed text-dim">{doc.long}</p>
                  {doc.offlineReason && (
                    <p className="mt-1.5 font-mono text-[10px] text-dim">offline: {doc.offlineReason}</p>
                  )}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </button>
  );
}

export function AgentPipeline() {
  const [board, setBoard] = useState<AgentBoard | null>(null);
  const [showOffline, setShowOffline] = useState(false);

  // Gated polling: one fetch on mount; keep polling every 8s ONLY while the
  // board reports an in-progress run (no more hammering the endpoint forever
  // just to render "no heartbeats yet").
  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    const load = async () => {
      try {
        const r = await fetch("/api/agents", { cache: "no-store" });
        if (!alive || !r.ok) return;
        const b: AgentBoard = await r.json();
        setBoard(b);
        const running = b.inProgress || b.agents.some((a) => a.status === "running");
        if (running) timer = window.setTimeout(load, 8000);
      } catch {
        /* board stays null — documented statuses are shown */
      }
    };
    load();
    return () => {
      alive = false;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);

  const byName = new Map<string, AgentRun>();
  for (const a of board?.agents ?? []) byName.set(a.agentName.toLowerCase(), a);
  // key on the real backend agent id where a stage declares one; the display
  // names never match agent_run_log.agent_name, so a name-only lookup found
  // nothing and no live badge ever lit.
  const runFor = (d: Doc) => byName.get((d.agentId ?? d.name).toLowerCase());
  const liveRecorded = (board?.agents ?? []).some((a) => a.status === "running" || a.status === "done");

  // --- Signature moment: one tracer pulse along the pipeline -----------------
  // SSR + no-JS render the terminal state (all stages lit, rail filled) so the
  // page never shows a dead pipeline; on first scroll-into-view the pulse
  // snaps to the start and plays ONE pass. Motion-value driven → plays under
  // OS reduced-motion (.brand-motion), and there is no loop.
  const rootRef = useRef<HTMLDivElement>(null);
  const inView = useInView(rootRef, { once: true, margin: "-15% 0px" });
  const progress = useMotionValue(1);
  const [lit, setLit] = useState(LIVE.length);
  const [done, setDone] = useState(true);
  const litRef = useRef(LIVE.length);

  useEffect(() => {
    if (!inView) return;
    progress.set(0);
    litRef.current = 0;
    setLit(0);
    setDone(false);
    const c = animate(progress, 1, {
      duration: 2.2,
      delay: 0.25,
      ease: EASE,
      onUpdate: (v) => {
        // stage i ignites exactly as the tracer head crosses its rail dot
        const n = v >= 1 ? LIVE.length : Math.min(LIVE.length, Math.floor(v * (LIVE.length - 1)) + 1);
        if (n !== litRef.current) {
          litRef.current = n;
          setLit(n);
        }
      },
      onComplete: () => {
        litRef.current = LIVE.length;
        setLit(LIVE.length);
        setDone(true);
      },
    });
    return () => c.stop();
  }, [inView, progress]);

  // Rail geometry: dots sit at the 5 column centers → 10%..90% of the rail.
  const headLeft = useTransform(progress, (v) => `${10 + v * 80}%`);
  const fillWidth = useTransform(progress, (v) => `${v * 80}%`);
  const headOpacity = useTransform(progress, [0, 0.04, 0.96, 1], [0, 1, 1, 0]);

  return (
    <GlassPanel as="section" noise innerClassName="p-4 sm:p-6">
      <div ref={rootRef}>
        <SectionEyebrow number="01">Live pipeline</SectionEyebrow>
        <div className="mt-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2 className="font-serif text-xl text-ink">
            Five stages decide the paper book.
          </h2>
          <p className="text-xs text-dim">Tap any agent for a plain-English explanation.</p>
        </div>

        {/* connector rail — desktop only; the tracer pulse travels it once */}
        <div className="relative mt-5 hidden h-4 lg:block" aria-hidden>
          <div className="absolute left-[10%] right-[10%] top-1/2 h-px -translate-y-1/2 bg-white/10" />
          <motion.div
            className="brand-motion absolute left-[10%] top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-emerald/10 via-emerald/50 to-emerald/80"
            style={{ width: fillWidth }}
          />
          <motion.div
            className="brand-motion absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald shadow-[0_0_10px_rgba(52,211,153,0.9)]"
            style={{ left: headLeft, opacity: headOpacity }}
          />
          {LIVE.map((d, i) => (
            <span
              key={d.name}
              className={`brand-motion absolute top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full transition-[background-color,box-shadow] duration-300 ${
                lit > i
                  ? i === SCORER_INDEX
                    ? "bg-gold shadow-[0_0_8px_rgba(201,169,97,0.8)]"
                    : "bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.6)]"
                  : "bg-white/15"
              }`}
              style={{ left: `${i * 20 + 10}%` }}
            />
          ))}
        </div>

        {/* the five stages — connected grid on desktop, vertical pipeline with
            visible connector segments on mobile (same pulse, same order) */}
        <ol className="mt-2 lg:grid lg:grid-cols-5 lg:gap-3">
          {LIVE.map((d, i) => (
            <li key={d.name} className="lg:h-full">
              {i > 0 && (
                <div
                  aria-hidden
                  className={`brand-motion mx-auto h-4 w-px transition-colors duration-300 lg:hidden ${
                    lit > i ? "bg-emerald/50" : "bg-white/10"
                  }`}
                />
              )}
              <StageCard doc={d} i={i} run={runFor(d)} lit={lit > i} done={done && i === SCORER_INDEX} />
            </li>
          ))}
        </ol>

        {/* research layer — recessed band; on mobile a single disclosure row */}
        <div className="mt-6 border-t border-hairline pt-4">
          <button
            type="button"
            onClick={() => setShowOffline((v) => !v)}
            aria-expanded={showOffline}
            className="flex w-full items-center justify-between gap-3 text-left sm:pointer-events-none"
          >
            <div>
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-dim">
                Research layer — offline
              </div>
              <p className="mt-0.5 text-[11px] text-dim">
                {OFFLINE_COUNT} research agents — built, not part of the live signal.
              </p>
            </div>
            <Chevron open={showOffline} className="sm:hidden" />
          </button>
          <div
            className={`${showOffline ? "mt-3 grid" : "hidden"} gap-2 sm:mt-3 sm:grid sm:grid-cols-2 lg:grid-cols-3`}
          >
            {OFFLINE.map((d) => (
              <OfflineCard key={d.name} doc={d} run={runFor(d)} />
            ))}
          </div>
        </div>

        {/* system-status footnote — mono, honest */}
        <p className="mt-4 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.08em] text-dim">
          <span
            aria-hidden
            className={`h-1.5 w-1.5 shrink-0 rounded-full ${liveRecorded ? "bg-emerald" : "bg-white/20"}`}
          />
          {liveRecorded
            ? `live run ${board?.runId} — status from agent_run_log`
            : "no nightly run has recorded heartbeats yet — statuses shown are the documented design"}
        </p>
      </div>
    </GlassPanel>
  );
}
