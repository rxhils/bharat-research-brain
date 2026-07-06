"use client";
/** Photo Reels — Daily Run pipeline view (/newsroom/reels/slides/run). */
import { useState } from "react";
import { Activity, Play, RefreshCw, Search } from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api } from "@/lib/photoReelsApi";
import { ModeBanner, StatusPill, usePhotoReelsLatest } from "@/components/photoReels/shared";

const STAGE_HINTS: Record<string, string> = {
  market_radar: "India finance / AI / tech / sector stories + top themes of the day",
  fact_check: "Verifies sources; blocks rumours, hype and advisory language",
  story_selector: "Picks the one story that works as a 5-image photo Reel",
  slide_script: "Exactly 5 slides: hook · what · why · why it matters · takeaway",
  slide_design: "5 premium 1080x1920 images — exact text via local compositor",
  export: "5 PNGs + ZIP + cover + manual Instagram upload steps",
  music_scout: "Instagram music-library mood + search terms (no downloads)",
  qa_gate: "Facts ≥95 · design ≥90 · readability ≥92 · format · compliance",
  package: "Review queue: approve / reject / revise / export",
};

export default function PhotoReelsRun() {
  const { pkg, error, reload, setError } = usePhotoReelsLatest();
  const [busy, setBusy] = useState(false);

  async function run(researchOnly: boolean) {
    setBusy(true); setError(null);
    try { await api.run(researchOnly ? { research_only: true } : {}); reload(); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(false);
  }

  const stages = pkg ? Object.entries(pkg.stages) : [];
  return (
    <div className="px-6 py-6 max-w-[1100px] mx-auto space-y-5">
      <div className="glass card-pad">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="eyebrow flex items-center gap-1.5"><Activity size={13} /> Daily Run</div>
            <h2 className="text-xl font-semibold tracking-tight mt-1">
              Photo Reel pipeline {pkg ? `· ${pkg.job_id}` : ""}
            </h2>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-primary" disabled={busy} onClick={() => run(false)}>
              <Play size={15} /> {busy ? "Running…" : "Run full pipeline"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => run(true)}>
              <Search size={15} /> Research only
            </button>
            <button className="btn btn-ghost" onClick={reload}><RefreshCw size={15} /></button>
          </div>
        </div>
        <div className="mt-3"><ModeBanner compact /></div>
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {!pkg ? (
        <EmptyState title="No run yet" hint="Start the full pipeline — every agent writes an auditable JSON artifact." />
      ) : (
        <div className="glass card-pad">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold">9 pipeline agents</div>
            <StatusPill status={pkg.package?.status} />
          </div>
          <div className="space-y-2">
            {stages.map(([key, st], i) => (
              <div key={key} className="flex items-center gap-3 border border-white/5 rounded-lg px-3 py-2.5">
                <span className={`h-6 w-6 shrink-0 rounded-full grid place-items-center text-[11px] font-semibold ${
                  st.done ? "bg-ok/15 text-ok border border-ok/40" : "bg-white/5 text-ink-faint border border-line"}`}>
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-medium">{st.name}</div>
                  <div className="text-[11px] text-ink-faint truncate">{STAGE_HINTS[key] ?? ""}</div>
                </div>
                <span className={`text-[11px] ${st.done ? "text-ok" : "text-ink-faint"}`}>
                  {st.done ? (st.status || "done") : "waiting"}
                </span>
              </div>
            ))}
          </div>
          {pkg.data_mode && (
            <div className="text-[11px] text-ink-faint mt-3">
              Data mode: <b>{pkg.data_mode}</b>
              {pkg.top_sectors_or_themes?.length ? ` · Top themes: ${pkg.top_sectors_or_themes.join(", ")}` : ""}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
