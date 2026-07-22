"use client";

/**
 * Backtest proof page — REAL results from the frozen Enhanced F+ engine (commit 6ced078).
 *
 * Enhanced F+ = F+ base (quality gate, 25 stocks, ≤4/sector, hold-winners buffer,
 * daily 15% stop, weekly regime check, graded cash 100/50/25%, quarterly rebalance)
 * + vol-adjusted momentum + a 6.5% cash-sleeve yield. F+ classic (commit 6417a74) is
 * kept as the fallback comparator. Every number here is from the committed walk-forward
 * + ₹10L simulations against the Nifty 500 Total-Return Index:
 *   - 2021–2026 bull run — beat the index 4/4 windows
 *   - 2017–2020 stress era (incl. the COVID crash) — protected capital, beat 2/4
 * Backtested results, NOT a live track record. Data is inlined on purpose: the engine
 * is frozen, it does not swap to a DB query.
 *
 * Wave-2 redesign — "The Evidence Room": editorial hero + count-up band, the
 * full-period equity/underwater curve, and the "Crash, Scrubbed" scrollytelling
 * sequence (app/backtest/covid-scrub.tsx) replacing the static COVID list.
 * Gold appears exactly twice on this page: the hero's "The proof." and the
 * scrub's gap band — gold = the risk story, nowhere else.
 */

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ScrollProgress } from "@/components/scroll-progress";
import { ChartReveal, Reveal, SectionEyebrow, useReducedMotionSafe } from "@/components/motion";
import { CovidScrub } from "./covid-scrub";
import { EquityCurve } from "./equity-curve";
import { StatTicker } from "./stat-ticker";

// Recharts replays its draw on every re-render; allow one bar-grow pass on mount
// (600ms) then hard-disable, and skip it entirely under reduced motion. Mirrors
// the client.tsx line-chart convention so the two proof surfaces feel identical.
function useBarDrawOnce() {
  const reduce = useReducedMotionSafe();
  const [firstPass, setFirstPass] = useState(true);
  useEffect(() => {
    const id = window.setTimeout(() => setFirstPass(false), 800); // outlives the 600ms draw
    return () => window.clearTimeout(id);
  }, []);
  return firstPass && !reduce;
}

/* ---------- palette ---------- */
const EMERALD = "#34d399";
const SLATE = "#64748b";

/* ---------- tiny self-contained formatters ---------- */
const pc = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
const inr = (n: number) =>
  "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
