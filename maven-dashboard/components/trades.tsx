"use client";

// Trades page — every trade the frozen F+ engine has taken (open + closed), each with
// a day-to-day price sparkline (is the stock going up or down) and the plain-English
// reason F+ entered / exited. All real data from paper_position + prices_eod_adjusted.

import { useState } from "react";
import type { Trade } from "@/lib/types";

const pc = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
const rs = (n: number) => "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
const sign = (n: number) => (n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted");

function Sparkline({ pts, up }: { pts: number[]; up: boolean }) {
  if (pts.length < 2) return <span className="text-[10px] text-dim">no path</span>;
  const w = 130, h = 34, min = Math.min(...pts), max = Math.max(...pts);
  const rng = max - min || 1;
  const d = pts
    .map((p, i) => {
      const x = (i / (pts.length - 1)) * w;
      const y = h - ((p - min) / rng) * (h - 4) - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = up ? "#34d399" : "#fb7185";
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function Field({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-dim">{label}</div>
      <div className={`mt-0.5 font-mono text-sm ${tone ?? "text-ink"}`}>{value}</div>
    </div>
  );
}

function TradeRow({ t }: { t: Trade }) {
  const [open, setOpen] = useState(false);
  const closes = t.series.map((p) => p.close);
  const up = t.trendPct >= 0;
  const value = t.shares * t.currentPrice;
  return (
    <div className="rounded-xl border border-hairline bg-bg/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 p-3 text-left transition-colors hover:bg-panel/50"
      >
        {/* name */}
        <div className="min-w-[150px] flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-ink">{t.ticker}</span>
            <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
              t.status === "open" ? "bg-emerald/15 text-emerald" : "bg-white/5 text-muted"}`}>
              {t.status}
            </span>
          </div>
          <div className="truncate text-xs text-muted">{t.name} · {t.sector}</div>
        </div>
        {/* sparkline (day-to-day) */}
        <div className="flex items-center gap-2">
          <Sparkline pts={closes} up={up} />
          <span className={`font-mono text-xs ${sign(t.trendPct)}`}>{pc(t.trendPct)}</span>
        </div>
        {/* entry -> current */}
        <div className="text-right font-mono text-xs text-muted">
          <div>{rs(t.entryPrice)} → {rs(t.currentPrice)}</div>
          <div className="text-[10px] text-dim">{t.status === "open" ? "entry → latest" : "entry → exit"}</div>
        </div>
        {/* pnl */}
        <div className={`w-20 text-right font-mono text-sm font-semibold ${sign(t.pnlPct)}`}>
          {pc(t.pnlPct)}
        </div>
      </button>

      {open && (
        <div className="space-y-3 border-t border-hairline px-3 pb-3 pt-3">
          {/* WHY F+ bought */}
          <div className="rounded-lg border border-emerald/20 bg-emerald/[0.05] p-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-emerald">Why F+ bought</div>
            <p className="mt-1 text-xs leading-relaxed text-muted">{t.whyEntry}</p>
          </div>
          {/* WHY F+ sold */}
          {t.whyExit && (
            <div className="rounded-lg border border-rose/20 bg-rose/[0.05] p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-rose">Why F+ sold</div>
              <p className="mt-1 text-xs leading-relaxed text-muted">{t.whyExit}</p>
            </div>
          )}
          {/* details */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field label="Entry" value={`${rs(t.entryPrice)}`} />
            <Field label="Entry date" value={t.entryDate} />
            <Field label={t.status === "open" ? "Latest" : "Exit"} value={rs(t.currentPrice)} tone={sign(t.pnlPct)} />
            <Field label={t.status === "open" ? "As of" : "Exit date"} value={t.exitDate ?? "—"} />
            <Field label="Shares" value={t.shares.toFixed(2)} />
            <Field label="Position value" value={rs(value)} />
            <Field label="Exposure at entry" value={`${(t.exposureAtEntry * 100).toFixed(0)}%`} />
            <Field label="P&L" value={pc(t.pnlPct)} tone={sign(t.pnlPct)} />
          </div>
          <p className="text-[11px] text-dim">
            Day-to-day path: {t.series.length} trading days, moved
            <span className={`ml-1 font-mono ${sign(t.trendPct)}`}>{pc(t.trendPct)}</span> since entry
            (real EOD adjusted close).
          </p>
        </div>
      )}
    </div>
  );
}

export function TradesView({ trades }: { trades: Trade[] }) {
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  if (!trades.length) {
    return (
      <div className="rounded-xl border border-hairline bg-bg/40 p-6 text-center text-sm text-muted">
        No trades yet — the paper account has not been incepted, or DATABASE_URL is not set.
      </div>
    );
  }
  const openN = trades.filter((t) => t.status === "open").length;
  const closedN = trades.length - openN;
  const shown = trades.filter((t) => filter === "all" || t.status === filter);
  const tab = (key: "all" | "open" | "closed", label: string) => (
    <button
      type="button"
      onClick={() => setFilter(key)}
      className={`rounded-lg px-3 py-1 text-xs transition-colors ${
        filter === key ? "bg-emerald/15 text-emerald" : "text-muted hover:text-ink"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted">
          {trades.length} trades · <span className="text-emerald">{openN} open</span> ·{" "}
          {closedN} closed. Tap a trade for the price path + why F+ took it.
        </p>
        <div className="flex items-center gap-1 rounded-lg border border-hairline bg-panel/50 p-1">
          {tab("all", "All")}
          {tab("open", "Open")}
          {tab("closed", "Closed")}
        </div>
      </div>
      <div className="space-y-2">
        {shown.map((t) => <TradeRow key={t.id} t={t} />)}
      </div>
    </div>
  );
}
