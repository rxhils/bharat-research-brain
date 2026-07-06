"use client";
/** Photo Reels — Dashboard (/newsroom/reels/slides). */
import { useEffect, useState } from "react";
import Link from "next/link";
import { Camera, Download, Images, Play, RefreshCw, Search, Square } from "lucide-react";
import { StatCard, EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api, type PhotoReelsConfig } from "@/lib/photoReelsApi";
import { ModeBanner, StatusPill, SlideThumb, usePhotoReelsLatest } from "@/components/photoReels/shared";

export default function PhotoReelsDashboard() {
  const { pkg, error, loading, reload, setError } = usePhotoReelsLatest();
  const [cfg, setCfg] = useState<PhotoReelsConfig | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => { api.config().then(setCfg).catch(() => {}); }, []);

  async function act(name: string, fn: () => Promise<unknown>) {
    setBusy(name); setNote(null);
    try { const r = await fn(); setNote(JSON.stringify(r).slice(0, 220)); reload(); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(null);
  }

  const jobId = pkg?.job_id;
  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-5">
      <div className="glass card-pad">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="eyebrow flex items-center gap-1.5">
              <Camera size={13} /> Photo Reels · 5 image slides · manual native upload
            </div>
            <h2 className="text-2xl font-semibold tracking-tight mt-1.5">
              Native Photo Reel Slides
            </h2>
            <div className="text-[12px] text-ink-faint mt-1">
              Cron status: <b className={cfg?.reel_image_slides_cron_enabled ? "text-warn" : "text-ok"}>
                {cfg ? (cfg.reel_image_slides_cron_enabled ? "ON" : "OFF") : "…"}
              </b>
              {" · "}Legacy reels cron: <b className="text-ok">{cfg?.legacy_reels_cron_enabled ? "ON" : "OFF"}</b>
              {" · "}Mode: {cfg?.primary_reels_mode ?? "…"}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-primary" disabled={busy !== null}
              onClick={() => act("run", () => api.run())}>
              <Play size={15} /> {busy === "run" ? "Running…" : "Run Photo Reel Slides"}
            </button>
            <button className="btn btn-ghost" disabled={busy !== null}
              onClick={() => act("research", () => api.run({ research_only: true }))}>
              <Search size={15} /> Run Research Only
            </button>
            <button className="btn btn-ghost" disabled={busy !== null || !jobId}
              onClick={() => jobId && act("images", () => api.generateImages(jobId))}>
              <Images size={15} /> Generate Images
            </button>
            <button className="btn btn-ghost" disabled={busy !== null || !jobId}
              onClick={() => jobId && act("export", () => api.exportImages(jobId))}>
              <Download size={15} /> Export Images
            </button>
            <button className="btn btn-ghost" disabled={busy !== null}
              onClick={() => act("cron", () => api.stopCron())}>
              <Square size={15} /> Stop Cron
            </button>
            <button className="btn btn-ghost" onClick={reload}><RefreshCw size={15} /></button>
          </div>
        </div>
        <div className="mt-4"><ModeBanner /></div>
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}
      {note && <div className="glass card-pad text-[11px] text-ink-faint font-mono break-all">{note}</div>}

      {loading ? null : !pkg ? (
        <EmptyState title="No photo-reel packages yet"
          hint="Run Photo Reel Slides — the pipeline finds a verified story and designs 5 slides for review." />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Latest package" value={pkg.job_id.replace("slides-", "")} hint={pkg.data_mode} />
            <StatCard label="QA score" value={pkg.qa?.overall_score ?? "—"}
              hint={pkg.qa?.passed ? "passed" : "not passed"} />
            <StatCard label="Slides" value={pkg.generated_images?.length ?? 0} hint="of 5 rendered" />
            <StatCard label="Export" value={pkg.export?.status ?? "—"} hint="ZIP for manual upload" />
          </div>

          <div className="glass card-pad">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="eyebrow">Selected story</div>
                <div className="text-sm font-semibold mt-1">{pkg.selected_story?.headline ?? "— (run blocked: no verified story)"}</div>
                {pkg.selected_story?.simulated && (
                  <div className="text-[11px] text-warn mt-0.5">SIMULATION data — not publishable</div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <StatusPill status={pkg.package?.status} />
                <Link href="/newsroom/reels/slides/review" className="btn btn-primary text-xs">Open Review</Link>
              </div>
            </div>
            {pkg.generated_images?.length ? (
              <div className="grid grid-cols-5 gap-3 max-w-[960px]">
                {pkg.slides.map((s) => (
                  <SlideThumb key={s.slide_number} jobId={pkg.job_id} n={s.slide_number} />
                ))}
              </div>
            ) : (
              <div className="text-[12px] text-ink-faint">No images rendered yet — Generate Images (zero credits, local compositor).</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
