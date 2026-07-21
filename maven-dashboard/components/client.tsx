"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartReveal, EASE, PRESS, useReducedMotionSafe } from "./motion";
import type {
  ABReadout, AgentBoard as TBoard, AgentRun, EquityPoint, ExposureState,
  Holding, ScoreRow,
} from "@/lib/types";
import { ago, fmtDate, inrCompact, pct, plain, signClass } from "@/lib/format";

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------
// Brand mark. Uses /public/logo.png when present; falls back to an inline
// SVG of the Maven mark (white peaks + emerald check + dot) until the file
// is dropped in. Rendered on a dark rounded tile to match the supplied logo.
// The Maven mark, baked in as inline SVG (a faithful recreation of the supplied
// logo: dark squircle, white mountain "M", emerald check "V", emerald dot).
// Vector → always crisp, no asset file or network request needed.
function Logo({ size = 30 }: { size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-[30%]"
      style={{ width: size, height: size, background: "#0d0e11" }}
    >
      <svg width={size} height={size} viewBox="0 0 100 100" fill="none" role="img" aria-label="Maven">
        <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="89" cy="17" r="8" fill="#34d399" />
      </svg>
    </span>
  );
}

// Footer-style press composition (see app/layout.tsx): keeps the color fade
// alongside the press scale — plain PRESS would override transition-colors.
const NAV_PRESS =
  "motion-safe:transition-[color,background-color,border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97]";

export function Nav() {
  const path = usePathname();
  const reduce = useReducedMotionSafe();
  // Elevation on scroll: the bar starts translucent and gains body + shadow
  // once the page moves, so it reads as a floating instrument panel.
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const tab = (href: string, label: string, dot = false) => {
    const active = path === href;
    return (
      <Link
        href={href}
        className={`relative flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-2 py-1 text-[11px] transition-colors ${NAV_PRESS} sm:px-3.5 sm:py-1.5 sm:text-sm ${
          active ? "text-emerald" : "text-muted hover:text-ink"
        }`}
      >
        {/* the active pill GLIDES between tabs (shared layoutId) */}
        {active && (
          <motion.span
            layoutId="nav-active-pill"
            className="absolute inset-0 rounded-lg bg-emerald/10 ring-1 ring-inset ring-emerald/20"
            transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 34 }}
            aria-hidden
          />
        )}
        {dot && <span className="relative z-10 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.8)]" aria-hidden />}
        <span className="relative z-10">{label}</span>
      </Link>
    );
  };

  return (
    /* pt clears the iPhone notch / Dynamic Island (safe-area var from globals.css) */
    <nav
      className={`sticky top-0 z-30 -mx-5 mb-2 flex items-center justify-between gap-2 px-5 pb-4 pt-[calc(1rem+var(--sat))] backdrop-blur-xl transition-[background-color,box-shadow] duration-300 sm:-mx-8 sm:px-8 ${
        scrolled ? "bg-bg/95 shadow-[0_20px_44px_-26px_rgba(0,0,0,0.95)]" : "bg-bg/70"
      }`}
    >
      {/* gradient hairline — emerald breathes through the bar's bottom edge */}
      <span aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(52,211,153,0.35) 25%, rgba(52,211,153,0.35) 75%, transparent)" }} />
      <span aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/[0.04]" />

      <Link href="/" className={`group relative flex shrink-0 items-center gap-2.5 ${PRESS}`}>
        <span className="relative">
          <span aria-hidden className="absolute -inset-1.5 rounded-xl bg-emerald/25 opacity-0 blur-md transition-opacity duration-300 group-hover:opacity-100" />
          <span className="relative"><Logo size={28} /></span>
        </span>
        <span className="hidden text-sm tracking-[0.2em] text-muted transition-colors duration-300 group-hover:text-ink sm:inline">MAVEN</span>
      </Link>

      <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
        <div className="scroll-touch flex min-w-0 items-center gap-0.5 overflow-x-auto rounded-xl border border-hairline bg-panel/50 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] [scrollbar-width:none] sm:gap-1 [&::-webkit-scrollbar]:hidden">
          {tab("/chat", "Chat", true)}
          {tab("/", "How it works")}
          {tab("/portfolio-mode", "Modes")}
          {tab("/portfolio", "Portfolio")}
          {tab("/broker", "Broker")}
          {tab("/trades", "Trades")}
          {tab("/strategies", "Strategies")}
        </div>
        <Link
          href="/backtest"
          className={`group relative shrink-0 overflow-hidden whitespace-nowrap rounded-lg border px-2.5 py-1 text-[11px] transition-[color,border-color,box-shadow] ${NAV_PRESS} sm:px-3.5 sm:py-1.5 sm:text-sm ${
            path === "/backtest"
              ? "border-emerald/50 bg-emerald/15 text-emerald"
              : "border-emerald/30 text-emerald hover:border-emerald/50 hover:bg-emerald/10 hover:shadow-[0_0_20px_-6px_rgba(52,211,153,0.5)]"
          }`}
        >
          {/* light sweep across the CTA on hover */}
          <span aria-hidden className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/3 -skew-x-12 bg-white/10 transition-transform duration-500 ease-out group-hover:translate-x-[420%]" />
          <span className="relative"><span className="text-gold-soft">★</span> Backtest</span>
        </Link>
      </div>
    </nav>
  );
}

