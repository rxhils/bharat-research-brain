"use client";
/** Photo Reels — Archive (/newsroom/reels/slides/archive). */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Archive, RefreshCw } from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api, type PackageSummary } from "@/lib/photoReelsApi";
import { StatusPill } from "@/components/photoReels/shared";

export default function PhotoReelsArchive() {
  const [rows, setRows] = useState<PackageSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    api.packages().then((r) => setRows(r.packages))
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  return (
    <div className="px-6 py-6 max-w-[1100px] mx-auto space-y-5">
      <div className="glass card-pad flex items-center justify-between">
        <div>
          <div className="eyebrow flex items-center gap-1.5"><Archive size={13} /> Archive</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">All photo-reel packages</h2>
        </div>
        <button className="btn btn-ghost" onClick={load}><RefreshCw size={15} /></button>
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {rows.length === 0 ? (
        <EmptyState title="No packages yet" hint="Every run lands here, newest first." />
      ) : (
        <div className="glass card-pad divide-y divide-white/5">
          {rows.map((r) => (
            <div key={r.job_id} className="py-3 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium truncate">{r.headline ?? "— (blocked run)"}</div>
                <div className="text-[11px] text-ink-faint">{r.job_id}</div>
              </div>
              <div className="text-[12px] text-ink-muted w-20 text-right">
                QA {r.qa_score ?? "—"}{r.qa_passed ? " ✓" : ""}
              </div>
              <StatusPill status={r.status} />
              {r.permalink && (
                <a className="text-[11px] text-teal underline" href={r.permalink}
                  target="_blank" rel="noreferrer">posted</a>
              )}
              <Link className="btn btn-ghost text-xs" href="/newsroom/reels/slides/review">Open</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
