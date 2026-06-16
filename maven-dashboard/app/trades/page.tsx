import { getDataStatus, getTrades } from "@/lib/data";
import { Card } from "@/components/client";
import { TradesView } from "@/components/trades";

export const dynamic = "force-dynamic";

export default async function Trades() {
  const [trades, status] = await Promise.all([getTrades(), getDataStatus()]);

  return (
    <div className="space-y-4 pt-2">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-emerald/20 bg-emerald/[0.04] px-3 py-2 text-[11px] text-muted">
        <span className="font-medium text-emerald">● Real data</span>
        <span>· {status.source}</span>
        <span>· {status.priceRows.toLocaleString("en-IN")} price rows · {status.stocks} stocks</span>
        <span>· latest <span className="font-mono text-ink">{status.latestPrice}</span></span>
      </div>
      <Card title="Trades" sub="every position F+ has taken — price path + why">
        <TradesView trades={trades} />
      </Card>
      <p className="px-1 text-xs text-dim">
        Every trade is a mechanical F+ decision from real end-of-day prices (no discretion). The
        sparkline is the stock's real adjusted close, entry → today. Research tool, not investment
        advice.
      </p>
    </div>
  );
}
