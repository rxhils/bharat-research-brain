import { getAccount, getEquityCurve, getExposure, getHoldings, getKeyStats } from "@/lib/data";
import { Card, EquityChart, ExposureGauge, HoldingsTable } from "@/components/client";
import { fmtDate, inrCompact, pct, plain, signClass } from "@/lib/format";

export const dynamic = "force-dynamic";

function Stat({ label, value, tone = "text-ink", hint }: {
  label: string; value: string; tone?: string; hint?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`mt-1 font-mono text-xl tnum ${tone}`}>{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-dim">{hint}</div>}
    </div>
  );
}

export default async function Portfolio() {
  const [acct, curve, exposure, stats, holdings] = await Promise.all([
    getAccount(), getEquityCurve(), getExposure(), getKeyStats(), getHoldings(),
  ]);

  return (
    <div className="space-y-4">
      {/* Headline */}
      <Card className="!p-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-dim">Paper portfolio value</div>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="font-mono text-4xl tnum text-ink">{inrCompact(acct.currentEquity)}</span>
              <span className={`font-mono text-lg tnum ${signClass(stats.totalReturnPct)}`}>{pct(stats.totalReturnPct)}</span>
            </div>
            <div className="mt-2 text-xs text-muted">
              from {inrCompact(acct.startingCapital)} · alpha vs Nifty 500
              <span className={`ml-1 font-mono tnum ${signClass(stats.alphaVsNifty500Pct)}`}>{pct(stats.alphaVsNifty500Pct)}</span>
            </div>
          </div>
          <div className="text-right text-xs text-dim">
            <div>Paper-traded since {fmtDate(acct.inceptionDate)}</div>
            <div className="mt-0.5">{stats.daysLive} days live · {acct.engineVersion}</div>
            <div className="mt-2 inline-block rounded-md bg-emerald/10 px-2 py-1 text-[11px] text-emerald">
              Goal: index-like return, ~half the drawdown
            </div>
          </div>
        </div>
      </Card>

      {/* Curve + exposure */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Equity curve" sub="F+ vs Nifty 500 TRI" className="lg:col-span-2" delay={60}>
          <EquityChart data={curve} />
        </Card>
        <Card title="Exposure" sub="cash sleeve" delay={120}>
          <ExposureGauge state={exposure} />
        </Card>
      </div>

      {/* Key stats — RISK first */}
      <Card title="Key stats" sub="risk-first" delay={160}>
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
          <Stat label="Max drawdown" value={plain(stats.maxDrawdownPct) + "%"} tone="text-amber" hint="the headline metric" />
          <Stat label="Sharpe" value={plain(stats.sharpe)} tone="text-ink" />
          <Stat label="Holdings" value={String(stats.holdings)} tone="text-ink" hint="+ cash sleeve" />
          <Stat label="Win rate" value={plain(stats.winRatePct, 0) + "%"} tone="text-ink" />
        </div>
      </Card>

      {/* Holdings */}
      <Card title="Holdings" sub={`${stats.holdings} positions + cash`} delay={200}>
        <HoldingsTable rows={holdings} />
      </Card>

      <p className="px-1 pt-2 text-xs text-dim">
        Research tool. Not investment advice. Paper-traded results, not real money.
      </p>
    </div>
  );
}
