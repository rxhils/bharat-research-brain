"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Send, X, RefreshCw, Mic, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { Card, EmptyState } from "@/components/ui/Card";
import { ScoreCard } from "@/components/ui/ScoreCard";

export default function ReelReviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [quality, setQuality] = useState<any>(null);
  const [caption, setCaption] = useState<any>(null);
  const [arts, setArts] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = useCallback(() => { api.job(jobId).then(setJob).catch(() => {}); }, [jobId]);
  useEffect(() => {
    refresh();
    fetch(api.artifactUrl(jobId, "16_quality.json")).then((x) => x.ok ? x.json() : null).then(setQuality).catch(() => {});
    fetch(api.artifactUrl(jobId, "14_caption.json")).then((x) => x.ok ? x.json() : null).then(setCaption).catch(() => {});
    api.artifacts(jobId).then((a) => setArts(a.artifacts.map((x) => x.name))).catch(() => {});
  }, [jobId, refresh]);

  const act = useCallback(async (label: string, fn: () => Promise<any>) => {
    setToast(`${label}…`);
    try { const r = await fn(); setToast(r?.status === "requires_conductor" ? "Requires Claude Code conductor" : `${label}: ${r?.status ?? "done"}`); refresh(); }
    catch (e: any) { setToast(e?.data?.problems ? `Blocked: ${e.data.problems.join(", ")}` : `${label} failed`); }
    setTimeout(() => setToast(null), 4000);
  }, [refresh]);

  const s = quality?.scores ?? {};
  const allow = quality?.overall_pass;
  const hasReel = arts.includes("reel.mp4");
  const hasCover = arts.includes("cover.jpg");

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="eyebrow">Reel Review · Reel Auditor + Publish Gate</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">Approve the reel · {jobId}</h2>
        </div>
        <span className={`chip ${allow ? "border-ok/40 text-ok bg-ok/10" : "border-warn/40 text-warn bg-warn/10"}`}>Publish {allow ? "allowed" : "blocked"}</span>
      </div>

      <div className="grid lg:grid-cols-[380px_1fr] gap-5">
        <div className="space-y-3">
          {hasReel ? (
            <video controls className="w-full rounded-xl border border-line bg-black" style={{ aspectRatio: "9/16" }}
              src={api.artifactUrl(jobId, "reel.mp4")} poster={hasCover ? api.artifactUrl(jobId, "cover.jpg") : undefined} />
          ) : hasCover ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={api.artifactUrl(jobId, "cover.jpg")} alt="cover" className="w-full rounded-xl border border-line" style={{ aspectRatio: "9/16", objectFit: "cover" }} />
          ) : (
            <EmptyState title="No reel yet" hint="Cut Room builds reel.mp4 in the Claude Code conductor once scenes + voiceover exist." />
          )}
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <ScoreCard label="Hook" score={s.hook} threshold={85} />
            <ScoreCard label="Retention" score={s.retention} threshold={85} />
            <ScoreCard label="Visual" score={s.visual} threshold={85} sub={s.visual ? undefined : "needs the real video"} />
            <ScoreCard label="Compliance" score={s.compliance} threshold={95} />
          </div>
          {caption?.caption && <Card><div className="eyebrow mb-2">Caption</div><p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed">{caption.caption}</p></Card>}
          <Card>
            <div className="eyebrow mb-2">Actions (Telegram-approval mirror)</div>
            <div className="grid gap-2">
              <button disabled={!allow} onClick={() => act("Publish", () => api.publish(jobId))}
                className={`btn ${allow ? "btn-primary" : "btn-ghost opacity-50 cursor-not-allowed"}`}><Send size={15} />Approve & Publish Reel</button>
              <button onClick={() => act("Rewrite hook", () => api.rerun(jobId, "hook_lab"))} className="btn btn-ghost border-line"><Zap size={15} />Rewrite Hook</button>
              <button onClick={() => act("Regenerate video", () => api.rerun(jobId, "scene_studio"))} className="btn btn-ghost border-line"><RefreshCw size={15} />Regenerate Video</button>
              <button onClick={() => act("Regenerate voiceover", () => api.rerun(jobId, "voice_studio"))} className="btn btn-ghost border-line"><Mic size={15} />Regenerate Voiceover</button>
              <button onClick={() => act("Reject", () => api.reject(jobId))} className="btn btn-ghost border-danger/40 text-danger"><X size={15} />Reject</button>
            </div>
            {toast && <div className="mt-3 text-xs text-teal">{toast}</div>}
            <p className="text-[11px] text-mcp mt-2">Real publishing runs in the Claude Code conductor (Composio Reels). Never faked.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
