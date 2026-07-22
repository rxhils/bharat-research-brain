"use client";

// Strategies overview — the live, fully-backtested portfolios (see the LIVE
// array) with their EXACT validated figures, and the rest shown as a compact
// validation pipeline with NO numbers. Static content only; no DB.
//
// Wave-2 redesign (docs/design-plan/page-strategies.md):
// - Signature: per-card equity-curve sparkline (PathDraw, brand-motion — plays
//   under OS reduced-motion) vs a dim dashed Nifty 500 baseline. The ~24
//   monthly points per curve are illustrative interpolations; the START (0%),
//   END (total return) and dip depth (max drawdown) are consistent with the
//   verbatim backtest figures. No interim numbers are ever labeled.
// - Animated benchmark delta bar per card (strategy vs +82.17% Nifty 500).
// - Seven in-validation entries compressed into a tight two-column grid with
//   legible type (nothing below 10px; labels 11px mono).
// - Flagship keeps the gold crown + border-beam (decorative loop — freezes
//   under reduced motion by design); gold appears nowhere else except the
//   header eyebrow.
// Numbers must match the validated figures verbatim — nothing invented,
// nothing rounded differently.

import { motion, useMotionTemplate, useMotionValue } from "framer-motion";
import { useEffect, useState, type PointerEvent } from "react";
import { GlassPanel } from "@/components/glass-panel";
import { CountUp, EASE, EASE_SOFT, PathDraw, Reveal, SectionEyebrow, useReducedMotionSafe } from "@/components/motion";

type Stat = { label: string; value: number; prefix?: string; suffix?: string; decimals?: number; tone?: "emerald" | "amber"; note?: string };
type Live = {
  name: string; sub?: string; flagship?: boolean; oneLiner: string; stats: Stat[];
  edge: string; forWho: string; period: string;
  /** Illustrative monthly equity-curve shape (cumulative % return). Endpoints
   *  and dip depth match the verbatim figures; intermediate points are shape
   *  only and are never labeled. */
  series: number[];
};

/** Verbatim benchmark figure (Nifty 500, 2021–26) — matches /backtest. */
const NIFTY_RETURN = 82.17;

/** Illustrative Nifty 500 baseline shape — starts 0, ends +82.17% verbatim. */
const NIFTY_SERIES = [0, 3, 7, 10, 8, 13, 17, 21, 18, 14, 19, 24, 22, 28, 33, 38, 35, 42, 48, 54, 58, 66, 74, 82.17];

