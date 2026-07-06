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