const sign = (n: number) => (n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted");
/* drawdown is a risk number, not a directional loss — quiet slate by default,
 * house rose only when the pain is genuinely deep (≥20%). Retires amber. */
const ddTone = (n: number) => (n >= 20 ? "text-rose" : "text-muted");

/* ---------- data: ERA 2021–2026 (bull run, beat index 4/4) ---------- */
/* per-window Enhanced F+: ret / maxDD / Sharpe / trades vs Nifty 500 TRI */
const E2_WF = [
  { w: "W1", period: "2021–2023", ret: 33.97, sharpe: 1.02, dd: 8.02, trades: 63, idx: 21.95, alpha: 12.02, beat: true },
  { w: "W2", period: "2022–2024", ret: 96.83, sharpe: 2.24, dd: 8.98, trades: 118, idx: 52.78, alpha: 44.05, beat: true },
  { w: "W3", period: "2023–2025", ret: 54.05, sharpe: 1.14, dd: 14.48, trades: 134, idx: 47.42, alpha: 6.63, beat: true },
  { w: "W4", period: "2024–2026", ret: 24.67, sharpe: 0.24, dd: 15.00, trades: 121, idx: 20.46, alpha: 4.21, beat: true },
];

/* ₹10L outcome — Enhanced F+ primary, F+ classic fallback, Nifty 500 benchmark */
const E2_CAP = [
  { name: "Nifty 500 TRI", final: 1821735, ret: 82.17, dd: 18.59, sharpe: null as number | null, trades: null as number | null, accent: SLATE },
  { name: "Enhanced F+ ✓", final: 2299700, ret: 129.97, dd: 14.05, sharpe: 0.95, trades: null as number | null, accent: EMERALD },
  { name: "F+ classic (fallback)", final: 1815996, ret: 81.60, dd: 18.95, sharpe: 0.51, trades: 275, accent: SLATE },
];

/* ---------- data: ERA 2017–2020 (stress test) ---------- */
const E1_WF = [
  { w: "W1", period: "Jan'17–Dec'18", ret: 17.50, sharpe: 0.18, dd: 14.60, trades: 110, idx: 29.79, alpha: -12.29, beat: false },
  { w: "W2", period: "Jun'17–Jun'19", ret: 6.63, sharpe: -0.30, dd: 15.99, trades: 101, idx: 20.02, alpha: -13.39, beat: false },
  { w: "W3", period: "Jan'18–Jun'20 ⚠ COVID", ret: -7.40, sharpe: -1.01, dd: 13.88, trades: 146, idx: -7.46, alpha: 0.06, beat: true },
  { w: "W4", period: "Jun'18–Dec'20", ret: 46.89, sharpe: 0.80, dd: 16.90, trades: 138, idx: 25.00, alpha: 21.89, beat: true },
];

const E1_CAP = [
  { name: "Nifty 500 TRI", final: 1624459, ret: 62.45, dd: 38.52, sharpe: null as number | null, trades: null as number | null, accent: SLATE },
  { name: "Enhanced F+ ✓", final: 1822900, ret: 82.29, dd: 15.08, sharpe: 0.77, trades: null as number | null, accent: EMERALD },
  { name: "F+ classic (fallback)", final: 1409895, ret: 40.99, dd: 23.27, sharpe: 0.22, trades: 316, accent: SLATE },
];

/* max-drawdown over the full 2017–2020 stress era (lower = better) */
const STRESS_DD = [
  { name: "Nifty 500", dd: 38.52, accent: SLATE },
  { name: "F+ classic", dd: 23.27, accent: SLATE },
  { name: "Enhanced F+", dd: 15.08, accent: EMERALD },
];

const CAVEATS = [
  ["Backtested, not live", "Every figure on this page is a simulation over historical prices. It is NOT a live track record. The forward paper account is the only out-of-sample evidence — see the Portfolio and Brain pages."],
  ["No lookahead", "Every decision at date D uses only data dated ≤ D. The regime cut exposure during/before the COVID drop, never after — no hindsight leakage."],
  ["Survivorship", "The universe is today's Nifty 500 constituents, backfilled. It biases every config and the benchmark the same way, but absolute returns read optimistic. The return-vs-drawdown edge is the durable signal, not the headline percentage."],
  ["Cash yield is partly bull-amplified", "Enhanced F+ credits the cash sleeve at 6.5% (real T-bill ballpark) vs classic's 0%. In a rising market that interest is redeployed at each rebalance, so part of the uplift is bull-amplified — it would contribute less in a flat or falling tape."],
  ["Vol-adjusted momentum", "Enhanced F+ ranks on vol-adjusted momentum + quality + low-volatility. Pre-2024 fundamentals / news / sentiment were offline for the historical window, so the composite is price-and-quality driven there."],
  ["Frozen & guarded", "Engine pinned at commit 6ced078; F+ classic (commit 6417a74) kept as the locked fallback. No mutual-fund comparison is made — there is no NAV data here, so the only benchmark is the Nifty 500 TRI."],
];

/* ============================ presentational bits ============================ */

/** House glass-hairline panel: gradient p-px wrapper (brighter top edge = the
 *  /broker card recipe), inner top highlight, radius 20. No backdrop-filter —
 *  the blur budget is spent on the hero band and the page stays cheap. */
function Panel({ title, sub, children }: { title?: string; sub?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-[20px] bg-gradient-to-b from-white/[0.12] to-white/[0.03] p-px">
      <div className="rounded-[19px] bg-panel/95 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.07)] sm:p-6">
        {title && (
          <header className="mb-4">
            <h3 className="text-sm font-semibold tracking-tight text-ink">{title}</h3>
            {sub && <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted">{sub}</p>}
          </header>
        )}
        {children}
      </div>
    </section>
  );
}

/** Editorial chapter head — mono eyebrow, serif display, one-line standfirst. */
function EraHead({ eyebrow, title, standfirst }: { eyebrow: string; title: string; standfirst: string }) {
  return (
    <Reveal>
      <div className="border-t border-hairline pt-8">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{eyebrow}</p>
        <h2 className="mt-2 font-serif text-[clamp(1.75rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.01em] text-ink">
          {title}
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">{standfirst}</p>
      </div>
    </Reveal>
  );
}

const tipStyle = {
  background: "#0a0b0d",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  fontSize: 12,
};

/* Per-window alpha strip: index (slate) and Enhanced F+ (emerald) plotted on a
 * shared return scale, joined by a connector colored by the sign of alpha. Adds
 * the index-vs-strategy gap reading the table can't show, and breaks the
 * table→bars→table→bars rhythm between the two eras. */
function AlphaStrip({ rows }: { rows: typeof E1_WF }) {
  const vals = rows.flatMap((r) => [r.ret, r.idx]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = hi - lo || 1;
  // map a return to 6..94% of the track (padding keeps end dots off the edge)
  const x = (v: number) => 6 + ((v - lo) / span) * 88;
  return (
    <ChartReveal delay={0.1}>
      <div className="mt-5 space-y-2.5">
        <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-wide text-dim">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: SLATE }} />
            Nifty 500
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
            Enhanced F+
          </span>
          <span className="ml-auto normal-case tracking-normal">alpha</span>
        </div>
        {rows.map((r) => {
          const xi = x(r.idx);
          const xf = x(r.ret);
          const up = r.alpha >= 0;
          return (
            <div key={r.w} className="grid grid-cols-[3rem_1fr_4.25rem] items-center gap-3">
              <span className="font-mono text-[11px] text-muted">{r.w}</span>
              <div className="relative h-5">
                <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-white/[0.06]" />
                <div
                  className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${Math.min(xi, xf)}%`,
                    width: `${Math.abs(xf - xi)}%`,
                    background: up ? "rgba(52,211,153,0.55)" : "rgba(251,113,133,0.55)",
                  }}
                />
                <span
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2"
                  style={{ left: `${xi}%`, borderColor: SLATE, background: "#0a0b0d" }}
                />
                <span
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-emerald"
                  style={{ left: `${xf}%`, background: "#0a0b0d" }}
                />
              </div>
              <span className={`tnum text-right font-mono text-[11px] ${up ? "text-emerald" : "text-rose"}`}>
                {pc(r.alpha)}
              </span>
            </div>
          );
        })}
      </div>
    </ChartReveal>
  );
}

/* max-drawdown comparison (lower = better) */
function DrawdownBars() {
  const draw = useBarDrawOnce();
  return (
    <ChartReveal delay={0.1}>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={STRESS_DD} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: SLATE, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: SLATE, fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip contentStyle={tipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} formatter={(v: number) => [`${v}%`, "max drawdown"]} />
          <Bar dataKey="dd" radius={[3, 3, 0, 0]} maxBarSize={64} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out">
            {STRESS_DD.map((d, i) => (
              <Cell key={i} fill={d.accent} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartReveal>
  );
}

/* walk-forward table */
function WFTable({ rows }: { rows: typeof E1_WF }) {
  return (
    <div className="scroll-touch overflow-x-auto">
      <table className="w-full min-w-[600px] text-left text-sm">
        <thead className="text-[11px] uppercase tracking-wide text-muted">
          <tr className="border-b border-hairline">
            <th className="py-2 pr-3 font-medium">Window</th>
            <th className="py-2 pr-3 text-right font-medium">Enhanced F+ return</th>
            <th className="py-2 pr-3 text-right font-medium">Sharpe</th>
            <th className="py-2 pr-3 text-right font-medium">Max DD</th>
            <th className="py-2 pr-3 text-right font-medium">Trades</th>
            <th className="py-2 pr-3 text-right font-medium">Nifty 500</th>
            <th className="py-2 pr-3 text-right font-medium">Alpha</th>
            <th className="py-2 pr-0 text-right font-medium">Beat?</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((r) => (
            <tr key={r.w} className="border-b border-hairline/60 transition-colors hover:bg-white/[0.02]">
              <td className="py-2 pr-3 font-sans text-xs text-ink">
                <span className="font-semibold">{r.w}</span>{" "}
                <span className="text-muted">{r.period}</span>
              </td>
              <td className={`tnum py-2 pr-3 text-right ${sign(r.ret)}`}>{pc(r.ret)}</td>
              <td className={`tnum py-2 pr-3 text-right ${sign(r.sharpe)}`}>{r.sharpe.toFixed(2)}</td>
              <td className={`tnum py-2 pr-3 text-right ${ddTone(r.dd)}`}>{r.dd.toFixed(2)}%</td>
              <td className="tnum py-2 pr-3 text-right text-muted">{r.trades}</td>
              <td className={`tnum py-2 pr-3 text-right ${sign(r.idx)}`}>{pc(r.idx)}</td>
              <td className="py-2 pr-3 text-right">
                <span
                  className={`tnum rounded-md px-1.5 py-0.5 text-xs ${
                    r.alpha > 0 ? "bg-emerald/10 text-emerald" : "bg-rose/10 text-rose"
                  }`}
                >
                  {pc(r.alpha)}
                </span>
              </td>
              <td className="py-2 pr-0 text-right">
                {r.beat ? (
                  <span className="rounded-md bg-emerald/15 px-1.5 py-0.5 text-xs text-emerald">✓</span>
                ) : (
                  <span className="rounded-md bg-rose/10 px-1.5 py-0.5 text-xs text-rose">✗</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ₹10,00,000 capital outcome table */
function CapTable({ rows }: { rows: typeof E1_CAP }) {
  return (
    <div className="scroll-touch overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="text-[11px] uppercase tracking-wide text-muted">
          <tr className="border-b border-hairline">
            <th className="py-2 pr-3 font-medium">Strategy</th>
            <th className="py-2 pr-3 text-right font-medium">₹10L grew to</th>
            <th className="py-2 pr-3 text-right font-medium">Return</th>
            <th className="py-2 pr-3 text-right font-medium">Max DD</th>
            <th className="py-2 pr-3 text-right font-medium">Sharpe</th>
            <th className="py-2 pr-0 text-right font-medium">Trades</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((r) => {
            const hi = r.accent === EMERALD;
            return (
              <tr
                key={r.name}
                className={`border-b border-hairline/60 transition-colors hover:bg-white/[0.02] ${hi ? "bg-emerald/[0.04] shadow-[inset_2px_0_0_0_rgba(52,211,153,0.55)]" : ""}`}
              >
                <td className={`py-2 pl-2 pr-3 font-sans text-xs ${hi ? "font-semibold text-emerald" : "text-ink"}`}>{r.name}</td>
                <td className={`tnum py-2 pr-3 text-right ${hi ? "text-emerald" : "text-ink"}`}>{inr(r.final)}</td>
                <td className={`tnum py-2 pr-3 text-right ${sign(r.ret)}`}>{pc(r.ret)}</td>
                <td className={`tnum py-2 pr-3 text-right ${ddTone(r.dd)}`}>{r.dd.toFixed(2)}%</td>
                <td className="tnum py-2 pr-3 text-right text-muted">{r.sharpe === null ? "—" : r.sharpe.toFixed(2)}</td>
                <td className="tnum py-2 pr-0 text-right text-muted">{r.trades ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ============================ page ============================ */

export default function BacktestPage() {
  return (
    <div className="space-y-10 pt-8">
      <ScrollProgress />

      {/* hero — editorial scale; the radial glow is the light source, no cards */}
      <header className="relative space-y-6">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-16 left-1/2 h-[380px] w-full max-w-[760px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(52,211,153,0.07),transparent_65%)]"
        >
          <div className="noise-overlay" />
        </div>
        <div className="relative flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-emerald/30 bg-emerald/10 px-2.5 py-1 text-[11px] font-medium text-emerald">
            Backtested — not a live track record
          </span>
          <span className="rounded-full border border-hairline bg-panel/60 px-2.5 py-1 font-mono text-[11px] text-muted">
            frozen Enhanced F+ · commit 6ced078
          </span>
        </div>
        <h1 className="relative max-w-4xl text-balance font-serif text-[clamp(2.25rem,1rem+4.5vw,5rem)] leading-[1.02] tracking-[-0.02em] text-ink">
          Half the drawdown. <em className="italic text-gold-soft">The proof.</em>
        </h1>
        <p className="relative max-w-3xl text-base leading-relaxed text-muted">
          The engine running the paper account, tested two ways: across the 2021–2026 bull run and
          through the 2017–2020 stress era (the COVID crash). No-lookahead walk-forward plus a
          ₹10,00,000 capital simulation against the Nifty 500 Total-Return Index. F+ classic is shown
          alongside as the locked fallback.
        </p>
        <div className="relative">
          <StatTicker />
        </div>
      </header>

      {/* the missing artifact — full-period equity curve + underwater ribbon */}
      <section className="space-y-4">
        <Reveal>
          <div>
            <SectionEyebrow number="01">The full period</SectionEyebrow>
            <h2 className="mt-2 font-serif text-[clamp(1.75rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.01em] text-ink">
              Five years, one curve
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
              ₹10,00,000 through the 2021–2026 simulation — the equity path on top, the drawdown it
              cost underneath. Backtested results; the durable claim is the return-vs-drawdown edge,
              not the absolute percentage.
            </p>
          </div>
        </Reveal>
        <Panel>
          <EquityCurve />
        </Panel>
      </section>

      {/* ERA 1 — shown first: the 2021–2026 bull run */}
      <EraHead
        eyebrow="Era 1 · 2021–2026"
        title="The bull run"
        standfirst="Four overlapping walk-forward windows across the up-cycle — Enhanced F+ beat the index in every one."
      />

      <Reveal>
        <Panel
          title="Walk-forward — beat the index 4 / 4"
          sub="Every window cleared the Nifty 500 TRI on return, with positive alpha and a Sharpe above 1.0 in three of four windows. Backtested, no-lookahead."
        >
          <WFTable rows={E2_WF} />
          <AlphaStrip rows={E2_WF} />
        </Panel>
      </Reveal>

      <Reveal>
        <Panel
          title="₹10,00,000 simulated — 2021-06-01 → 2026-05-26"
          sub="Enhanced F+ grew ₹10L to ₹22.99L (+129.97%) versus the index's ₹18.22L (+82.17%) — and did it at lower drawdown (14.05% vs 18.59%). F+ classic, the fallback, effectively matched the index. Backtested simulation, not real money."
        >
          <CapTable rows={E2_CAP} />
        </Panel>
      </Reveal>

      {/* ERA 2 — shown second: the 2017–2020 stress test */}
      <EraHead
        eyebrow="Era 2 · 2017–2020"
        title="The stress test"
        standfirst="The era that includes the COVID crash — where the risk machinery earned its keep."
      />

      <Reveal>
        <Panel
          title="Walk-forward — 4 overlapping windows, beat the index 2 / 4"
          sub="The market itself was brutal here: every window includes or borders the COVID crash. Enhanced F+ trailed the index in the two calm early windows but protected capital through the crash — beating the index in the COVID window (W3) and the recovery (W4), with far lower drawdown throughout."
        >
          <WFTable rows={E1_WF} />
          <AlphaStrip rows={E1_WF} />
        </Panel>
      </Reveal>

      <Reveal>
        <Panel
          title="Drawdown — half the pain"
          sub="Full 2017–2020 stress era. Lower is better. Enhanced F+ took 15.08% max drawdown vs F+ classic's 23.27% and the Nifty 500's 38.52%."
        >
          <DrawdownBars />
        </Panel>
      </Reveal>

      {/* signature moment — "The Crash, Scrubbed" */}
      <section className="space-y-4">
        <Reveal>
          <div>
            <SectionEyebrow number="02">The crash, scrubbed</SectionEyebrow>
            <h2 className="mt-2 font-serif text-[clamp(1.75rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.01em] text-ink">
              Watch the de-risk happen
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
              Graded cash (100 / 50 / 25%) cut exposure live, before the bottom — no hindsight.
              Enhanced F+ fell only −13.88% peak-to-trough through the COVID window versus the
              market&apos;s ~−38%.
            </p>
          </div>
        </Reveal>
        <CovidScrub />
      </section>

      <Reveal>
        <Panel
          title="₹10,00,000 simulated — 2017-01-16 → 2020-12-31"
          sub="Through the stress era Enhanced F+ ended ahead of both the index and F+ classic, while taking the least drawdown of the three. Backtested simulation, not real money."
        >
          <CapTable rows={E1_CAP} />
        </Panel>
      </Reveal>

      {/* methodology — the credibility engine, editorial footnotes */}
      <section className="border-t border-hairline pt-8">
        <Reveal>
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
              Methodology &amp; honest caveats
            </p>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
              What this backtest does and does not claim. Read this before trusting any number above.
            </p>
          </div>
        </Reveal>
        <div className="mt-6 grid gap-x-10 gap-y-6 sm:grid-cols-2">
          {CAVEATS.map(([h, b], i) => (
            <Reveal key={h} delay={i * 0.05}>
              <div className="flex gap-4">
                <span className="pt-0.5 font-mono text-[11px] font-semibold text-dim">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="text-xs font-semibold text-ink">{h}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{b}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <p className="px-1 pb-4 text-xs leading-relaxed text-muted">
        For personal research and educational purposes only. Not investment advice. Paper-traded /
        simulated results, not real money. Past simulated performance does not predict future
        results. The operator has not paid for advice and Claude is not registered as an investment
        adviser or research analyst with SEBI.
      </p>
    </div>
  );
}
