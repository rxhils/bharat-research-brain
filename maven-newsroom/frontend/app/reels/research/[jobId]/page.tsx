"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, EmptyState } from "@/components/ui/Card";

export default function ReelResearchPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [research, setResearch] = useState<any>(null);
  const [fit, setFit] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    fetch(api.artifactUrl(jobId, "01_research.json")).then((x) => x.ok ? x.json() : null).then(setResearch).catch(() => {});
    fetch(api.artifactUrl(jobId, "02_viral_fit.json")).then((x) => x.ok ? x.json() : null).then(setFit).catch(() => {}).finally(() => setLoaded(true));
  }, [jobId]);

  if (loaded && !fit) return <div className="px-6 py-8 max-w-5xl mx-auto"><EmptyState title="No viral-fit artifact" hint="Run the reel pipeline first." /></div>;
  const ranked = fit?.ranked ?? [];
  const dims = fit?.dimensions ?? [];

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto space-y-4">
      <div>
        <div className="eyebrow">Research & Viral Fit · Market Sentinel + Viral Fit Gate</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">Which story becomes the reel</h2>
        <p className="text-sm text-ink-muted mt-1">The most <em>important</em> story isn&apos;t always the best <em>reel</em> — this scores each story for scroll-stop.</p>
      </div>

      {research?.market_summary && <Card><div className="eyebrow mb-2">Market Summary</div><p className="text-sm text-ink-muted leading-relaxed">{research.market_summary}</p></Card>}

      {fit && (
        <div className="glass overflow-hidden">
          <div className="grid grid-cols-[1fr_repeat(7,minmax(0,52px))_70px] gap-2 px-4 py-2.5 border-b border-line text-[10px] uppercase tracking-wider text-ink-faint">
            <span>Story</span>
            {dims.map((d: string) => <span key={d} className="text-center">{d.slice(0, 4)}</span>)}
            <span className="text-center">Fit</span>
          </div>
          {ranked.map((r: any, i: number) => (
            <div key={i} className={`grid grid-cols-[1fr_repeat(7,minmax(0,52px))_70px] gap-2 px-4 py-3 border-b border-line/60 items-center ${i === 0 ? "bg-teal/[0.06]" : ""}`}>
              <div className="min-w-0">
                <div className="text-[13px] truncate">{r.headline}</div>
                {i === 0 ? <span className="chip border-teal/40 text-teal bg-teal/10 mt-1">Chosen for the reel</span>
                  : <div className="text-[10px] text-ink-faint truncate mt-0.5">{r.rejected_reason}</div>}
              </div>
              {dims.map((d: string) => (
                <span key={d} className="text-center text-xs mono" style={{ color: r.dims[d] >= 7 ? "#27C281" : r.dims[d] >= 5 ? "#94A3B8" : "#5B6B7E" }}>{r.dims[d]}</span>
              ))}
              <span className="text-center font-semibold" style={{ color: i === 0 ? "#1FB6A6" : "#94A3B8" }}>{r.viral_fit}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
