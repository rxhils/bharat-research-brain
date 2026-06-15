import { getABReadout, getEquityCurve, getScores } from "@/lib/data";
import { ABChart, AgentActivity, Card, ScoreBreakdown, TopScores } from "@/components/client";

export const dynamic = "force-dynamic";

export default async function Brain() {
  const [curve, readout, scores] = await Promise.all([
    getEquityCurve(), getABReadout(), getScores(),
  ]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Is it working?" sub="F+ · mechanical vs agentic">
          <ABChart data={curve} readout={readout} />
        </Card>
        <Card title="Score breakdown" sub="sub-signals to composite" delay={60}>
          <ScoreBreakdown rows={scores} />
        </Card>
      </div>

      <Card title="Top scores" sub="ranked by composite" delay={120}>
        <TopScores rows={scores} />
      </Card>

      <Card title="Agent activity" sub="live · polls every 4s" delay={160}>
        <AgentActivity />
      </Card>

      <p className="px-1 pt-2 text-xs text-dim">
        The agents produce signals; the frozen F+ engine decides the portfolio. Research
        tool, not investment advice.
      </p>
    </div>
  );
}
