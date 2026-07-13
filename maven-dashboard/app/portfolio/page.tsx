import {
  getAccount, getEquityCurve, getExposure, getHoldings, getKeyStats, getLivePortfolios,
} from "@/lib/data";
import { Card, EquityChart, ExposureGauge, HoldingsTable } from "@/components/client";
import { fmtDate, inrCompact, pct, plain, signClass } from "@/lib/format";
import type { EquityPoint, ExposureState, Holding, KeyStats, PaperAccount } from "@/lib/types";

export const dynamic = "force-dynamic";

// "Quant" is shown as its strategy name on the public site.
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

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

type Panel = {
  name: string; acct: PaperAccount; curve: EquityPoint[];
  exposure: ExposureState; stats: KeyStats; holdings: Holding[];
};

/** One live paper book — its own headline, curve, exposure, stats, holdings. */
function PortfolioPanel({ name, acct, curve, exposure, stats, holdings }: Panel) {
  const isDefensive = name === "Defensive";
  const dn = displayName(name);
  return (
    <div className="space-y-4">
      <Card className="!p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-dim">{dn}</div>
            <div className="mt-1 flex items-baseline gap-2.5">
              <span className="font-mono text-3xl tnum text-ink">{inrCompact(acct.currentEquity)}</span>
              <span className={`font-mono text-base tnum ${signClass(stats.totalReturnPct)}`}>{pct(stats.totalReturnPct)}</span>
            </div>
            <div className="mt-1.5 text-xs text-muted">
              from {inrCompact(acct.startingCapital)} · alpha vs Nifty 500
              <span className={`ml-1 font-mono tnum ${signClass(stats.alphaVsNifty500Pct)}`}>{pct(stats.alphaVsNifty500Pct)}</span>
            </div>
          </div>
          <span className="shrink-0 rounded-md bg-emerald/10 px-2 py-1 text-[10px] text-emerald">{acct.engineVersion}</span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-dim">
          <span>{stats.daysLive > 0
            ? `Paper-traded since ${fmtDate(acct.inceptionDate)}`
            : `Live from ${fmtDate(acct.inceptionDate)} — awaiting first session`}</span>
          <span className="rounded-md bg-emerald/10 px-2 py-0.5 text-emerald">
            {isDefensive
              ? "Capital protection, smaller drawdowns"
              : name === "Concentrated"
                ? "Concentrated top-10, higher conviction"
                : "Index-like return, ~half the drawdown"}
          </span>
        </div>
      </Card>

      <Card title="Equity curve" sub={`${dn} vs Nifty 500 TRI`} delay={60}>
        <EquityChart data={curve} />
      </Card>

      <Card title="Exposure" sub="cash sleeve" delay={100}>
        <ExposureGauge state={exposure} />
      </Card>

      <Card title="Key stats" sub="risk-first" delay={140}>
        <div className="grid grid-cols-2 gap-4">
          <Stat label="Max drawdown" value={plain(stats.maxDrawdownPct) + "%"} tone="text-amber" hint="the headline metric" />
          <Stat label="Sharpe" value={plain(stats.sharpe)} />
          <Stat label="Holdings" value={String(stats.holdings)} hint="+ cash sleeve" />
          <Stat label="Win rate" value={plain(stats.winRatePct, 0) + "%"} />
        </div>
      </Card>

      <Card title="Holdings" sub={`${stats.holdings} positions + cash`} delay={180}>
        <HoldingsTable rows={holdings} />
      </Card>
    </div>
  );
}

export default async function Portfolio() {
  const ports = await getLivePortfolios();
  const panels = await Promise.all(
    ports.map(async (p): Promise<Panel> => {
      const [acct, curve, exposure, stats, holdings] = await Promise.all([
        getAccount(p.id), getEquityCurve(p.id), getExposure(p.id), getKeyStats(p.id), getHoldings(p.id),
      ]);
      return { name: p.name, acct, curve, exposure, stats, holdings };
    }),
  );

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] uppercase tracking-wider text-dim">Paper portfolios</div>
        <h1 className="mt-1 font-serif text-2xl text-ink">Three live books, three engines.</h1>
        <p className="mt-1 text-sm text-muted">
          Enhanced F+ trades vol-adjusted momentum; Defensive trades low-volatility with sooner, harder
          de-risking; Concentrated runs a top-10 high-conviction book. All three ₹10L paper, side by side.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {panels.map((panel) => <PortfolioPanel key={panel.name} {...panel} />)}
      </div>

      <p className="px-1 pt-2 text-xs text-dim">
        Research tool. Not investment advice. Paper-traded results, not real money.
      </p>
    </div>
  );
}
