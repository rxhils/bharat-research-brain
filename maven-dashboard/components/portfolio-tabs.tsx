"use client";

// Book desk — replaces the old three-column grid. One tab per paper book
// (LayoutPill glide between tabs, same spring as the nav), and the active
// book's full composition rendered full-width: header card, equity curve +
// exposure/stats grid, holdings table (compact-responsive). Panel swap is an
// AnimatePresence cross-fade, gated by reduced-motion. All data arrives
// serialized from the server page — nothing is fetched or invented here.

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Card, EquityChart, ExposureGauge, HoldingsTable } from "@/components/client";
import { EASE, LayoutPill, useReducedMotionSafe } from "@/components/motion";
import { fmtDate, inrCompact, pct, plain, signClass } from "@/lib/format";
import type { EquityPoint, ExposureState, Holding, KeyStats, PaperAccount } from "@/lib/types";

export type BookPanelData = {
  /** Raw DB name ("Quant" | "Defensive" | "Concentrated"). */
  name: string;
  /** Public display name ("Enhanced F+" etc.). */
  displayName: string;
  /** Book accent color — must match the race chart line. */
  color: string;
  acct: PaperAccount;
  curve: EquityPoint[];
  exposure: ExposureState;
  stats: KeyStats;
  holdings: Holding[];
};

function Stat({ label, value, tone = "text-ink", hint }: {
  label: string; value: string; tone?: string; hint?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`mt-1 font-mono text-lg tnum ${tone}`}>{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-dim">{hint}</div>}
    </div>
  );
}

const MANDATE: Record<string, string> = {
  Defensive: "Capital protection, smaller drawdowns",
  Concentrated: "Concentrated top-10, higher conviction",
};

export function PortfolioTabs({ books }: { books: BookPanelData[] }) {
  const [activeName, setActiveName] = useState(books[0]?.name ?? "");
  const reduce = useReducedMotionSafe();
  const active = books.find((b) => b.name === activeName) ?? books[0];
  if (!active) return null;

  return (
    <div>
      {/* tab rail */}
      <div
        role="tablist"
        aria-label="Paper books"
        className="scroll-touch mb-4 flex w-fit max-w-full items-center gap-1 overflow-x-auto rounded-full border border-hairline bg-panel/50 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {books.map((b) => {
          const on = b.name === active.name;
          return (
            <button
              key={b.name}
              role="tab"
              aria-selected={on}
              type="button"
              onClick={() => setActiveName(b.name)}
              className="relative shrink-0 whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm transition-colors motion-safe:duration-150 motion-safe:active:scale-[0.97] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60"
              style={{ color: on ? b.color : undefined }}
            >
              {on && (
                <LayoutPill
                  layoutId="book-active-pill"
                  className="absolute inset-0 rounded-full bg-white/[0.06] ring-1 ring-inset ring-white/10"
                />
              )}
              <span className={`relative z-10 flex items-center gap-2 ${on ? "" : "text-muted hover:text-ink"}`}>
                <span
                  aria-hidden
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: b.color, opacity: on ? 1 : 0.45 }}
                />
                {b.displayName}
              </span>
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={active.name}
          initial={reduce ? { opacity: 1 } : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? { opacity: 1 } : { opacity: 0, y: -8 }}
          transition={{ duration: 0.25, ease: EASE }}
          className="space-y-4"
        >
          {/* header card: equity + alpha, full width */}
          <Card className="!p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-dim">{active.displayName}</div>
                <div className="mt-1 flex items-baseline gap-2.5">
                  <span className="font-mono text-3xl tnum text-ink">{inrCompact(active.acct.currentEquity)}</span>
                  <span className={`font-mono text-base tnum ${signClass(active.stats.totalReturnPct)}`}>
                    {pct(active.stats.totalReturnPct)}
                  </span>
                </div>
                <div className="mt-1.5 text-xs text-muted">
                  from {inrCompact(active.acct.startingCapital)} · alpha vs Nifty 500
                  <span className={`ml-1 font-mono tnum ${signClass(active.stats.alphaVsNifty500Pct)}`}>
                    {pct(active.stats.alphaVsNifty500Pct)}
                  </span>
                </div>
              </div>
              <span
                className="shrink-0 rounded-md px-2 py-1 text-[10px]"
                style={{ background: `${active.color}1A`, color: active.color }}
              >
                {active.acct.engineVersion}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-dim">
              <span>
                {active.stats.daysLive > 0
                  ? `Paper-traded since ${fmtDate(active.acct.inceptionDate)}`
                  : `Live from ${fmtDate(active.acct.inceptionDate)} — awaiting first session`}
              </span>
              <span className="rounded-md px-2 py-0.5" style={{ background: `${active.color}1A`, color: active.color }}>
                {MANDATE[active.name] ?? "Index-like return, ~half the drawdown"}
              </span>
            </div>
          </Card>

          {/* full-width detail grid: chart spans 2, exposure + stats stack right */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Card title="Equity curve" sub={`${active.displayName} vs Nifty 500 TRI`} className="lg:col-span-2">
              <EquityChart data={active.curve} seriesName={active.displayName} accent={active.color} />
            </Card>
            <div className="space-y-4">
              <Card title="Exposure" sub="invested vs cash">
                <ExposureGauge state={active.exposure} />
              </Card>
              <Card title="Key stats" sub="risk-first" delay={60}>
                <div className="grid grid-cols-2 gap-4">
                  <Stat label="Max drawdown" value={plain(active.stats.maxDrawdownPct) + "%"} tone="text-amber" hint="the headline metric" />
                  <Stat label="Sharpe" value={plain(active.stats.sharpe)} />
                  <Stat label="Holdings" value={String(active.stats.holdings)} hint="+ cash sleeve" />
                  <Stat label="Win rate" value={plain(active.stats.winRatePct, 0) + "%"} />
                </div>
              </Card>
            </div>
          </div>

          <Card title="Holdings" sub={`${active.stats.holdings} positions + cash`} delay={80}>
            <HoldingsTable rows={active.holdings} compact />
          </Card>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
