"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Zap } from "lucide-react";
import { api } from "@/lib/api";
import { Card, EmptyState } from "@/components/ui/Card";

export default function ReelHooksPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [hooks, setHooks] = useState<any>(null);
  const [angle, setAngle] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    fetch(api.artifactUrl(jobId, "04_hooks.json")).then((x) => x.ok ? x.json() : null).then(setHooks).catch(() => {}).finally(() => setLoaded(true));
    fetch(api.artifactUrl(jobId, "03_angle.json")).then((x) => x.ok ? x.json() : null).then(setAngle).catch(() => {});
  }, [jobId]);

  if (loaded && !hooks) return <div className="px-6 py-8 max-w-4xl mx-auto"><EmptyState title="No hooks artifact" /></div>;
  const list = (hooks?.hooks ?? []).slice().sort((a: any, b: any) => b.strength - a.strength);
  const chosen = hooks?.chosen;

  return (
    <div className="px-6 py-6 max-w-4xl mx-auto space-y-4">
      <div>
        <div className="eyebrow flex items-center gap-1.5"><Zap size={13} /> Hook Lab + Angle Studio</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">The first 2 seconds</h2>
      </div>

      {angle?.chosen && (
        <Card><div className="eyebrow mb-1">Chosen angle</div>
          <p className="text-[15px] font-medium">{angle.chosen.angle}</p>
          <p className="text-xs text-ink-faint mt-1">{angle.rationale}</p>
        </Card>
      )}

      <div className="space-y-2">
        {list.map((h: any, i: number) => (
          <div key={i} className={`glass card-pad flex items-center gap-4 ${chosen && h.text === chosen.text ? "border-teal/50 shadow-glow" : ""}`}>
            <span className="chip border-line text-ink-muted uppercase w-24 justify-center">{h.bucket}</span>
            <p className="flex-1 text-sm">{h.text}</p>
            {chosen && h.text === chosen.text && <span className="chip border-teal/40 text-teal bg-teal/10">Chosen</span>}
            {!h.compliant && <span className="chip border-danger/40 text-danger">flagged</span>}
            <span className="text-lg font-semibold" style={{ color: h.strength >= 85 ? "#27C281" : "#F2994A" }}>{h.strength}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
