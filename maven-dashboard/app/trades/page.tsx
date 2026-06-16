import { getTrades } from "@/lib/data";
import { Card } from "@/components/client";
import { TradesView } from "@/components/trades";

export const dynamic = "force-dynamic";

export default async function Trades() {
  const trades = await getTrades();

  return (
    <div className="space-y-4 pt-2">
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
