"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type {
  ABReadout, AgentBoard as TBoard, AgentRun, EquityPoint, ExposureState,
  Holding, ScoreRow,
} from "@/lib/types";
import { ago, fmtDate, inrCompact, pct, plain, signClass } from "@/lib/format";

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------
export function Nav() {
  const path = usePathname();
  const tab = (href: string, label: string) => {
    const active = path === href;
    return (
      <Link
        href={href}
        className={`rounded-lg px-3.5 py-1.5 text-sm transition-colors ${
          active ? "bg-emerald/10 text-emerald" : "text-muted hover:text-ink"
        }`}
      >
        {label}
      </Link>
    );
  };
  return (
    <nav className="sticky top-0 z-30 -mx-5 mb-2 flex items-center justify-between border-b border-hairline bg-bg/85 px-5 py-4 backdrop-blur-md sm:-mx-8 sm:px-8">
      <Link href="/" className="flex items-center gap-2.5">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-emerald/15 font-mono text-sm text-emerald">M</span>
        <span className="text-sm tracking-[0.2em] text-muted">MAVEN</span>
        <span className="rounded-full border border-amber/30 bg-amber/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber">
          demo data
        </span>
      </Link>
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 rounded-xl border border-hairline bg-panel/50 p-1">
          {tab("/", "Portfolio")}
          {tab("/brain", "Brain")}
        </div>
        <Link
          href="/backtest"
          className={`rounded-lg border px-3.5 py-1.5 text-sm transition-colors ${
            path === "/backtest"
              ? "border-emerald/50 bg-emerald/15 text-emerald"
              : "border-emerald/30 text-emerald hover:bg-emerald/10"
          }`}
        >
          ★ F+ Backtest
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
  return (
    <section
      className={`animate-fadeUp rounded-xl2 border border-border bg-panel/60 p-5 ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {title && (
        <div className="mb-4 flex items-baseline justify-between gap-3">
          <h3 className="text-[13px] font-medium tracking-wide text-ink">{title}</h3>
          {sub && <span className="text-xs text-dim">{sub}</span>}
        </div>
      )}
      {children}
    </section>
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

export function EquityChart({ data }: { data: EquityPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(d) => fmtDate(d).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(v) => inrCompact(v)} width={56} axisLine={false} tickLine={false} domain={["dataMin", "dataMax"]} />
        <Tooltip content={<ChartTip />} />
        <Line type="monotone" dataKey="nifty500" name="Nifty 500 TRI" stroke="#5a616a" strokeWidth={1.5} dot={false} />
        <Line type="monotone" dataKey="fplus" name="F+" stroke="#34d399" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ABChart({ data, readout }: { data: EquityPoint[]; readout: ABReadout }) {
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
      <ResponsiveContainer width="100%" height={210}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(d) => fmtDate(d).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#5a616a", fontSize: 11 }} tickFormatter={(v) => inrCompact(v)} width={56} axisLine={false} tickLine={false} domain={["dataMin", "dataMax"]} />
          <Tooltip content={<ChartTip />} />
          <Line type="monotone" dataKey="fplus" name="F+ · mechanical" stroke="#34d399" strokeWidth={2} dot={false} />
          {readout.hasAgentic && (
            <Line type="monotone" dataKey="fplusAgentic" name="F+ · agentic" stroke="#fbbf24" strokeWidth={2} dot={false} />
          )}
        </LineChart>
      </ResponsiveContainer>
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
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-2xl tnum text-emerald">{invested}%</span>
        <span className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${riskOff ? "bg-amber/12 text-amber" : "bg-emerald/12 text-emerald"}`}>
          {riskOff ? "Risk-off" : "Risk-on"}
        </span>
      </div>
      <div className="flex h-3 overflow-hidden rounded-full bg-white/5">
        <div className="bg-emerald" style={{ width: `${invested}%` }} />
        <div className="bg-white/10" style={{ width: `${state.cashPct}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-muted">
        <span>Invested {invested}%</span>
        <span>Cash {state.cashPct}%</span>
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
  const head = (k: SortKey, label: string, extra = "") => (
    <th
      className={`cursor-pointer select-none py-2 text-xs font-medium text-dim hover:text-ink ${extra}`}
      onClick={() => { if (key === k) { setDir((d) => (d === 1 ? -1 : 1)); } else { setKey(k); setDir(-1); } }}
    >
      {label}{key === k ? (dir === 1 ? " up" : " dn") : ""}
    </th>
  );
  return (
    <div className="overflow-x-auto">
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
        <tbody className="tnum">
          {sorted.map((r) => (
            <tr key={r.isin} className={`border-b border-hairline/60 ${r.isCash ? "text-muted" : "text-ink"}`}>
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
          className="rounded-lg border border-border bg-panel2 px-3 py-1.5 text-sm text-ink outline-none"
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
            onClick={() => setSector(sec)}
            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${sector === sec ? "bg-emerald/12 text-emerald" : "bg-white/4 text-dim hover:text-muted"}`}
          >
            {sec}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
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
const DOT: Record<AgentRun["status"], string> = {
  done: "bg-emerald", running: "bg-amber animate-pulseDot",
  waiting: "bg-white/30", offline: "bg-rose/60", error: "bg-rose",
};
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
        <span className={`h-2 w-2 rounded-full ${DOT[a.status]}`} />
        <span className="text-sm text-ink">{a.agentName}</span>
        <span className="ml-auto font-mono text-[11px] text-dim">
          {a.status === "offline" ? "offline" : a.durationMs ? `${(a.durationMs / 1000).toFixed(1)}s` : running ? "running" : ""}
        </span>
      </div>
      <p className="mt-1.5 text-xs text-muted">{a.headlineOutput}</p>
      {running && (
        <div className="mt-2">
          <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
            <div className="h-full bg-amber transition-all" style={{ width: `${pctDone}%` }} />
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
        <span className={`h-2 w-2 rounded-full ${board.inProgress ? "bg-amber animate-pulseDot" : "bg-emerald"}`} />
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
        These scores feed <span className="text-muted">F+</span> (frozen risk engine) — agents produce signals, F+ decides the portfolio.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
export function Empty({ msg = "No data yet — paper trade starts when the engine goes live." }: { msg?: string }) {
  return <div className="grid place-items-center rounded-xl2 border border-dashed border-border py-10 text-sm text-dim">{msg}</div>;
}
