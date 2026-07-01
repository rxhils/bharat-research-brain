"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Scissors } from "lucide-react";
import { api } from "@/lib/api";
import { Card, EmptyState } from "@/components/ui/Card";

export default function ReelScriptPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [edited, setEdited] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    fetch(api.artifactUrl(jobId, "06_script_edited.json")).then((x) => x.ok ? x.json() : null).then(setEdited).catch(() => {}).finally(() => setLoaded(true));
  }, [jobId]);

  if (loaded && !edited) return <div className="px-6 py-8 max-w-3xl mx-auto"><EmptyState title="No script artifact" /></div>;
  const segs = edited?.segments ?? [];

  return (
    <div className="px-6 py-6 max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="eyebrow">Script Room + Retention Editor</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">Timed script · {edited?.total_seconds}s</h2>
        </div>
        <span className="chip border-line text-ink-muted">{edited?.pattern_interrupt_beats} visual beats</span>
      </div>

      <div className="space-y-2">
        {segs.map((s: any, i: number) => (
          <div key={i} className="glass card-pad flex gap-4">
            <div className="w-16 shrink-0">
              <div className="text-xs uppercase text-ink-faint">{s.label}</div>
              <div className="text-sm mono text-teal">{s.t0}–{s.t0 + s.seconds}s</div>
            </div>
            <p className="flex-1 text-sm text-ink-muted">{s.narration}</p>
          </div>
        ))}
      </div>

      {edited?.edits && (
        <Card>
          <div className="eyebrow mb-2 flex items-center gap-1.5"><Scissors size={13} /> Retention edits</div>
          <ul className="text-sm text-ink-muted space-y-1 list-disc pl-4">
            {edited.edits.map((e: string, i: number) => <li key={i}>{e}</li>)}
          </ul>
        </Card>
      )}
    </div>
  );
}
