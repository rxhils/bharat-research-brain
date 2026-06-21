import { getABReadout, getEquityCurve } from "@/lib/data";
import { ABChart, Card } from "@/components/client";
import { AgentExplainer } from "@/components/agents";

export const dynamic = "force-dynamic";

export default async function Brain() {
  const [curve, readout] = await Promise.all([getEquityCurve(), getABReadout()]);

  return (
    <div className="space-y-4 pt-2">
      {/* Agents on top — the main thing: what each one does, in plain English */}
      <Card title="Agents" sub="the system, in plain English — tap any agent">
        <AgentExplainer />
      </Card>

      {/* The honest live record: the frozen F+ paper book vs the index */}
      <Card title="Is it working?" sub="Enhanced F+ live paper record vs Nifty 500 TRI" delay={80}>
        <ABChart data={curve} readout={readout} />
      </Card>

      <p className="px-1 pt-1 text-xs text-dim">
        The frozen Enhanced F+ engine decides the portfolio from real end-of-day prices. The research
        agents above are built but offline and do NOT affect the live picks. Research tool, not
        investment advice.
      </p>
    </div>
  );
}
