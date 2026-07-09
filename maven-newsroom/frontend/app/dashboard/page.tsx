"use client";
/** Command Center — the two latest carousel runs + the two latest photo-reel
 *  runs (real data), plus entry points to the live Agent Orchestrator (a
 *  simulation you can watch each agent hand off to the next). */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ExternalLink, Film, LayoutGrid, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { photoReelsApi, type PackageSummary } from "@/lib/photoReelsApi";
import type { Job } from "@/lib/types";
import { EmptyState } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatusPill } from "@/components/photoReels/shared";

export default function DashboardPage() {
  const router = useRouter();
  const [carousels, setCarousels] = useState<Job[]>([]);
  const [reels, setReels] = useState<PackageSummary[]>([]);
  const [running, setRunning] = useState<"carousel" | "reel" | null>(null);

  useEffect(() => {
    api.jobs("carousel").then((r) => setCarousels(r.jobs.slice(0, 2))).catch(() => {});
    photoReelsApi.packages().then((r) => setReels(r.packages.slice(0, 2))).catch(() => {});
  }, []);

  async function runCarousel() {
    setRunning("carousel");
    try {
      const r = await api.run();
      router.push(`/orchestrator/${r.job_id}`);
    } catch {
      setRunning(null);
    }
  }

  async function runPhotoReel() {
    setRunning("reel");
    try {
      const r = await photoReelsApi.simulate();
      router.push(`/orchestrator/${r.job_id}`);
    } catch {
      setRunning(null);
    }
  }

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      {/* hero */}
      <div className="glass card-pad relative overflow-hidden mb-6">
        <div className="absolute -top-24 -right-16 h-64 w-64 rounded-full bg-teal/10 blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="eyebrow">Maven Command Center</div>
            <h2 className="text-2xl font-semibold tracking-tight mt-1.5">
              Your two AI newsrooms, one view.
            </h2>
            <p className="text-sm text-ink-muted mt-1.5 max-w-xl">
              The two latest carousel and photo-reel runs — plus a live Agent Orchestrator where you
              watch each agent hand off to the next. Orchestrator runs are simulations; real
              publishing happens in the Claude Code conductor.
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <button className="btn btn-primary" onClick={runCarousel} disabled={!!running}>
              {running === "carousel" ? <Loader2 size={15} className="animate-spin" /> : <LayoutGrid size={15} />}
              Orchestrator · Carousel
            </button>
            <button className="btn btn-primary" onClick={runPhotoReel} disabled={!!running}>
              {running === "reel" ? <Loader2 size={15} className="animate-spin" /> : <Film size={15} />}
              Orchestrator · Photo Reels
            </button>
          </div>
        </div>
      </div>

      {/* latest carousel runs */}
      <div className="eyebrow mb-2 flex items-center gap-2"><LayoutGrid size={13} /> Latest carousel runs</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {carousels.length === 0 ? (
          <EmptyState title="No carousel runs yet" hint="Trigger a run or wait for the 5:00 PM IST schedule." />
        ) : (
          carousels.map((j) => (
            <Link key={j.job_id} href={`/run/${j.job_id}`}
              className="glass card-pad block hover:border-teal/40 transition-colors">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold truncate">{j.job_id}</div>
                <StatusBadge status={j.status} />
              </div>
              <div className="text-[12px] text-ink-muted mt-1 line-clamp-2">{j.summary || "—"}</div>
              <div className="flex items-center gap-3 mt-3 text-[11px] text-ink-faint">
                <span>content {j.scores?.content_score ?? "—"}</span>
                <span>design {j.scores?.design_score ?? "—"}</span>
                <span>compliance {j.scores?.compliance_score ?? "—"}</span>
                {j.instagram_post_url && (
                  <a href={j.instagram_post_url} target="_blank" rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="ml-auto inline-flex items-center gap-1 text-teal hover:underline">
                    IG <ExternalLink size={11} />
                  </a>
                )}
              </div>
            </Link>
          ))
        )}
      </div>

      {/* latest photo-reel runs */}
      <div className="eyebrow mb-2 flex items-center gap-2"><Film size={13} /> Latest photo-reel runs</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reels.length === 0 ? (
          <EmptyState title="No photo-reel runs yet" hint="Run the pipeline from the Photo Reels dashboard." />
        ) : (
          reels.map((p) => (
            <Link key={p.job_id} href="/newsroom/reels/slides"
              className="glass card-pad block hover:border-teal/40 transition-colors">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold truncate">{p.headline || p.job_id}</div>
                <StatusPill status={p.status} />
              </div>
              <div className="text-[12px] text-ink-faint mt-1">{p.job_id}</div>
              <div className="flex items-center gap-3 mt-3 text-[11px] text-ink-faint">
                <span>QA {p.qa_score ?? "—"}/100</span>
                {p.permalink && (
                  <a href={p.permalink} target="_blank" rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="ml-auto inline-flex items-center gap-1 text-teal hover:underline">
                    View reel <ExternalLink size={11} />
                  </a>
                )}
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
