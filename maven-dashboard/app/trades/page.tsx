import { getDataStatus, getLivePortfolios, getTrades } from "@/lib/data";
import { Card } from "@/components/client";
import { TradesView } from "@/components/trades";

export const dynamic = "force-dynamic";

// "Quant" is shown as its strategy name on the public site.
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

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

  return (
    <div className="space-y-4 pt-2">
      {/* page header — same eyebrow + serif h1 rhythm as /portfolio */}
      <div>
        <div className="text-[11px] uppercase tracking-wider text-dim">Trade log</div>
        <h1 className="mt-1 font-serif text-2xl text-ink">Every trade, with its why.</h1>
      </div>

      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-emerald/20 bg-emerald/[0.04] px-3 py-2 text-[11px] text-muted">
        <span className="font-medium text-emerald">● Real data</span>
        <span>· {status.source}</span>
        <span>· {status.priceRows.toLocaleString("en-IN")} price rows · {status.stocks} stocks</span>
        <span>· latest <span className="font-mono text-ink">{status.latestPrice}</span></span>
      </div>

      {sections.map((s) => (
        <Card key={s.name} title={`${s.label} trades`} sub={`every position ${s.label} has taken — price path + why`}>
          <TradesView trades={s.trades} engineLabel={s.label} />
        </Card>
      ))}

      <p className="px-1 text-xs text-dim">
        Every trade is a mechanical decision from real end-of-day prices (no discretion) — Enhanced F+
        scores on vol-adjusted momentum, Defensive on low volatility. The sparkline is the stock&apos;s
        real adjusted close, entry → today. Research tool, not investment advice.
      </p>
    </div>
  );
}
