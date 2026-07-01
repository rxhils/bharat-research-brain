"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ExternalLink, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { Card, EmptyState } from "@/components/ui/Card";

export default function ResearchPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [r, setR] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    fetch(api.artifactUrl(jobId, "01_research.json")).then((x) => x.ok ? x.json() : null)
      .then(setR).catch(() => {}).finally(() => setLoaded(true));
  }, [jobId]);

  if (loaded && !r) return <div className="px-6 py-8 max-w-5xl mx-auto"><EmptyState title="No research artifact" hint="This run has no 01_research.json yet." /></div>;
  const stories = r?.top_3_stories ?? [];

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto space-y-4">
      <div>
        <div className="eyebrow">Research Room · Market Sentinel + Conviction Gate</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">Verified market intelligence · {r?.date ?? jobId}</h2>
      </div>

      {r?.market_summary && <Card><div className="eyebrow mb-2">Market Summary</div><p className="text-sm text-ink-muted leading-relaxed">{r.market_summary}</p></Card>}

      {r?.data_confidence_note && (
        <div className="glass card-pad border-info/30">
          <div className="flex items-center gap-2 mb-2"><ShieldAlert size={15} className="text-info" /><span className="eyebrow text-info">Data Confidence</span></div>
          <p className="text-sm text-ink-muted leading-relaxed">{r.data_confidence_note}</p>
        </div>
      )}

      <div className="flex items-center gap-3 text-sm">
        <span className="chip border-ok/40 text-ok bg-ok/10">{stories.length} selected</span>
        <span className="text-ink-faint">Gate: importance ≥ 7 · confidence ≥ 8</span>
      </div>

      <div className="space-y-4">
        {stories.map((s: any) => (
          <Card key={s.rank}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="h-7 w-7 grid place-items-center rounded-lg bg-teal/15 text-teal font-semibold text-sm">{s.rank}</span>
                <div>
                  <div className="text-[15px] font-semibold leading-snug">{s.headline}</div>
                  <div className="text-[11px] text-ink-faint mt-0.5">{s.category}</div>
                </div>
              </div>
              <div className="flex gap-1.5 shrink-0">
                <span className="chip border-line text-ink-muted">imp {s.importance_score}</span>
                <span className="chip border-line text-ink-muted">conf {s.confidence_score}</span>
              </div>
            </div>
            <p className="text-sm text-ink-muted mt-3">{s.what_happened}</p>
            <div className="grid md:grid-cols-2 gap-3 mt-3">
              <div><div className="eyebrow mb-1">Why it matters</div><p className="text-sm text-ink-muted">{s.why_it_matters}</p></div>
              <div><div className="eyebrow mb-1">Takeaway</div><p className="text-sm text-ink-muted">{s.investor_takeaway}</p></div>
            </div>
            {s.key_numbers?.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {s.key_numbers.map((k: string, i: number) => <span key={i} className="chip border-line text-ink-muted mono">{k}</span>)}
              </div>
            )}
            <div className="mt-3 flex flex-wrap gap-3">
              {(s.affected_sectors ?? []).map((x: string) => <span key={x} className="text-[11px] text-teal/80">#{x.replace(/\s+/g, "")}</span>)}
            </div>
            {s.sources?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-line flex flex-wrap gap-x-4 gap-y-1.5">
                {s.sources.map((src: any, i: number) => (
                  <a key={i} href={src.url} target="_blank" rel="noreferrer" className="text-[11px] text-ink-muted hover:text-teal inline-flex items-center gap-1">
                    {src.name} <ExternalLink size={10} />
                  </a>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
