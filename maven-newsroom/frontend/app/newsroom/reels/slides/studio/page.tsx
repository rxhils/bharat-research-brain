"use client";
/** Photo Reels — Slide Studio (/newsroom/reels/slides/studio). */
import { useEffect, useState } from "react";
import {
  Layers, LayoutTemplate, Palette, RefreshCw, Shapes, Sparkles, Wand2, Zap,
} from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api, type DesignAction } from "@/lib/photoReelsApi";
import { usePhotoReelsLatest } from "@/components/photoReels/shared";

export default function SlideStudio() {
  const { pkg, error, reload, setError } = usePhotoReelsLatest();
  const [styles, setStyles] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [bust, setBust] = useState(0); // cache-buster after regeneration

  useEffect(() => { api.config().then((c) => setStyles(c.styles)).catch(() => {}); }, []);

  async function refresh() { reload(); setBust(Date.now()); }

  async function act(key: string, fn: () => Promise<unknown>) {
    setBusy(key); setError(null);
    try { await fn(); await refresh(); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(null);
  }

  const design = (action: DesignAction, slide?: number) =>
    act(`${action}${slide ?? ""}`, () => api.designAction(pkg!.job_id, action, slide));

  function editText(n: number, field: "title" | "body", current: string) {
    const next = window.prompt(`Slide ${n} ${field} (${field === "title" ? "max 7" : "max 18"} words):`, current);
    if (next !== null && next.trim())
      void act(`edit${n}`, () => api.regenerateSlide(pkg!.job_id, n, { [field]: next.trim() }));
  }

  const judge = pkg?.design_judge;
  const fixesFor = (n: number) =>
    (judge?.required_fixes ?? []).filter((f) => f.startsWith(`slide ${n}`));

  const ACTIONS: { key: DesignAction; label: string; icon: React.ReactNode }[] = [
    { key: "make_more_visual", label: "Make More Visual", icon: <Sparkles size={13} /> },
    { key: "add_finance_graphic", label: "Add Finance Graphic", icon: <Shapes size={13} /> },
    { key: "regenerate_background", label: "Regenerate Background", icon: <Layers size={13} /> },
    { key: "redesign_layout", label: "Redesign Layout", icon: <LayoutTemplate size={13} /> },
    { key: "make_cover_stronger", label: "Make Cover Stronger", icon: <Zap size={13} /> },
  ];

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-5">
      <div className="glass card-pad">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="eyebrow flex items-center gap-1.5"><Palette size={13} /> Slide Studio</div>
            <h2 className="text-xl font-semibold tracking-tight mt-1">
              Design deck {pkg ? `· ${pkg.job_id}` : ""}
            </h2>
            <div className="text-[11px] text-ink-faint mt-0.5 flex flex-wrap gap-x-3">
              <span>Design pack: <b className="text-ink-muted">{pkg?.style ?? "—"}</b></span>
              <span>Design judge: <b className={judge?.passed ? "text-ok" : "text-danger"}>
                {judge?.overall_score ?? "—"}/100 {judge?.passed ? "PASS" : judge ? "FAIL" : ""}</b></span>
              <span>Visual richness: <b className="text-ink-muted">{judge?.scores?.visual_richness ?? "—"}</b></span>
              <span>Cover: <b className="text-ink-muted">{judge?.scores?.slide_1_cover ?? "—"}</b></span>
              <span>Variety: <b className="text-ink-muted">{judge?.scores?.layout_variety ?? "—"}</b></span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select className="bg-bg-soft border border-line rounded-lg text-[12px] px-2 py-1.5"
              value={pkg?.style ?? ""} disabled={busy !== null || !pkg}
              onChange={(e) => e.target.value && pkg &&
                act("style", () => api.generateImages(pkg.job_id, { style: e.target.value }))}>
              <option value="" disabled>Redesign style…</option>
              {styles.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
            <button className="btn btn-ghost" onClick={refresh}><RefreshCw size={15} /></button>
          </div>
        </div>
        {pkg && (
          <div className="flex flex-wrap gap-2 mt-3">
            {ACTIONS.map((a) => (
              <button key={a.key} className="btn btn-ghost text-xs" disabled={busy !== null}
                onClick={() => design(a.key)}>
                {a.icon} {busy === a.key ? "Rendering…" : a.label}
              </button>
            ))}
          </div>
        )}
        <div className="text-[11px] text-ink-faint mt-2">
          All design actions re-render locally — zero Higgsfield credits, Photo Reels only.
        </div>
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {!pkg || !pkg.slides.length ? (
        <EmptyState title="No slides yet" hint="Run the pipeline from the Dashboard first." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {pkg.slides.map((s) => {
            const prompt = pkg.slide_prompts.find((p) => p.slide_number === s.slide_number);
            const img = pkg.generated_images.find((i) => i.slide_number === s.slide_number);
            const fixes = fixesFor(s.slide_number);
            return (
              <div key={s.slide_number} className="glass card-pad flex gap-4">
                <div className="w-[150px] shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={`${api.slideUrl(pkg.job_id, s.slide_number)}?v=${bust}`}
                    alt={`Slide ${s.slide_number}`}
                    className="rounded-lg border border-line bg-black aspect-[9/16] object-contain w-full" />
                </div>
                <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                  <div className="eyebrow">Slide {s.slide_number} · {s.role.replace(/_/g, " ")}</div>
                  <div className="flex flex-wrap gap-1.5 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-teal/10 text-teal border border-teal/25">
                      {img?.motif?.replace(/_/g, " ") ?? "—"}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-white/5 text-ink-faint border border-line">
                      {img?.layout?.replace(/_/g, " ") ?? "—"}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-white/5 text-ink-faint border border-line">
                      {img?.visual_elements?.length ?? 0} elements
                    </span>
                  </div>
                  <button className="text-left text-sm font-semibold hover:text-teal"
                    title="Edit title" onClick={() => editText(s.slide_number, "title", s.title)}>
                    {s.title}
                  </button>
                  <button className="text-left text-[12px] text-ink-muted hover:text-ink"
                    title="Edit body" onClick={() => editText(s.slide_number, "body", s.body)}>
                    {s.body}
                  </button>
                  <div className="text-[10px] text-ink-faint line-clamp-2" title={prompt?.prompt}>
                    {prompt ? `bg prompt: ${prompt.prompt}` : ""}
                  </div>
                  <div className="text-[10px] text-ink-faint">{s.source_note}</div>
                  {fixes.length > 0 && (
                    <div className="text-[10px] text-warn">{fixes.map((f) => <div key={f}>· {f}</div>)}</div>
                  )}
                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    <button className="btn btn-ghost text-xs" disabled={busy !== null}
                      onClick={() => act(`regen${s.slide_number}`,
                        () => api.regenerateSlide(pkg.job_id, s.slide_number))}>
                      <Wand2 size={13} /> {busy === `regen${s.slide_number}` ? "Rendering…" : "Regenerate"}
                    </button>
                    <button className="btn btn-ghost text-xs" disabled={busy !== null}
                      onClick={() => design("change_motif", s.slide_number)}>
                      <Shapes size={13} /> Change Motif
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