const LIVE: Live[] = [
  {
    name: "Quant", sub: "Enhanced F+", flagship: true,
    oneLiner: "Balanced growth with strong risk management.",
    stats: [
      { label: "Total return", value: 129.97, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 14.05, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 14, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Beat the Nifty 500 — +129.97% vs +82.17% — at a lower drawdown.",
    forWho: "Investors who want growth with crash protection.",
    period: "2021–26",
    series: [0, 4, 9, 14, 18, 24, 30, 35, 25, 16, 24, 33, 38, 45, 52, 60, 56, 65, 74, 85, 94, 106, 118, 129.97],
  },
  {
    name: "Defensive",
    oneLiner: "Safety-first. Smaller drops, smoother ride.",
    stats: [
      { label: "Total return", value: 84.61, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 17.63, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 9, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Lower drawdown than Quant in 7 of 8 test windows, with better COVID survival — it trades a little return for less risk.",
    forWho: "Cautious investors prioritising capital protection.",
    period: "2021–26",
    series: [0, 3, 6, 10, 14, 18, 23, 30, 20, 7, 14, 21, 26, 31, 37, 43, 40, 47, 53, 60, 65, 72, 78, 84.61],
  },
  {
    name: "Concentrated",
    oneLiner: "Enhanced F+, concentrated to the top 10.",
    stats: [
      { label: "Total return", value: 152.66, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 12.63, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 21, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Highest return of the three — +152.66% vs the index's +82.17% — by holding only the top 10. Same crash brakes as Quant, but more single-name risk (a deeper ~21% COVID drawdown).",
    forWho: "Investors who want maximum conviction and upside, and can accept more concentration risk.",
    period: "2021–26",
    series: [0, 5, 11, 17, 23, 31, 40, 22.4, 30, 38, 34, 45, 52, 61, 70, 66, 78, 89, 101, 110, 122, 132, 143, 152.66],
  },
];

// Spelled-out count derived from LIVE so the subheadline can never drift from
// the number of cards actually rendered.
const COUNT_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"] as const;
const LIVE_COUNT_WORD = COUNT_WORDS[LIVE.length] ?? String(LIVE.length);

/** Widest bar in the benchmark-delta pairs = the best total return on page. */
const BAR_MAX = Math.max(NIFTY_RETURN, ...LIVE.map((p) => p.stats[0].value));

const SOON: { name: string; style: string }[] = [
  { name: "Growth", style: "Higher-upside names with faster compounding potential." },
  { name: "Core", style: "A steady, benchmark-aware long-term base." },
  { name: "Value", style: "Undervalued businesses priced below their fundamentals." },
  { name: "Income", style: "Dependable cash generation and sustainable payouts." },
  { name: "Momentum", style: "Market leaders already showing trend strength." },
  { name: "Quality", style: "Durable, financially strong businesses." },
  { name: "Constrained", style: "Rules-based selection inside tighter risk limits." },
];

function Crown() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#c9a961" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 8l4 3 5-7 5 7 4-3-2 11H5z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Sparkline — the page's signature: each live card draws its equity curve
// (PathDraw = motion.path pathLength inside .brand-motion, so it plays under
// the OS reduced-motion flag) departing from a static, dim, dashed Nifty 500
// baseline. Uniform SVG scaling (no preserveAspectRatio="none") keeps the
// stroke and endpoint dot round.
// ---------------------------------------------------------------------------
const SPARK_W = 240;
const SPARK_H = 64;
const SPARK_P = 4;

function sparkPoints(series: number[], max: number): [number, number][] {
  const n = series.length - 1;
  return series.map((v, i) => [
    +(SPARK_P + (i * (SPARK_W - 2 * SPARK_P)) / n).toFixed(1),
    +(SPARK_H - SPARK_P - (v / max) * (SPARK_H - 2 * SPARK_P)).toFixed(1),
  ]);
}

function toPathD(pts: [number, number][]): string {
  return pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x} ${y}`).join(" ");
}

function Sparkline({ series, name, delay = 0 }: { series: number[]; name: string; delay?: number }) {
  const max = Math.max(...series, ...NIFTY_SERIES);
  const strat = sparkPoints(series, max);
  const nifty = sparkPoints(NIFTY_SERIES, max);
  const d = toPathD(strat);
  const first = strat[0];
  const last = strat[strat.length - 1];
  const areaD = `${d} L${last[0]} ${SPARK_H - SPARK_P} L${first[0]} ${SPARK_H - SPARK_P} Z`;
  return (
    <div>
      <svg
        viewBox={`0 0 ${SPARK_W} ${SPARK_H}`}
        className="w-full"
        role="img"
        aria-label={`${name} backtested equity curve versus the dim Nifty 500 baseline`}
      >
        {/* Benchmark baseline — static, dim, dashed: the reference the strategy visibly departs from. */}
        <path d={toPathD(nifty)} fill="none" stroke="rgba(148,163,184,0.4)" strokeWidth="1.25" strokeDasharray="3 4" strokeLinecap="round" />
        <PathDraw
          d={d}
          strokeWidth={1.75}
          duration={1.5}
          delay={delay}
          gradient={{ from: "#10b981", to: "#34d399" }}
          areaD={areaD}
          areaFill="rgba(52,211,153,0.07)"
          dot={{ cx: last[0], cy: last[1], r: 2.5 }}
        />
      </svg>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] uppercase tracking-[0.1em] text-dim">
        <span className="flex items-center gap-1.5"><span className="h-px w-4 bg-emerald" aria-hidden />{name}</span>
        <span className="flex items-center gap-1.5"><span className="w-4 border-t border-dashed" style={{ borderColor: "rgba(148,163,184,0.5)" }} aria-hidden />Nifty 500</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Benchmark delta bar — strategy total return vs the Nifty 500's +82.17%,
// two width-proportional bars animating scaleX from the left on in-view.
// Inline motion transforms + .brand-motion, so it plays under reduced motion.
// ---------------------------------------------------------------------------
function BarRow({ label, value, prefix, dim, delay }: {
  label: string; value: number; prefix: string; dim?: boolean; delay: number;
}) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr_auto] items-center gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-dim">{label}</span>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <motion.div
          className={`h-full rounded-full ${dim ? "bg-slate-400/50" : "bg-emerald"}`}
          style={{ width: `${(value / BAR_MAX) * 100}%`, transformOrigin: "0% 50%" }}
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true, margin: "-10% 0px" }}
          transition={{ duration: 0.8, delay, ease: EASE }}
        />
      </div>
      <span className={`font-mono text-xs tnum ${dim ? "text-dim" : "text-emerald"}`}>{prefix}{value.toFixed(2)}%</span>
    </div>
  );
}

function DeltaBars({ value, delay = 0 }: { value: number; delay?: number }) {
  return (
    <div className="brand-motion mt-4 space-y-2">
      <BarRow label="This model" value={value} prefix="+" delay={delay} />
      <BarRow label="Nifty 500" value={NIFTY_RETURN} prefix="+" dim delay={delay + 0.15} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// RiskReturnMap — the page's signature: an SVG scatter of total return (y)
// against maximum drawdown (x, lower drawdown to the RIGHT = better) for the
// three live strategies plus the Nifty 500 benchmark. EVERY point is a verbatim
// figure: strategy return/drawdown from LIVE; the Nifty dot's drawdown (18.59%)
// from /backtest (2021-06 → 2026-05 capital sim). The numeric labels are plain
// HTML (always in the SSR markup — crawlers read the real figures); only the
// dots and connectors animate. Inside .brand-motion, so it plays under the OS
// reduced-motion flag (a signature moment, not a decorative loop).
// ---------------------------------------------------------------------------

/** Nifty 500 max drawdown over 2021-06 → 2026-05, verbatim from /backtest. */
const NIFTY_DD = 18.59;

type MapPt = {
  name: string; ret: number; dd: number; tone: "emerald" | "slate";
  flagship?: boolean; side: "l" | "r"; dy: number;
};
/** Label placement per point (keyed by card name) — hand-tuned to avoid overlap. */
const MAP_PLACEMENT: Record<string, { side: "l" | "r"; dy: number }> = {
  "Nifty 500": { side: "r", dy: 15 },
  "Quant": { side: "l", dy: -4 },
  "Defensive": { side: "r", dy: -15 },
  "Concentrated": { side: "l", dy: 2 },
};
const MAP_PTS: MapPt[] = [
  { name: "Nifty 500", ret: NIFTY_RETURN, dd: NIFTY_DD, tone: "slate", ...MAP_PLACEMENT["Nifty 500"] },
  ...LIVE.map((p) => ({
    name: p.name,
    ret: p.stats[0].value,
    dd: p.stats[1].value,
    tone: "emerald" as const,
    flagship: p.flagship,
    ...(MAP_PLACEMENT[p.name] ?? { side: "l" as const, dy: 0 }),
  })),
];

const MAP_W = 460, MAP_H = 300, MAP_PADL = 40, MAP_PADR = 24, MAP_PADT = 28, MAP_PADB = 40;
const MAP_PLOTW = MAP_W - MAP_PADL - MAP_PADR;
const MAP_PLOTH = MAP_H - MAP_PADT - MAP_PADB;
const DD_MIN = 12, DD_MAX = 19, RET_MIN = 78, RET_MAX = 156;
const mapX = (dd: number) => MAP_PADL + ((DD_MAX - dd) / (DD_MAX - DD_MIN)) * MAP_PLOTW; // lower dd → right
const mapY = (ret: number) => MAP_PADT + ((RET_MAX - ret) / (RET_MAX - RET_MIN)) * MAP_PLOTH;

function MapLabel({ p }: { p: MapPt }) {
  const leftPct = (mapX(p.dd) / MAP_W) * 100;
  const topPct = (mapY(p.ret) / MAP_H) * 100;
  return (
    <div className="pointer-events-none absolute" style={{ left: `${leftPct}%`, top: `${topPct}%` }}>
      <div
        className={`absolute whitespace-nowrap ${p.side === "l" ? "right-2 text-right" : "left-2"}`}
        style={{ transform: `translateY(calc(-50% + ${p.dy}px))` }}
      >
        <div className={`font-mono text-[10px] font-semibold ${p.tone === "emerald" ? "text-emerald" : "text-muted"}`}>
          {p.name}
        </div>
        <div className="font-mono text-[9px] tnum text-dim">+{p.ret.toFixed(2)}% · DD {p.dd.toFixed(2)}%</div>
      </div>
    </div>
  );
}

function RiskReturnMap() {
  const nifty = MAP_PTS[0];
  const strategies = MAP_PTS.slice(1);
  const nx = mapX(nifty.dd), ny = mapY(nifty.ret);
  const grid = [0.25, 0.5, 0.75];
  return (
    <div className="brand-motion">
      <div className="relative w-full" style={{ aspectRatio: `${MAP_W} / ${MAP_H}` }}>
        <svg
          viewBox={`0 0 ${MAP_W} ${MAP_H}`}
          className="absolute inset-0 h-full w-full"
          role="img"
          aria-label="Risk versus return scatter: total return against maximum drawdown for each live strategy and the Nifty 500 benchmark. Lower drawdown and higher return is better (top-right)."
        >
          {/* plot frame + faint gridlines (scale only — no numeric claims) */}
          <rect x={MAP_PADL} y={MAP_PADT} width={MAP_PLOTW} height={MAP_PLOTH} fill="none" stroke="rgba(255,255,255,0.07)" />
          {grid.map((f) => (
            <line key={`h${f}`} x1={MAP_PADL} x2={MAP_W - MAP_PADR} y1={MAP_PADT + f * MAP_PLOTH} y2={MAP_PADT + f * MAP_PLOTH} stroke="rgba(255,255,255,0.04)" />
          ))}
          {grid.map((f) => (
            <line key={`v${f}`} x1={MAP_PADL + f * MAP_PLOTW} x2={MAP_PADL + f * MAP_PLOTW} y1={MAP_PADT} y2={MAP_H - MAP_PADB} stroke="rgba(255,255,255,0.04)" />
          ))}
          {/* improvement vectors: benchmark → each strategy, dashed, draw in staggered */}
          {strategies.map((s, i) => (
            <motion.path
              key={s.name}
              d={`M${nx.toFixed(1)} ${ny.toFixed(1)} L${mapX(s.dd).toFixed(1)} ${mapY(s.ret).toFixed(1)}`}
              fill="none"
              stroke="rgba(52,211,153,0.3)"
              strokeWidth={1}
              strokeDasharray="3 4"
              initial={{ pathLength: 0, opacity: 0.85 }}
              whileInView={{ pathLength: 1, opacity: 0.85 }}
              viewport={{ once: true, margin: "-10% 0px" }}
              transition={{ duration: 0.7, delay: 0.5 + i * 0.25, ease: EASE }}
            />
          ))}
          {/* benchmark dot fades in first */}
          <motion.circle
            cx={nx} cy={ny} r={5} fill="#64748b"
            style={{ transformBox: "fill-box", transformOrigin: "center" }}
            initial={{ opacity: 0, scale: 0 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-10% 0px" }}
            transition={{ duration: 0.4, delay: 0.2, ease: EASE_SOFT }}
          />
          {/* strategy dots spring in after the connectors */}
          {strategies.map((s, i) => (
            <motion.circle
              key={s.name}
              cx={mapX(s.dd)} cy={mapY(s.ret)} r={s.flagship ? 7 : 5.5} fill="#34d399"
              style={{ transformBox: "fill-box", transformOrigin: "center" }}
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-10% 0px" }}
              transition={{ type: "spring", stiffness: 320, damping: 18, delay: 1.1 + i * 0.12 }}
            />
          ))}
          {/* axis titles */}
          <text x={MAP_PADL + MAP_PLOTW / 2} y={MAP_H - 8} textAnchor="middle" fill="#64748b" fontFamily="ui-monospace, monospace" fontSize="9" letterSpacing="1.2">
            MAX DRAWDOWN · LOWER →
          </text>
          <text x={12} y={MAP_PADT + MAP_PLOTH / 2} textAnchor="middle" fill="#64748b" fontFamily="ui-monospace, monospace" fontSize="9" letterSpacing="1.2" transform={`rotate(-90 12 ${MAP_PADT + MAP_PLOTH / 2})`}>
            TOTAL RETURN →
          </text>
        </svg>
        {/* HTML overlay labels — verbatim figures, always in the SSR markup */}
        {MAP_PTS.map((p) => <MapLabel key={p.name} p={p} />)}
        <div className="pointer-events-none absolute right-2 top-2 font-mono text-[9px] uppercase tracking-[0.14em] text-emerald/70">best ↗</div>
      </div>
    </div>
  );
}

function LiveCard({ p, delay }: { p: Live; delay: number }) {
  const reduce = useReducedMotionSafe();
  const ret = p.stats[0];
  const risk = p.stats.slice(1); // max-drawdown + COVID-drawdown, demoted to a 2-up row
  // Pointer-tracked hover spotlight (desktop, fine pointer, non-RM). Decorative,
  // background-only — no transform/opacity churn on the card itself.
  const mx = useMotionValue(-200);
  const my = useMotionValue(-200);
  const spotlight = useMotionTemplate`radial-gradient(300px circle at ${mx}px ${my}px, rgba(52,211,153,0.07), transparent 70%)`;
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFine(mq.matches);
    const on = (e: MediaQueryListEvent) => setFine(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const showSpotlight = fine && !reduce;
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!showSpotlight) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set(e.clientX - r.left);
    my.set(e.clientY - r.top);
  };
  return (
    <Reveal y={18} delay={delay} className="h-full">
      <motion.div
        className="group h-full"
        onPointerMove={onMove}
        whileHover={reduce ? undefined : { y: -6, scale: 1.012 }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
      >
        <GlassPanel
          glow={p.flagship ? "gold" : "none"}
          noise
          className={`h-full${p.flagship ? " border-beam" : ""}`}
          innerClassName="flex h-full flex-col p-6 sm:p-7"
        >
          {showSpotlight && (
            <motion.div
              aria-hidden
              className="pointer-events-none absolute inset-0 z-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              style={{ background: spotlight }}
            />
          )}
          {/* Static radial glow behind the flagship — depth, not a loop. */}
          {p.flagship && <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.18),transparent 70%)" }} aria-hidden />}
          <div className="relative z-10 flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              {p.flagship && <Crown />}
              <div>
                <h3 className="font-serif text-2xl text-ink">{p.name}</h3>
                {p.sub && <p className="text-xs text-gold-soft">{p.sub}</p>}
              </div>
            </div>
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald/40 bg-emerald/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-emerald">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald" aria-hidden />Live
            </span>
          </div>
          <p className="relative z-10 mt-3 text-sm italic text-emerald/90">{p.oneLiner}</p>

          {/* Hero figure: total return owns the card. */}
          <div className="relative z-10 mt-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-dim">Total return · {p.period}</div>
            <div className="mt-1 font-mono text-3xl font-semibold leading-none text-emerald">
              <CountUp to={ret.value} prefix={ret.prefix} suffix={ret.suffix} decimals={ret.decimals ?? 2} />
            </div>
          </div>

          {/* Signature: equity curve vs dim Nifty baseline. */}
          <div className="relative z-10 mt-5">
            <Sparkline series={p.series} name={p.name} delay={delay} />
          </div>

          {/* Benchmark delta bars. */}
          <div className="relative z-10">
            <DeltaBars value={ret.value} delay={delay} />
          </div>

          {/* Risk, demoted: a compact two-up row (mobile-safe). */}
          <div className="relative z-10 mt-5 grid grid-cols-2 gap-3">
            {risk.map((s) => (
              <div key={s.label} className="rounded-lg border border-hairline bg-bg/40 px-3 py-2.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-dim">{s.label}</div>
                <div className={`mt-1 font-mono text-lg font-semibold ${s.tone === "amber" ? "text-amber" : "text-emerald"}`}>
                  <CountUp to={s.value} prefix={s.prefix} suffix={s.suffix} decimals={s.decimals ?? 2} />
                </div>
                {s.note && <div className="mt-0.5 text-[10px] leading-snug text-dim">{s.note}</div>}
              </div>
            ))}
          </div>
          <p className="relative z-10 mt-4 text-sm leading-relaxed text-muted">{p.edge}</p>
          <div className="relative z-10 mt-auto border-t border-hairline pt-3">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-dim">For</p>
            <p className="mt-1 text-sm text-ink/90">{p.forWho}</p>
            <p className="mt-3 text-[11px] text-dim">Backtested ({p.period}) — not a live track record.</p>
          </div>
        </GlassPanel>
      </motion.div>
    </Reveal>
  );
}

export default function StrategiesPage() {
  const reduce = useReducedMotionSafe();
  return (
    <div className="pt-6">
      <header className="pb-2">
        <SectionEyebrow tone="gold">AI Portfolios</SectionEyebrow>
        <h1 className="mt-4 font-serif text-[clamp(2.25rem,1rem+4.5vw,4.5rem)] font-light leading-[0.98] tracking-[-0.02em] text-ink">Models, ranked.</h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">{LIVE_COUNT_WORD} {LIVE.length === 1 ? "strategy is" : "strategies are"} live and fully backtested. The rest are in validation — no numbers until they&apos;ve earned them.</p>
        {/* Mono stat strip — every figure derived or verbatim. */}
        <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2 font-mono text-[11px] uppercase tracking-[0.14em] text-dim">
          <span><span className="text-emerald">{LIVE.length}</span> live</span>
          <span aria-hidden>·</span>
          <span><span className="text-ink">{SOON.length}</span> in validation</span>
          <span aria-hidden>·</span>
          <span>2021–26 window</span>
          <span aria-hidden>·</span>
          <span>vs Nifty 500 <CountUp className="text-ink" to={NIFTY_RETURN} prefix="+" suffix="%" decimals={2} /></span>
        </div>
      </header>

      {/* Signature: the risk/return map — where each model sits, verbatim. */}
      <section className="mt-10">
        <div className="flex items-center gap-3">
          <SectionEyebrow number="01">Risk vs return — where each model sits</SectionEyebrow>
          <span className="h-px flex-1 bg-hairline" aria-hidden />
        </div>
        <GlassPanel className="mt-5" innerClassName="p-4 sm:p-6" noise>
          <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.14em] text-emerald">Lower drawdown → higher return</p>
          <RiskReturnMap />
          <p className="mt-4 max-w-3xl text-[11px] leading-relaxed text-dim">
            Each point is a verbatim backtest figure (2021–26): total return plotted against maximum
            drawdown. The dashed lines mark each model&apos;s distance from the Nifty 500 benchmark —
            up and to the right is more return for less risk. Backtested, not a live track record.
          </p>
        </GlassPanel>
      </section>

      <section className="mt-14">
        <div className="flex items-center gap-3">
          <SectionEyebrow number="02">Live &amp; validated</SectionEyebrow>
          <span className="h-px flex-1 bg-hairline" aria-hidden />
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-3">
          {LIVE.map((p, i) => <LiveCard key={p.name} p={p} delay={i * 0.08} />)}
        </div>
        <p className="mt-3 max-w-3xl text-[11px] leading-relaxed text-dim">
          Curve shapes are illustrative monthly interpolations — the start, end and drawdown depth of each
          line are the verbatim backtest figures; intermediate points are not data and carry no labels.
        </p>
      </section>

      <section className="mt-14">
        <div className="flex items-center gap-3">
          <SectionEyebrow number="03">Validation pipeline — no numbers until earned</SectionEyebrow>
          <span className="h-px flex-1 bg-hairline" aria-hidden />
        </div>
        {/* Single-panel ledger — one staggered Reveal parent, hairline-separated
            rows: mono name left, style centre, "In validation" tick right. */}
        <GlassPanel className="mt-5" innerClassName="p-2 sm:p-3" noise>
          {/* per-item initial/whileInView (same proven pattern as the live cards);
              parent-variant propagation through GlassPanel did not fire the reveal */}
          <ul className="divide-y divide-hairline">
            {SOON.map((s, i) => (
              <motion.li
                key={s.name}
                className="grid grid-cols-[7rem_1fr_auto] items-center gap-3 px-3 py-2.5 sm:gap-5"
                initial={reduce ? false : { opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-8% 0px" }}
                transition={{ duration: 0.4, delay: i * 0.05, ease: EASE }}
              >
                <span className="font-serif text-base text-ink/90">{s.name}</span>
                <span className="text-[11px] leading-snug text-dim">{s.style}</span>
                <span className="shrink-0 rounded-full border border-border px-2.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-dim">In validation</span>
              </motion.li>
            ))}
          </ul>
        </GlassPanel>
      </section>

      <div className="mt-12 max-w-3xl border-t border-hairline pt-4">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-dim">Methodology</p>
        <p className="mt-2 text-xs leading-relaxed text-dim">
          Backtested results — not a live track record. Based on current index constituents, so absolute
          returns are optimistic. Past performance does not guarantee future results. For personal research
          and educational purposes only; not investment advice.
        </p>
      </div>
    </div>
  );
}
