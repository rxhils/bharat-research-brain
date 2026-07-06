"use client";
/** Photo Reels — Review (/newsroom/reels/slides/review). */
import { useState } from "react";
import { Check, ClipboardCheck, Copy, Download, RefreshCw, X } from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api } from "@/lib/photoReelsApi";
import { ManualSteps, SlideThumb, StatusPill, ViralAudioCard, usePhotoReelsLatest } from "@/components/photoReels/shared";

export default function PhotoReelsReview() {
  const { pkg, error, reload, setError } = usePhotoReelsLatest();
  const [busy, setBusy] = useState(false);
  const [zoom, setZoom] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  async function decide(decision: "approve" | "reject" | "revise") {
    if (!pkg) return;
    let reason: string | undefined;
    if (decision !== "approve") {
      reason = window.prompt(`Why ${decision}? (weak hook / unreadable / wrong story / design off ...)`) ?? undefined;
      if (reason === undefined) return;
    }
    setBusy(true); setError(null);
    try { await api.decision(pkg.job_id, decision, reason); reload(); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(false);
  }

  async function copyCaption() {
    if (!pkg) return;
    await navigator.clipboard.writeText(`${pkg.caption}\n\n${pkg.hashtags.join(" ")}`);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  const qa = pkg?.qa;
  const judge = pkg?.design_judge;
  const canApprove = !!qa?.passed && (judge ? !!judge.passed : true);
  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-5">
      <div className="glass card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow flex items-center gap-1.5"><ClipboardCheck size={13} /> Review</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">{pkg?.selected_story?.headline ?? "Photo Reel review"}</h2>
          {pkg && <div className="mt-1.5 flex items-center gap-2">
            <StatusPill status={pkg.package?.status} />
            {pkg.selected_story?.simulated && <span className="text-[11px] text-warn">SIMULATION — not publishable</span>}
          </div>}
        </div>
        {pkg && (
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-primary text-xs" disabled={busy || !canApprove}
              title={canApprove ? "" : "QA + design judge must pass before approval"}
              onClick={() => decide("approve")}><Check size={14} /> Approve</button>
            <button className="btn btn-ghost text-xs" disabled={busy} onClick={() => decide("revise")}>Revise</button>
            <button className="btn btn-ghost text-xs" disabled={busy} onClick={() => decide("reject")}><X size={14} /> Reject</button>
            <a className="btn btn-ghost text-xs" href={api.zipUrl(pkg.job_id)}><Download size={14} /> ZIP</a>
            <button className="btn btn-ghost" onClick={reload}><RefreshCw size={15} /></button>
          </div>
        )}
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {judge && !judge.passed && (
        <div className="glass card-pad border border-warn/40 text-sm">
          <b className="text-warn">Slides are readable but too plain.</b>{" "}
          <span className="text-ink-muted">
            Design judge: {judge.overall_score}/100.{" "}
            {(judge.issues ?? []).slice(0, 3).join(" · ")}
            {" — "}use the Slide Studio design actions (Make More Visual,
            Add Finance Graphic, Make Cover Stronger).
          </span>
        </div>
      )}

      {!pkg ? (
        <EmptyState title="Nothing to review" hint="Run the pipeline from the Dashboard first." />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2 space-y-5">
            <div className="glass card-pad">
              <div className="eyebrow mb-3">5 slides — tap to preview full-screen</div>
              <div className="grid grid-cols-5 gap-3">
                {pkg.slides.map((s) => (
                  <SlideThumb key={s.slide_number} jobId={pkg.job_id} n={s.slide_number}
                    onClick={() => setZoom(s.slide_number)} />
                ))}
              </div>
            </div>

            <div className="glass card-pad">
              <div className="flex items-center justify-between mb-2">
                <div className="eyebrow">Caption + hashtags</div>
                <button className="btn btn-ghost text-xs" onClick={copyCaption}>
                  <Copy size={13} /> {copied ? "Copied!" : "Copy caption"}
                </button>
              </div>
              <pre className="text-[12px] text-ink-muted whitespace-pre-wrap font-sans">{pkg.caption}</pre>
              <div className="text-[12px] text-teal mt-2">{pkg.hashtags.join(" ")}</div>
            </div>

            <div className="glass card-pad">
              <div className="eyebrow mb-2">Sources</div>
              {(pkg.selected_story?.sources ?? []).map((s) => (
                <div key={s.url || s.name} className="text-[12px] text-ink-muted">
                  {s.name}{s.url ? <> — <a className="text-teal underline" href={s.url} target="_blank" rel="noreferrer">{s.url}</a></> : null}
                </div>
              ))}
              <div className="text-[11px] text-ink-faint mt-2">{pkg.why_selected}</div>
            </div>
          </div>

          <div className="space-y-5">
            <div className="glass card-pad">
              <div className="eyebrow mb-2">QA Gate</div>
              <div className={`text-lg font-semibold ${qa?.passed ? "text-ok" : "text-danger"}`}>
                {qa?.passed ? "PASSED" : "NOT PASSED"} · {qa?.overall_score ?? "—"}/100
              </div>
              <div className="mt-2 space-y-1">
                {Object.entries(qa?.scores ?? {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-[12px]">
                    <span className="text-ink-muted">{k.replace(/_/g, " ")}</span>
                    <span className={v >= 90 ? "text-ok" : v >= 70 ? "text-warn" : "text-danger"}>{v}</span>
                  </div>
                ))}
              </div>
              {(qa?.issues?.length ?? 0) > 0 && (
                <div className="mt-3 text-[11px] text-warn space-y-1">
                  {qa?.issues?.map((i) => <div key={i}>· {i}</div>)}
                </div>
              )}
              {judge && (
                <div className="mt-4 pt-3 border-t border-line">
                  <div className="eyebrow mb-1.5">Design judge</div>
                  <div className={`text-sm font-semibold ${judge.passed ? "text-ok" : "text-warn"}`}>
                    {judge.passed ? "PREMIUM" : "TOO PLAIN"} · {judge.overall_score ?? "—"}/100
                  </div>
                  <div className="mt-1.5 space-y-1">
                    {["slide_1_cover", "visual_richness", "layout_variety", "premium_feel"].map((k) => (
                      <div key={k} className="flex justify-between text-[12px]">
                        <span className="text-ink-muted">{k.replace(/_/g, " ")}</span>
                        <span className={(judge.scores?.[k] ?? 0) >= 90 ? "text-ok" : "text-warn"}>
                          {judge.scores?.[k] ?? "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <ViralAudioCard pkg={pkg} busy={busy}
              onRefresh={async () => {
                setBusy(true);
                try { await api.refreshViralAudio(pkg.job_id); reload(); }
                catch (e) { setError(String((e as Error).message)); }
                setBusy(false);
              }} />

            <div className="glass card-pad">
              <div className="eyebrow mb-2">Manual upload steps</div>
              <ManualSteps steps={pkg.instagram_manual_steps} />
            </div>
          </div>
        </div>
      )}

      {pkg && zoom !== null && (
        <div className="fixed inset-0 z-50 bg-black/85 grid place-items-center p-6" onClick={() => setZoom(null)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={api.slideUrl(pkg.job_id, zoom)} alt={`Slide ${zoom}`}
            className="max-h-[92vh] rounded-xl border border-line" />
        </div>
      )}
    </div>
  );
}