export function Card({
  title, sub, children, className = "", delay = 0,
}: {
  title?: string; sub?: string; children: React.ReactNode; className?: string; delay?: number;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.section
      className={`rounded-xl2 border border-border bg-panel/60 p-5 transition-[border-color,box-shadow,transform] duration-300 hover:border-emerald/25 hover:shadow-[0_18px_50px_-28px_rgba(52,211,153,0.45)] motion-safe:hover:-translate-y-0.5 ${className}`}
      initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-6% 0px" }}
      transition={{ duration: 0.55, delay: delay / 1000, ease: EASE }}
    >
      {title && (
        <div className="mb-4 flex items-baseline justify-between gap-3">
          <h3 className="text-[13px] font-medium tracking-wide text-ink">{title}</h3>
          {sub && <span className="text-xs text-dim">{sub}</span>}
        </div>
      )}
      {children}
    </motion.section>
  );
}

export function Pill({ signal }: { signal: ScoreRow["signal"] }) {
  const map = {
    bullish: "bg-emerald/12 text-emerald",
    neutral: "bg-white/8 text-muted",
    avoid: "bg-rose/12 text-rose",
  } as const;
  const label = { bullish: "Bullish", neutral: "Neutral", avoid: "Avoid" }[signal];
  return <span className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${map[signal]}`}>{label}</span>;
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------
function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-panel2 px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 text-dim">{fmtDate(label)}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-muted">{p.name}</span>
          <span className="ml-auto font-mono tnum text-ink">{inrCompact(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

// Recharts replays its draw animation on every data change. Allow one pass on
// mount (600ms), then hard-disable so refreshes/re-renders never redraw lines.
// Reduced motion skips the draw entirely.
function useChartDrawOnce() {
  const reduce = useReducedMotionSafe();
  const [firstPass, setFirstPass] = useState(true);
  useEffect(() => {
    const id = window.setTimeout(() => setFirstPass(false), 800); // outlives the 600ms draw
    return () => window.clearTimeout(id);
  }, []);
  return firstPass && !reduce;
}

export function EquityChart({ data, seriesName = "Enhanced F+", accent = "#34d399" }: { data: EquityPoint[]; seriesName?: string; accent?: string }) {
  const draw = useChartDrawOnce();
  return (
    <ChartReveal delay={0.1}>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(d) => fmtDate(d).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(v) => inrCompact(v)} width={56} axisLine={false} tickLine={false} domain={["dataMin", "dataMax"]} />
          <Tooltip content={<ChartTip />} />
          <Line type="monotone" dataKey="nifty500" name="Nifty 500 TRI" stroke="#5a616a" strokeWidth={1.5} dot={false} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
          <Line type="monotone" dataKey="fplus" name={seriesName} stroke={accent} strokeWidth={2} dot={false} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
        </LineChart>
      </ResponsiveContainer>
    </ChartReveal>
  );
}

export function ABChart({ data, readout }: { data: EquityPoint[]; readout: ABReadout }) {
  const draw = useChartDrawOnce(); // one draw on mount, never on data refresh
  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-sm">
        {readout.hasAgentic ? (
          <span className={signClass(readout.edgePct ?? 0)}>
            Agents adding {pct(readout.edgePct ?? 0)} edge so far
          </span>
        ) : (
          <span className="text-muted">No agentic edge yet — agents not live</span>
        )}
      </div>
      <ChartReveal delay={0.1}>
        <ResponsiveContainer width="100%" height={210}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(d) => fmtDate(d).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(v) => inrCompact(v)} width={56} axisLine={false} tickLine={false} domain={["dataMin", "dataMax"]} />
            <Tooltip content={<ChartTip />} />
            <Line type="monotone" dataKey="fplus" name="Enhanced F+" stroke="#34d399" strokeWidth={2} dot={false} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
            {readout.hasAgentic && (
              <Line type="monotone" dataKey="fplusAgentic" name="F+ · agentic" stroke="#fbbf24" strokeWidth={2} dot={false} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </ChartReveal>
      <p className="mt-3 text-xs leading-relaxed text-dim">{readout.note}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exposure gauge
// ---------------------------------------------------------------------------
export function ExposureGauge({ state }: { state: ExposureState }) {
  const invested = 100 - state.cashPct;
  const riskOff = state.regime === "risk_off";
  const reduce = useReducedMotionSafe();
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-2xl tnum text-emerald">{plain(invested, 1)}%</span>
        <span className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${riskOff ? "bg-amber/12 text-amber" : "bg-emerald/12 text-emerald"}`}>
          {riskOff ? "Risk-off" : "Risk-on"}
        </span>
      </div>
      {/* Invested sleeve fills from 0 once on view — a single purposeful gauge
          entrance (not a nested fade); origin-aware, GPU-cheap via width tween. */}
      <div className="flex h-3 overflow-hidden rounded-full bg-white/5">
        <motion.div
          className="bg-emerald"
          initial={reduce ? false : { width: 0 }}
          whileInView={{ width: `${invested}%` }}
          viewport={{ once: true, margin: "-8% 0px" }}
          transition={{ duration: 0.7, ease: EASE }}
          style={{ width: `${invested}%` }}
        />
        <div className="bg-white/10" style={{ width: `${state.cashPct}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-muted">
        <span>Invested {plain(invested, 1)}%</span>
        <span>Cash {plain(state.cashPct, 1)}%</span>
      </div>
      <div className="mt-4 flex gap-1.5">
        {[100, 50, 25].map((lvl) => (
          <span key={lvl} className={`flex-1 rounded-md py-1 text-center text-[11px] ${state.level * 100 === lvl ? "bg-emerald/15 text-emerald" : "bg-white/4 text-dim"}`}>
            {lvl}%
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs text-dim">Graded cash exposure set by the market regime. Below 200-DMA, de-risk.</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Holdings table (sortable)
// ---------------------------------------------------------------------------
type SortKey = "weightPct" | "pnlPct" | "ticker";
export function HoldingsTable({ rows }: { rows: Holding[] }) {
  const [key, setKey] = useState<SortKey>("weightPct");
  const [dir, setDir] = useState<1 | -1>(-1);
  const sorted = useMemo(() => {
    const stocks = rows.filter((r) => !r.isCash);
    const cash = rows.filter((r) => r.isCash);
    stocks.sort((a, b) => {
      const av = a[key]; const bv = b[key];
      if (typeof av === "string") return (av as string).localeCompare(bv as string) * dir;
      return ((av as number) - (bv as number)) * dir;
    });
    return [...stocks, ...cash];
  }, [rows, key, dir]);
  // Sort direction shown as a caret that only renders on the active column —
  // keeps inactive headers quiet (Emil: no ambient affordance noise).
  // Real <button> inside the th → keyboard-sortable (Enter/Space) with a visible
  // focus ring; aria-sort stays on the columnheader where AT expects it.
  const head = (k: SortKey, label: string, extra = "") => {
    const on = key === k;
    return (
      <th
        aria-sort={on ? (dir === 1 ? "ascending" : "descending") : "none"}
        className={`py-2 text-xs font-medium ${extra}`}
      >
        <button
          type="button"
          className={`select-none rounded font-medium motion-safe:transition-[color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 ${on ? "text-muted" : "text-dim hover:text-muted"}`}
          onClick={() => { if (key === k) { setDir((d) => (d === 1 ? -1 : 1)); } else { setKey(k); setDir(-1); } }}
        >
          {label}
          <span className={`ml-1 inline-block font-mono transition-opacity ${on ? "opacity-100" : "opacity-0"}`} aria-hidden>
            {dir === 1 ? "↑" : "↓"}
          </span>
        </button>
      </th>
    );
  };
  return (
    <div className="scroll-touch overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr className="border-b border-hairline text-left">
            {head("ticker", "Ticker")}
            <th className="py-2 text-xs font-medium text-dim">Name</th>
            <th className="py-2 text-xs font-medium text-dim">Sector</th>
            {head("weightPct", "Weight", "text-right")}
            <th className="py-2 text-right text-xs font-medium text-dim">Entry</th>
            <th className="py-2 text-right text-xs font-medium text-dim">Current</th>
            {head("pnlPct", "P&L", "text-right")}
          </tr>
        </thead>
        {/* tnum = tabular figures so columns of prices/percentages stay aligned */}
        <tbody className="tnum">
          {sorted.map((r) => (
            <tr
              key={r.isin}
              className={`border-b border-hairline/60 transition-colors hover:bg-white/[.02] ${r.isCash ? "text-muted" : "text-ink"}`}
            >
              <td className="py-2.5 font-mono text-sm">{r.ticker}</td>
              <td className="py-2.5 text-sm text-muted">{r.name}</td>
              <td className="py-2.5 text-xs text-dim">{r.sector}</td>
              <td className="py-2.5 text-right font-mono text-sm">{plain(r.weightPct, 1)}%</td>
              <td className="py-2.5 text-right font-mono text-sm text-muted">{r.isCash ? "-" : plain(r.entryPrice)}</td>
              <td className="py-2.5 text-right font-mono text-sm text-muted">{r.isCash ? "-" : plain(r.currentPrice)}</td>
              <td className={`py-2.5 text-right font-mono text-sm ${r.isCash ? "text-dim" : signClass(r.pnlPct)}`}>{r.isCash ? "-" : pct(r.pnlPct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score breakdown (selector + bars)
// ---------------------------------------------------------------------------
function Bar({ label, value }: { label: string; value: number | null }) {
  const off = value === null;
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 text-xs text-muted">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
        {!off && <div className="h-full bg-emerald/70" style={{ width: `${value}%` }} />}
      </div>
      <span className={`w-12 shrink-0 text-right font-mono text-xs tnum ${off ? "text-dim" : "text-ink"}`}>
        {off ? "pending" : value}
      </span>
    </div>
  );
}
export function ScoreBreakdown({ rows }: { rows: ScoreRow[] }) {
  const [isin, setIsin] = useState(rows[0]?.isin);
  const s = rows.find((r) => r.isin === isin) ?? rows[0];
  if (!s) return <Empty />;
  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <select
          value={isin}
          onChange={(e) => setIsin(e.target.value)}
          aria-label="Choose stock for score breakdown"
          className="rounded-lg border border-border bg-panel2 px-3 py-1.5 text-sm text-ink outline-none transition-colors focus:border-emerald/40 focus-visible:ring-1 focus-visible:ring-emerald/60"
        >
          {rows.map((r) => <option key={r.isin} value={r.isin}>{r.ticker} — {r.name}</option>)}
        </select>
        <div className="flex items-center gap-3">
          <span className="font-mono text-2xl tnum text-emerald">{s.composite}</span>
          <Pill signal={s.signal} />
        </div>
      </div>
      <div className="space-y-2.5">
        <Bar label="Momentum" value={s.momentum} />
        <Bar label="Quality" value={s.quality} />
        <Bar label="News" value={s.news} />
        <Bar label="Sentiment" value={s.sentiment} />
        <Bar label="Sector" value={s.sectorScore} />
      </div>
      <p className="mt-4 text-xs text-dim">News and Sentiment show <span className="text-muted">pending</span> until those agents are wired (API keys verified, agent live).</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top scores (filter)
// ---------------------------------------------------------------------------
export function TopScores({ rows }: { rows: ScoreRow[] }) {
  const sectors = useMemo(() => ["All", ...Array.from(new Set(rows.map((r) => r.sector))).sort()], [rows]);
  const [sector, setSector] = useState("All");
  const view = useMemo(
    () => rows.filter((r) => sector === "All" || r.sector === sector).sort((a, b) => b.composite - a.composite),
    [rows, sector],
  );
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {sectors.map((sec) => (
          <button
            key={sec}
            type="button"
            onClick={() => setSector(sec)}
            aria-pressed={sector === sec}
            className={`rounded-md px-2.5 py-1 text-xs motion-safe:transition-[color,background-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 ${sector === sec ? "bg-emerald/12 text-emerald" : "bg-white/4 text-dim hover:text-muted"}`}
          >
            {sec}
          </button>
        ))}
      </div>
      <div className="scroll-touch overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse">
          <thead>
            <tr className="border-b border-hairline text-left text-xs font-medium text-dim">
              <th className="py-2">Ticker</th><th className="py-2">Sector</th>
              <th className="py-2 text-right">Mom</th><th className="py-2 text-right">Qual</th>
              <th className="py-2 text-right">News</th><th className="py-2 text-right">Sent</th>
              <th className="py-2 text-right">Score</th><th className="py-2 text-right">Signal</th>
            </tr>
          </thead>
          <tbody className="tnum">
            {view.map((r) => (
              <tr key={r.isin} className="border-b border-hairline/60">
                <td className="py-2.5 font-mono text-sm text-ink">{r.ticker}</td>
                <td className="py-2.5 text-xs text-dim">{r.sector}</td>
                <td className="py-2.5 text-right font-mono text-sm text-muted">{r.momentum}</td>
                <td className="py-2.5 text-right font-mono text-sm text-muted">{r.quality}</td>
                <td className="py-2.5 text-right font-mono text-xs text-dim">{r.news ?? "-"}</td>
                <td className="py-2.5 text-right font-mono text-xs text-dim">{r.sentiment ?? "-"}</td>
                <td className="py-2.5 text-right font-mono text-sm text-emerald">{r.composite}</td>
                <td className="py-2.5 text-right"><Pill signal={r.signal} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Agent activity board (live polling)
// ---------------------------------------------------------------------------
// Static dot + glow per status (mirrors agents.tsx — an infinite pulse on a
// status dot is AI-slop noise; the glow alone reads as "active"). On a status
// TRANSITION the dot re-mounts (keyed by class) and plays ONE settle-flash.
const DOT: Record<AgentRun["status"], string> = {
  done: "bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.55)]",
  running: "bg-amber shadow-[0_0_6px_rgba(251,191,36,0.55)]",
  waiting: "bg-white/30",
  offline: "bg-rose/60",
  error: "bg-rose shadow-[0_0_6px_rgba(251,113,133,0.45)]",
};

function FlashDot({ cls }: { cls: string }) {
  const reduce = useReducedMotionSafe();
  const first = useRef(true);
  useEffect(() => { first.current = false; }, []);
  return (
    <motion.span
      key={cls} // remount on state change → one-shot flash; static otherwise
      aria-hidden
      className={`h-2 w-2 shrink-0 rounded-full ${cls}`}
      initial={reduce || first.current ? false : { scale: 1.8, opacity: 0.5 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.45, ease: EASE }}
    />
  );
}
const GROUPS: { key: AgentRun["group"]; label: string }[] = [
  { key: "selection", label: "Selection" },
  { key: "market", label: "Market" },
  { key: "meta", label: "Meta" },
];

function AgentCard({ a }: { a: AgentRun }) {
  const running = a.status === "running";
  const pctDone = running && a.progressTotal ? Math.round((a.progressCurrent! / a.progressTotal) * 100) : 0;
  return (
    <div className="rounded-lg border border-hairline bg-panel2/60 p-3">
      <div className="flex items-center gap-2">
        <FlashDot cls={DOT[a.status]} />
        <span className="text-sm text-ink">{a.agentName}</span>
        <span className="ml-auto font-mono text-[11px] text-dim">
          {a.status === "offline" ? "offline" : a.durationMs ? `${(a.durationMs / 1000).toFixed(1)}s` : running ? "running" : ""}
        </span>
      </div>
      <p className="mt-1.5 text-xs text-muted">{a.headlineOutput}</p>
      {running && (
        <div className="mt-2">
          <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
            <div className="h-full bg-amber transition-[width]" style={{ width: `${pctDone}%` }} />
          </div>
          <div className="mt-1 text-right font-mono text-[10px] text-dim">{a.progressCurrent}/{a.progressTotal}</div>
        </div>
      )}
      {a.status === "offline" && a.offlineReason && (
        <p className="mt-1 text-[11px] text-rose/80">{a.offlineReason}</p>
      )}
    </div>
  );
}

export function AgentActivity() {
  const [board, setBoard] = useState<TBoard | null>(null);
  useEffect(() => {
    let on = true;
    const load = async () => {
      try {
        const r = await fetch("/api/agents", { cache: "no-store" });
        const b: TBoard = await r.json();
        if (on) setBoard(b);
      } catch { /* keep last board on a transient error */ }
    };
    load();
    const id = setInterval(load, 4000); // poll every 4s so running agents tick live
    return () => { on = false; clearInterval(id); };
  }, []);

  if (!board) return <Empty msg="Loading agent activity..." />;
  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-xs text-muted">
        <FlashDot cls={board.inProgress ? DOT.running : DOT.done} />
        {board.inProgress ? "Run in progress" : "Idle"} · last update {ago(board.lastRun)}
        <span className="ml-auto font-mono text-dim">{board.runId}</span>
      </div>
      {GROUPS.map((g) => {
        const items = board.agents.filter((a) => a.group === g.key);
        if (!items.length) return null;
        return (
          <div key={g.key} className="mb-4">
            <div className="mb-2 text-[11px] uppercase tracking-wider text-dim">{g.label}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((a) => <AgentCard key={a.agentName} a={a} />)}
            </div>
          </div>
        );
      })}
      <p className="mt-2 border-t border-hairline pt-3 text-xs text-dim">
        These scores feed <span className="text-muted">Enhanced F+</span> (frozen risk engine) — agents produce signals, Enhanced F+ decides the portfolio.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
export function Empty({ msg = "No data yet — paper trade starts when the engine goes live." }: { msg?: string }) {
  return <div className="grid place-items-center rounded-xl2 border border-dashed border-border py-10 text-sm text-dim">{msg}</div>;
}
