"use client";
/** Photo Reels — Export (/newsroom/reels/slides/export). */
import { useEffect, useState } from "react";
import { Clapperboard, Copy, Download, Link2, RefreshCw } from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api, type PhotoReelsConfig } from "@/lib/photoReelsApi";
import { ManualSteps, SlideThumb, StatusPill, ViralAudioCard, usePhotoReelsLatest } from "@/components/photoReels/shared";

export default function PhotoReelsExport() {
  const { pkg, error, reload, setError } = usePhotoReelsLatest();
  const [cfg, setCfg] = useState<PhotoReelsConfig | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => { api.config().then(setCfg).catch(() => {}); }, []);

  async function act(name: string, fn: () => Promise<unknown>) {
    setBusy(name); setError(null);
    try { await fn(); reload(); } catch (e) { setError(String((e as Error).message)); }
    setBusy(null);
  }

  async function copyCaption() {
    if (!pkg) return;
    await navigator.clipboard.writeText(`${pkg.caption}\n\n${pkg.hashtags.join(" ")}`);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  function markPosted() {
    if (!pkg) return;
    const permalink = window.prompt("Posted manually — paste the Instagram Reel URL/permalink (optional):") ?? undefined;
    void act("posted", () => api.markPosted(pkg.job_id, permalink || undefined));
  }

  function renderVideo() {
    if (!pkg) return;
    if (!window.confirm("Render a slideshow MP4 for AUTOMATED publishing? "
      + "This is NOT the default — the native photo Reel is uploaded manually. Continue?")) return;
    void act("video", () => api.renderVideo(pkg.job_id));
  }

  return (
    <div className="px-6 py-6 max-w-[1200px] mx-auto space-y-5">
      <div className="glass card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow flex items-center gap-1.5"><Download size={13} /> Export</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">
            Native photo Reel package {pkg ? `· ${pkg.job_id}` : ""}
          </h2>
          {pkg && <div className="mt-1.5"><StatusPill status={pkg.package?.status} /></div>}
        </div>
        {pkg && (
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-primary text-xs" disabled={busy !== null}
              onClick={() => act("export", () => api.exportImages(pkg.job_id))}>
              <Download size={14} /> {busy === "export" ? "Exporting…" : "Export images"}
            </button>
            {pkg.export?.zip_path && (
              <a className="btn btn-ghost text-xs" href={api.zipUrl(pkg.job_id)}>
                <Download size={14} /> Download ZIP
              </a>
            )}
            <button className="btn btn-ghost text-xs" onClick={copyCaption}>
              <Copy size={14} /> {copied ? "Copied!" : "Copy caption"}
            </button>
            <button className="btn btn-ghost text-xs" disabled={busy !== null} onClick={markPosted}>
              <Link2 size={14} /> Mark posted manually
            </button>
            <button className="btn btn-ghost" onClick={reload}><RefreshCw size={15} /></button>
          </div>
        )}
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {!pkg ? (
        <EmptyState title="Nothing to export" hint="Run the pipeline and pass review first." />
      ) : (
        <>
          <div className="glass card-pad">
            <div className="eyebrow mb-3">All 5 individual images (upload in this order)</div>
            <div className="grid grid-cols-5 gap-3">
              {pkg.slides.map((s) => (
                <div key={s.slide_number} className="space-y-1">
                  <SlideThumb jobId={pkg.job_id} n={s.slide_number} />
                  <div className="text-[10px] text-ink-faint text-center">#{s.slide_number}</div>
                </div>
              ))}
            </div>
            {pkg.export?.status === "exported" ? (
              <div className="text-[11px] text-ok mt-3">Exported — ZIP includes the 5 PNGs, cover, caption.txt and upload_steps.txt.</div>
            ) : (
              <div className="text-[11px] text-ink-faint mt-3">Not exported yet — click Export images.</div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="glass card-pad">
              <div className="eyebrow mb-2">Manual Instagram steps</div>
              <ManualSteps steps={pkg.instagram_manual_steps} />
            </div>
            <div className="space-y-5">
              <ViralAudioCard pkg={pkg} busy={busy !== null}
                onRefresh={() => act("audio", () => api.refreshViralAudio(pkg.job_id))} />
              <div className="glass card-pad">
                <div className="eyebrow mb-2 flex items-center gap-1.5">
                  <Clapperboard size={12} /> Optional: automated video Reel
                </div>
                <div className="text-[12px] text-ink-muted mb-3">
                  Renders the 5 slides into an MP4 for API publishing
                  (slideshow_video_reel_auto). Not the default; the native photo
                  Reel above is the primary output.
                </div>
                <button className="btn btn-ghost text-xs" onClick={renderVideo}
                  disabled={busy !== null || !cfg?.allow_auto_reel_video_mode}>
                  {busy === "video" ? "Rendering…" : cfg?.allow_auto_reel_video_mode
                    ? "Render MP4 for auto publish" : "Auto video mode disabled"}
                </button>
                {pkg.video_render?.video_path && (
                  <div className="text-[11px] text-ink-faint mt-2 break-all">
                    Rendered: {pkg.video_render.video_path} ({pkg.video_render.duration_seconds}s)
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
