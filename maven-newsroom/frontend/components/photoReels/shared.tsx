"use client";
/** Shared pieces for the Native Photo Reel Slides pages. */
import { useCallback, useEffect, useState } from "react";
import { photoReelsApi as api, type PackageDetail } from "@/lib/photoReelsApi";

export const STATUS_TONE: Record<string, string> = {
  draft: "bg-white/5 text-ink-faint",
  needs_review: "bg-info/15 text-info",
  approved: "bg-ok/15 text-ok",
  rejected: "bg-danger/15 text-danger",
  revise_requested: "bg-warn/15 text-warn",
  exported: "bg-ok/15 text-ok",
  posted_manually: "bg-ok/20 text-ok",
  queued_for_auto_video: "bg-mcp/15 text-mcp",
  published_video_reel: "bg-ok/20 text-ok",
  blocked: "bg-danger/15 text-danger",
};

export function StatusPill({ status }: { status?: string }) {
  const s = status || "draft";
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${STATUS_TONE[s] || STATUS_TONE.draft}`}>
      {s.replace(/_/g, " ")}
    </span>
  );
}

export function ManualSteps({ steps }: { steps: string[] }) {
  return (
    <ol className="space-y-1.5 text-[13px] text-ink-muted list-none">
      {steps.map((s, i) => (
        <li key={s} className="flex gap-2.5">
          <span className="shrink-0 h-5 w-5 rounded-full bg-teal/10 border border-teal/30 text-teal grid place-items-center text-[10px] font-semibold">
            {i + 1}
          </span>
          {s}
        </li>
      ))}
    </ol>
  );
}

export function SlideThumb({ jobId, n, onClick, size = "small" }: {
  jobId: string; n: number; onClick?: () => void; size?: "small" | "large";
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={api.slideUrl(jobId, n)}
      alt={`Slide ${n}`}
      onClick={onClick}
      className={`rounded-lg border border-line bg-black object-contain aspect-[9/16] ${
        size === "large" ? "w-full" : "w-full max-w-[180px]"
      } ${onClick ? "cursor-zoom-in hover:border-teal/50 transition-colors" : ""}`}
    />
  );
}

export function usePhotoReelsLatest() {
  const [pkg, setPkg] = useState<PackageDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    api
      .latest()
      .then((p) => { setPkg(p); setError(null); })
      .catch((e: Error) => {
        if (!String(e.message).includes("no photo-reel")) setError(e.message);
        setPkg(null);
      })
      .finally(() => setLoading(false));
  }, []);
  useEffect(load, [load]);
  return { pkg, error, loading, reload: load, setError };
}

export function ViralAudioCard({ pkg, onRefresh, busy }: {
  pkg: PackageDetail; onRefresh?: () => void; busy?: boolean;
}) {
  const va = pkg.viral_audio;
  const picks = va?.picks ?? [];
  return (
    <div className="glass card-pad">
      <div className="flex items-center justify-between mb-2">
        <div className="eyebrow">🎵 Viral audio right now (IG / TikTok)</div>
        {onRefresh && (
          <button className="btn btn-ghost text-xs" disabled={busy} onClick={onRefresh}>
            {busy ? "Scouting…" : "Re-scout"}
          </button>
        )}
      </div>
      {picks.length === 0 ? (
        <div className="text-[12px] text-ink-faint">
          No viral-audio picks yet — run the pipeline or Re-scout.
        </div>
      ) : (
        <div className="space-y-2.5">
          {picks.map((p, i) => (
            <div key={p.title}
              className={`rounded-lg border px-3 py-2 ${i === 0
                ? "border-teal/40 bg-teal/5" : "border-line bg-white/[0.02]"}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="text-[13px] font-semibold">
                  {i === 0 ? "★ " : ""}{p.title}
                  <span className="text-ink-faint font-normal"> — {p.artist}</span>
                </div>
                <div className="flex gap-1.5 text-[10px] shrink-0">
                  <span className="px-1.5 py-0.5 rounded bg-white/5 border border-line text-ink-faint">{p.platform}</span>
                  {p.business_safe && <span className="px-1.5 py-0.5 rounded bg-ok/10 border border-ok/30 text-ok">brand-safe</span>}
                </div>
              </div>
              <div className="text-[11px] text-ink-muted mt-0.5">{p.why}</div>
              <div className={`text-[10px] mt-0.5 ${p.freshness.startsWith("fresh") ? "text-ink-faint" : "text-warn"}`}>
                {p.freshness} · match {p.match_score}
              </div>
              {i === 0 && <div className="text-[11px] text-teal mt-1">{p.how_to_use}</div>}
            </div>
          ))}
        </div>
      )}
      {va?.registry_stale && (
        <div className="text-[11px] text-warn mt-2">
          Registry last refreshed {va.registry_last_refreshed} — trends live
          ~7-10 days; refresh it before posting.
        </div>
      )}
      <div className="text-[10px] text-ink-faint mt-2">{va?.compliance_note}</div>
    </div>
  );
}

export function ModeBanner({ compact }: { compact?: boolean }) {
  return (
    <div className={`rounded-lg border border-teal/25 bg-teal/5 text-[12px] text-ink-muted ${compact ? "px-3 py-2" : "px-4 py-3"}`}>
      <b className="text-teal">Native Photo Reel mode.</b> Creates 5 individual
      image slides for Instagram&apos;s native photo Reel flow. Upload them
      manually through Instagram Reels using <b>Select Multiple</b> — this is
      not a carousel post and not an auto-published video.
    </div>
  );
}
