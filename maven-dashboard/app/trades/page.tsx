import type { Metadata } from "next";
import type { ReactNode } from "react";
import { getDataStatus, getLivePortfolios, getTrades } from "@/lib/data";
import type { Trade } from "@/lib/types";
import { Card } from "@/components/client";
import { GlassPanel } from "@/components/glass-panel";
import { CountUp, SectionEyebrow } from "@/components/motion";
import { EngineJumpNav, TapePath, TradesView } from "@/components/trades";

export const dynamic = "force-dynamic";

const title = "Research Trade Decision History and Rationale";
const description =
  "Review timestamped public model trade decisions with rationale, evidence provenance, strategy context, real end-of-day price data, and outcome tracking.";
const url = "https://www.trymaven.in/trades";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

// "Quant" is shown as its strategy name on the public site.
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

// Stable anchor id per engine section (for the sticky jump-nav).
const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

const pc = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
const sign = (n: number) => (n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted");

/** Aggregate paper-P&L path for the hero tape: for each trading date, the mean
 *  of every trade's %-move-from-entry on that date, from the trades' real EOD
 *  series. Downsampled to ≤90 points. Empty when there is no data. */
function buildTape(trades: Trade[]): number[] {
  const byDate = new Map<string, { sum: number; n: number }>();
  for (const t of trades) {
    if (!t.entryPrice) continue;
    for (const p of t.series) {
      const rel = (p.close / t.entryPrice - 1) * 100;
      const cur = byDate.get(p.date) ?? { sum: 0, n: 0 };
      cur.sum += rel;
      cur.n += 1;
      byDate.set(p.date, cur);
    }
  }
  const pts = [...byDate.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([, v]) => v.sum / v.n);
  if (pts.length <= 90) return pts;
  const step = (pts.length - 1) / 89;
  return Array.from({ length: 90 }, (_, i) => pts[Math.round(i * step)]);
}

/** One scoreboard stat: mono tnum numeral over an 11px caption. */
function Stat({ label, caption, children }: { label: string; caption?: string; children: ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-dim">{label}</div>
      <div className="mt-1 font-mono text-[clamp(1.5rem,1rem+1.5vw,2.25rem)] font-semibold leading-none tnum text-ink">
        {children}
      </div>
      {caption && <div className="mt-1 text-[11px] text-dim">{caption}</div>}
    </div>
  );
}

export default async function Trades() {
  const ports = await getLivePortfolios();
  const status = await getDataStatus();
  const sections = await Promise.all(
    ports.map(async (p) => ({
      name: p.name,
      label: displayName(p.name),
      trades: await getTrades(p.id),
    })),
  );

  // Scoreboard stats — computed here, server-side, from the sections data
  // already fetched. Honest placeholders when empty; never fabricated numbers.
  const all = sections.flatMap((s) => s.trades);
  const open = all.filter((t) => t.status === "open");
  const closed = all.filter((t) => t.status === "closed");
  const wins = closed.filter((t) => t.pnlPct > 0).length;
  const winRate = closed.length ? (wins / closed.length) * 100 : null;
  const avgPnl = all.length ? all.reduce((s, t) => s + t.pnlPct, 0) / all.length : null;
  const best = all.length
    ? all.reduce((b, t) => (t.pnlPct > b.pnlPct ? t : b), all[0])
    : null;
  const tape = buildTape(all);

  return (
    <div className="space-y-4 pt-2">
      {/* hero scoreboard — "The Tape" */}
      <div className="relative">
        {/* radial emerald glow bled from behind the glass (light-source trick) */}
        <div
          aria-hidden
          className="pointer-events-none absolute -inset-x-10 -top-12 bottom-0 -z-10 bg-[radial-gradient(60%_60%_at_50%_0%,rgba(52,211,153,0.12),transparent_70%)]"
        />
        <GlassPanel glow="emerald" noise innerClassName="p-5 sm:p-6">
          <SectionEyebrow>Trade log</SectionEyebrow>
          <h1 className="mt-2 font-serif text-[clamp(1.875rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.02em] text-ink">
            Every trade, with its why.
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Each position is a mechanical decision from real end-of-day prices — logged with its
            entry thesis, exit trigger, and full price path.
          </p>

          {/* 4-stat band */}
          <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4">
            <Stat label="Open positions" caption={all.length ? `of ${all.length} trades` : "awaiting data"}>
              {all.length ? <CountUp to={open.length} decimals={0} /> : <span className="text-dim">—</span>}
            </Stat>
            <Stat
              label="Closed win rate"
              caption={closed.length ? `${wins} of ${closed.length} closed` : "no closed trades yet"}
            >
              {winRate !== null ? <CountUp to={winRate} suffix="%" decimals={0} /> : <span className="text-dim">—</span>}
            </Stat>
            <Stat label="Avg P&L" caption={all.length ? "incl. open (unrealized)" : "awaiting data"}>
              {avgPnl !== null ? (
                <span className={sign(avgPnl)}>
                  <CountUp to={avgPnl} prefix={avgPnl > 0 ? "+" : ""} suffix="%" decimals={2} />
                </span>
              ) : (
                <span className="text-dim">—</span>
              )}
            </Stat>
            <Stat
              label="Best trade"
              caption={best ? (best.status === "open" ? `${best.ticker} · open (unrealized)` : best.ticker) : "awaiting data"}
            >
              {best ? (
                <span className="text-gold-soft">
                  <CountUp to={best.pnlPct} prefix={best.pnlPct > 0 ? "+" : ""} suffix="%" decimals={2} />
                </span>
              ) : (
                <span className="text-dim">—</span>
              )}
            </Stat>
          </div>

          {/* aggregate paper-P&L path, drawn from the real trade series */}
          {tape.length > 1 && <TapePath pts={tape} className="mt-6" />}

          {/* provenance — quiet mono footnote, not a banner */}
          <div className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-hairline pt-3 font-mono text-[11px] text-dim">
            <span aria-hidden className="brand-motion inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald" />
            <span>real data</span>
            <span>· {status.source}</span>
            <span>· {status.priceRows.toLocaleString("en-IN")} price rows · {status.stocks} stocks</span>
            <span>· latest <span className="tnum text-muted">{status.latestPrice}</span></span>
          </div>
        </GlassPanel>
      </div>

      {sections.length > 1 && (
        <EngineJumpNav items={sections.map((s) => ({ id: slug(s.label), label: s.label }))} />
      )}

      {sections.map((s) => (
        <div key={s.name} id={slug(s.label)} className="scroll-mt-20">
          <Card
            title={`${s.label} trades`}
            sub={`every position ${s.label} has taken — price path + entry/exit logic`}
          >
            <TradesView trades={s.trades} engineLabel={s.label} />
          </Card>
        </div>
      ))}

      <p className="px-1 text-xs text-dim">
        Every trade is a mechanical decision from real end-of-day prices (no discretion) — Enhanced F+
        scores on vol-adjusted momentum, Defensive on low volatility, and Concentrated runs the Enhanced F+
        engine narrowed to its top 10 names. The sparkline is the stock&apos;s real adjusted close, entry →
        today. Research tool, not investment advice.
      </p>
    </div>
  );
}
