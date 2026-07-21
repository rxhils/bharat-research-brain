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

import { motion } from "framer-motion";
import { GlassPanel } from "@/components/glass-panel";
import { CountUp, EASE, PathDraw, Reveal, SectionEyebrow, useReducedMotionSafe } from "@/components/motion";

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
      <div className="mt-1.5 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.1em] text-dim">
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

function LiveCard({ p, delay }: { p: Live; delay: number }) {
  const reduce = useReducedMotionSafe();
  return (
    <Reveal y={18} delay={delay} className="h-full">
      <motion.div
        className="h-full"
        whileHover={reduce ? undefined : { y: -6, scale: 1.012 }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
      >
        <GlassPanel
          glow={p.flagship ? "gold" : "none"}
          noise
          className={`h-full${p.flagship ? " border-beam" : ""}`}
          innerClassName="flex h-full flex-col p-6 sm:p-7"
        >
          {/* Static radial glow behind the flagship — depth, not a loop. */}
          {p.flagship && <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.18),transparent 70%)" }} aria-hidden />}
          <div className="relative flex items-start justify-between gap-3">
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
          <p className="relative mt-3 text-sm italic text-emerald/90">{p.oneLiner}</p>

          {/* Signature: equity curve vs dim Nifty baseline. */}
          <div className="relative mt-5">
            <Sparkline series={p.series} name={p.name} delay={delay} />
          </div>

          {/* Benchmark delta bars. */}
          <DeltaBars value={p.stats[0].value} delay={delay} />

          <div className="relative mt-5 grid grid-cols-3 gap-3">
            {p.stats.map((s) => (
              <div key={s.label} className="rounded-lg border border-hairline bg-bg/40 px-3 py-2.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-dim">{s.label}</div>
                <div className={`mt-1 font-mono text-lg font-semibold ${s.tone === "amber" ? "text-amber" : "text-emerald"}`}>
                  <CountUp to={s.value} prefix={s.prefix} suffix={s.suffix} decimals={s.decimals ?? 2} />
                </div>
                {s.note && <div className="mt-0.5 text-[10px] leading-snug text-dim">{s.note}</div>}
              </div>
            ))}
          </div>
          <p className="relative mt-4 text-sm leading-relaxed text-muted">{p.edge}</p>
          <div className="relative mt-auto border-t border-hairline pt-3">
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

      <section className="mt-10">
        <div className="flex items-center gap-3">
          <SectionEyebrow number="01">Live &amp; validated</SectionEyebrow>
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
          <SectionEyebrow number="02">Validation pipeline — no numbers until earned</SectionEyebrow>
          <span className="h-px flex-1 bg-hairline" aria-hidden />
        </div>
        <GlassPanel className="mt-5" innerClassName="p-3 sm:p-4" noise>
          <div className="grid gap-2 md:grid-cols-2">
            {SOON.map((s, i) => (
              <Reveal key={s.name} y={10} delay={i * 0.045}>
                <div className="flex h-full flex-col gap-1.5 rounded-lg bg-white/[0.03] px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-serif text-base text-ink/90">{s.name}</span>
                    <span className="shrink-0 rounded-full border border-border px-2.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-dim">In validation</span>
                  </div>
                  <span className="text-xs leading-relaxed text-dim">{s.style}</span>
                </div>
              </Reveal>
            ))}
          </div>
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
