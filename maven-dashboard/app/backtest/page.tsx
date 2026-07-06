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
 */

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartReveal, useReducedMotionSafe } from "@/components/motion";

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
const AMBER = "#fbbf24";
const ROSE = "#fb7185";

/* ---------- tiny self-contained formatters ---------- */
const pc = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
const inr = (n: number) =>
  "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
const sign = (n: number) => (n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted");

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

const COVID_TRACE = [
  { date: "2020-02-11", exp: 100, note: "Fully invested — pre-crash" },
  { date: "2020-03-04", exp: 50, note: "Regime risk-off — first cut" },
  { date: "2020-03-12", exp: 25, note: "Deep risk-off — exposure floor" },
  { date: "2020-06-03", exp: 50, note: "Recovery — stepping back in" },
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

function Panel({ title, sub, children }: { title?: string; sub?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-hairline bg-panel/50 p-5 sm:p-6">
      {title && (
        <header className="mb-4">
          <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>
          {sub && <p className="mt-1 text-xs leading-relaxed text-muted">{sub}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-hairline bg-bg/40 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 font-mono text-xl font-semibold ${tone ?? "text-ink"}`}>{value}</div>
    </div>
  );
}

const tipStyle = {
  background: "#0a0b0d",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  fontSize: 12,
};

/* grouped Enhanced F+ vs index return per walk-forward window */
function WindowReturns({ rows }: { rows: typeof E1_WF }) {
  const draw = useBarDrawOnce();
  const data = rows.map((r) => ({ w: r.w, "Enhanced F+": r.ret, "Nifty 500": r.idx }));
  return (
    <ChartReveal delay={0.1}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="w" tick={{ fill: SLATE, fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: SLATE, fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip contentStyle={tipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Enhanced F+" fill={EMERALD} radius={[3, 3, 0, 0]} maxBarSize={26} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
          <Bar dataKey="Nifty 500" fill={SLATE} radius={[3, 3, 0, 0]} maxBarSize={26} isAnimationActive={draw} animationDuration={600} animationEasing="ease-out" />
        </BarChart>
      </ResponsiveContainer>
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
            <th className="py-2 pr-3 font-medium">Enhanced F+ return</th>
            <th className="py-2 pr-3 font-medium">Sharpe</th>
            <th className="py-2 pr-3 font-medium">Max DD</th>
            <th className="py-2 pr-3 font-medium">Trades</th>
            <th className="py-2 pr-3 font-medium">Nifty 500</th>
            <th className="py-2 pr-3 font-medium">Alpha</th>
            <th className="py-2 pr-0 font-medium">Beat?</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((r) => (
            <tr key={r.w} className="border-b border-hairline/60">
              <td className="py-2 pr-3 font-sans text-xs text-ink">
                <span className="font-semibold">{r.w}</span>{" "}
                <span className="text-muted">{r.period}</span>
              </td>
              <td className={`py-2 pr-3 ${sign(r.ret)}`}>{pc(r.ret)}</td>
              <td className={`py-2 pr-3 ${sign(r.sharpe)}`}>{r.sharpe.toFixed(2)}</td>
              <td className="py-2 pr-3 text-amber">{r.dd.toFixed(2)}%</td>
              <td className="py-2 pr-3 text-muted">{r.trades}</td>
              <td className={`py-2 pr-3 ${sign(r.idx)}`}>{pc(r.idx)}</td>
              <td className={`py-2 pr-3 ${sign(r.alpha)}`}>{pc(r.alpha)}</td>
              <td className="py-2 pr-0">
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
            <th className="py-2 pr-3 font-medium">₹10L grew to</th>
            <th className="py-2 pr-3 font-medium">Return</th>
            <th className="py-2 pr-3 font-medium">Max DD</th>
            <th className="py-2 pr-3 font-medium">Sharpe</th>
            <th className="py-2 pr-0 font-medium">Trades</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((r) => {
            const hi = r.accent === EMERALD;
            return (
              <tr key={r.name} className={`border-b border-hairline/60 ${hi ? "bg-emerald/[0.04]" : ""}`}>
                <td className={`py-2 pr-3 font-sans text-xs ${hi ? "font-semibold text-emerald" : "text-ink"}`}>{r.name}</td>
                <td className={`py-2 pr-3 ${hi ? "text-emerald" : "text-ink"}`}>{inr(r.final)}</td>
                <td className={`py-2 pr-3 ${sign(r.ret)}`}>{pc(r.ret)}</td>
                <td className="py-2 pr-3 text-amber">{r.dd.toFixed(2)}%</td>
                <td className="py-2 pr-3 text-muted">{r.sharpe === null ? "—" : r.sharpe.toFixed(2)}</td>
                <td className="py-2 pr-0 text-muted">{r.trades ?? "—"}</td>
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
    <div className="space-y-6 pt-6">
      {/* hero */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-emerald/30 bg-emerald/10 px-2.5 py-1 text-[11px] font-medium text-emerald">
            Backtested — not a live track record
          </span>
          <span className="rounded-full border border-hairline bg-panel/60 px-2.5 py-1 font-mono text-[11px] text-muted">
            frozen Enhanced F+ · commit 6ced078
          </span>
        </div>
        {/* serif h1 matches the house headline voice (portfolio/strategies pages) */}
        <h1 className="text-balance font-serif text-2xl text-ink sm:text-3xl">
          Enhanced F+ Backtest — the proof
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted">
          The engine running the paper account, tested two ways: across the 2021–2026 bull run and
          through the 2017–2020 stress era (the COVID crash). No-lookahead walk-forward plus a
          ₹10,00,000 capital simulation against the Nifty 500 Total-Return Index. F+ classic is shown
          alongside as the locked fallback.
        </p>
      </header>

      {/* verdict */}
      <Panel
        title="The headline"
        sub="Enhanced F+ beat the Nifty 500 over 2021–26 at lower drawdown, and fell only ~14% through the COVID window versus the market's ~38%. Backtested results — the durable claim is the return-vs-drawdown edge, not the absolute percentage."
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="2021–26 return" value="+129.97%" tone="text-emerald" />
          <Stat label="vs Nifty 500 TRI" value="+82.17%" tone="text-muted" />
          <Stat label="Max drawdown" value="14.05%" tone="text-emerald" />
          <Stat label="vs Nifty 500 DD" value="18.59%" tone="text-muted" />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="COVID-window DD" value="13.88%" tone="text-emerald" />
          <Stat label="vs market crash" value="~38%" tone="text-muted" />
          <Stat label="Bull windows beaten" value="4 / 4" tone="text-emerald" />
          <Stat label="2021–26 Sharpe" value="0.95" tone="text-emerald" />
        </div>
      </Panel>

      {/* ERA 1 — shown first: the 2021–2026 bull run */}
      <div className="flex items-center gap-3 pt-2">
        <div className="h-px flex-1 bg-hairline" />
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
          Era 1 · 2021–2026 bull run
        </span>
        <div className="h-px flex-1 bg-hairline" />
      </div>

      <Panel
        title="Walk-forward — beat the index 4 / 4"
        sub="Every window cleared the Nifty 500 TRI on return, with positive alpha and a Sharpe above 1.0 in three of four windows. Backtested, no-lookahead."
      >
        <WFTable rows={E2_WF} />
        <div className="mt-5">
          <WindowReturns rows={E2_WF} />
        </div>
      </Panel>

      <Panel
        title="₹10,00,000 simulated — 2021-06-01 → 2026-05-26"
        sub="Enhanced F+ grew ₹10L to ₹22.99L (+129.97%) versus the index's ₹18.22L (+82.17%) — and did it at lower drawdown (14.05% vs 18.59%). F+ classic, the fallback, effectively matched the index. Backtested simulation, not real money."
      >
        <CapTable rows={E2_CAP} />
      </Panel>

      {/* ERA 2 — shown second: the 2017–2020 stress test */}
      <div className="flex items-center gap-3 pt-2">
        <div className="h-px flex-1 bg-hairline" />
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
          Era 2 · 2017–2020 stress test
        </span>
        <div className="h-px flex-1 bg-hairline" />
      </div>

      <Panel
        title="Walk-forward — 4 overlapping windows, beat the index 2 / 4"
        sub="The market itself was brutal here: every window includes or borders the COVID crash. Enhanced F+ trailed the index in the two calm early windows but protected capital through the crash — beating the index in the COVID window (W3) and the recovery (W4), with far lower drawdown throughout."
      >
        <WFTable rows={E1_WF} />
        <div className="mt-5">
          <WindowReturns rows={E1_WF} />
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Drawdown — half the pain"
          sub="Full 2017–2020 stress era. Lower is better. Enhanced F+ took 15.08% max drawdown vs F+ classic's 23.27% and the Nifty 500's 38.52%."
        >
          <DrawdownBars />
        </Panel>

        <Panel
          title="The COVID de-risk, step by step"
          sub="Graded cash (100 / 50 / 25%) cut exposure live, before the bottom — no hindsight. Enhanced F+ fell only −13.88% peak-to-trough through the COVID window versus the market's ~−38%."
        >
          <ol className="relative space-y-3 border-l border-hairline pl-5">
            {COVID_TRACE.map((s) => (
              <li key={s.date} className="relative">
                <span
                  className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full ring-2 ring-bg"
                  style={{ background: s.exp >= 100 ? SLATE : s.exp <= 25 ? ROSE : AMBER }}
                />
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-xs text-muted">{s.date}</span>
                  <span className="font-mono text-sm font-semibold text-ink">{s.exp}% invested</span>
                </div>
                <p className="text-xs text-muted">{s.note}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <Panel
        title="₹10,00,000 simulated — 2017-01-16 → 2020-12-31"
        sub="Through the stress era Enhanced F+ ended ahead of both the index and F+ classic, while taking the least drawdown of the three. Backtested simulation, not real money."
      >
        <CapTable rows={E1_CAP} />
      </Panel>

      {/* methodology */}
      <Panel
        title="Methodology & honest caveats"
        sub="What this backtest does and does not claim. Read this before trusting any number above."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {CAVEATS.map(([h, b]) => (
            <div key={h} className="rounded-xl border border-hairline bg-bg/40 p-4">
              <div className="text-xs font-semibold text-ink">{h}</div>
              <p className="mt-1 text-xs leading-relaxed text-muted">{b}</p>
            </div>
          ))}
        </div>
      </Panel>

      <p className="px-1 text-xs leading-relaxed text-muted">
        For personal research and educational purposes only. Not investment advice. Paper-traded /
        simulated results, not real money. Past simulated performance does not predict future
        results. The operator has not paid for advice and Claude is not registered as an investment
        adviser or research analyst with SEBI.
      </p>
    </div>
  );
}
