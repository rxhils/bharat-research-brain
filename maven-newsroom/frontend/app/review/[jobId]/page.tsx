"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Check, X, Send, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { Card, EmptyState } from "@/components/ui/Card";
import { ScoreCard } from "@/components/ui/ScoreCard";

export default function ReviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [caption, setCaption] = useState<any>(null);
  const [hashtags, setHashtags] = useState<any>(null);
  const [arts, setArts] = useState<any[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = useCallback(() => { api.job(jobId).then(setJob).catch(() => {}); }, [jobId]);
  useEffect(() => {
    refresh();
    fetch(api.artifactUrl(jobId, "05_caption.json")).then((x) => x.ok ? x.json() : null).then(setCaption).catch(() => {});
    fetch(api.artifactUrl(jobId, "06_hashtags.json")).then((x) => x.ok ? x.json() : null).then(setHashtags).catch(() => {});
    api.artifacts(jobId).then((a) => setArts(a.artifacts.filter((x) => x.name.match(/^slide_\d\.jpg$/)).sort((p, q) => p.name.localeCompare(q.name)))).catch(() => {});
  }, [jobId, refresh]);

  const act = useCallback(async (label: string, fn: () => Promise<any>) => {
    setToast(`${label}…`);
    try { const r = await fn(); setToast(r?.status === "requires_conductor" ? "Requires Claude Code conductor" : `${label}: ${r?.status ?? "done"}`); refresh(); }
    catch (e: any) { setToast(e?.data?.problems ? `Blocked: ${e.data.problems.join(", ")}` : `${label} failed`); }
    setTimeout(() => setToast(null), 4000);
  }, [refresh]);

  const sc = job?.scores;
  const allow = sc?.publish_allowed === 1;

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="eyebrow">Review Room · Meta Auditor + Publish Gate</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">Final approval · {jobId}</h2>
        </div>
        <span className={`chip ${allow ? "border-ok/40 text-ok bg-ok/10" : "border-warn/40 text-warn bg-warn/10"}`}>
          Publish {allow ? "allowed" : "blocked"}
        </span>
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-5">
        <div className="space-y-4">
          {arts.length === 0 ? <EmptyState title="No final images" hint="Pixel Lab outputs slide_*.jpg once images are generated." /> : (
            <div className="grid grid-cols-3 gap-3">
              {arts.map((a, i) => (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img key={a.artifact_id} src={api.artifactUrl(jobId, a.name)} alt={`slide ${i + 1}`}
                  className="w-full rounded-xl border border-line" style={{ aspectRatio: "4/5", objectFit: "cover" }} />
              ))}
            </div>
          )}
          {caption?.caption && (
            <Card><div className="eyebrow mb-2">Caption</div>
              <p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed">{caption.caption}</p>
            </Card>
          )}
          {hashtags?.hashtags && (
            <Card><div className="eyebrow mb-2">Hashtags ({hashtags.count})</div>
              <div className="flex flex-wrap gap-1.5">{hashtags.hashtags.map((h: string) => <span key={h} className="chip border-line text-teal/80">{h}</span>)}</div>
            </Card>
          )}
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <ScoreCard label="Content" score={sc?.content_score} threshold={90} />
            <ScoreCard label="Design" score={sc?.design_score} threshold={90} />
            <ScoreCard label="Compliance" score={sc?.compliance_score} threshold={95} />
            <ScoreCard label="Aesthetic" score={sc?.aesthetic_score} sub="Visual QA" />
          </div>
          <Card>
            <div className="eyebrow mb-2">Actions</div>
            <div className="grid gap-2">
              <button disabled={!allow} onClick={() => act("Publish", () => api.publish(jobId))}
                className={`btn ${allow ? "btn-primary" : "btn-ghost opacity-50 cursor-not-allowed"}`}><Send size={15} />Approve &amp; Publish</button>
              <button onClick={() => act("Regenerate design", () => api.regenerateImages(jobId))} className="btn btn-ghost border-line"><RefreshCw size={15} />Regenerate Design</button>
              <button onClick={() => act("Rewrite caption", () => api.rewriteCaption(jobId))} className="btn btn-ghost border-line">Rewrite Caption</button>
              <button onClick={() => act("Recheck compliance", () => api.recheckQuality(jobId))} className="btn btn-ghost border-line">Rerun Compliance</button>
              <button onClick={() => act("Reject", () => api.reject(jobId))} className="btn btn-ghost border-danger/40 text-danger"><X size={15} />Reject</button>
            </div>
            {toast && <div className="mt-3 text-xs text-teal">{toast}</div>}
            <p className="text-[11px] text-mcp mt-2">Real publishing runs in the Claude Code conductor (Composio MCP). The gate here confirms quality + approval; it never fakes a publish.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
