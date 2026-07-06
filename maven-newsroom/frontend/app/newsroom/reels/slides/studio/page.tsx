"use client";
/** Photo Reels — Slide Studio (/newsroom/reels/slides/studio). */
import { useEffect, useState } from "react";
import { Palette, RefreshCw, Wand2 } from "lucide-react";
import { EmptyState } from "@/components/ui/Card";
import { photoReelsApi as api } from "@/lib/photoReelsApi";
import { usePhotoReelsLatest } from "@/components/photoReels/shared";

export default function SlideStudio() {
  const { pkg, error, reload, setError } = usePhotoReelsLatest();
  const [styles, setStyles] = useState<string[]>([]);
  const [busy, setBusy] = useState<number | "all" | null>(null);
  const [bust, setBust] = useState(0); // cache-buster after regeneration

  useEffect(() => { api.config().then((c) => setStyles(c.styles)).catch(() => {}); }, []);

  async function regen(n: number, opts?: { title?: string; body?: string; style?: string }) {
    if (!pkg) return;
    setBusy(n); setError(null);
    try { await api.regenerateSlide(pkg.job_id, n, opts); reload(); setBust(Date.now()); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(null);
  }

  async function redesignAll(style: string) {
    if (!pkg) return;
    setBusy("all"); setError(null);
    try { await api.generateImages(pkg.job_id, { style }); reload(); setBust(Date.now()); }
    catch (e) { setError(String((e as Error).message)); }
    setBusy(null);
  }

  function editText(n: number, field: "title" | "body", current: string) {
    const next = window.prompt(`Slide ${n} ${field} (${field === "title" ? "max 7" : "max 18"} words):`, current);
    if (next !== null && next.trim()) void regen(n, { [field]: next.trim() });
  }

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-5">
      <div className="glass card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow flex items-center gap-1.5"><Palette size={13} /> Slide Studio</div>
          <h2 className="text-xl font-semibold tracking-tight mt-1">
            Edit &amp; regenerate slides {pkg ? `· ${pkg.job_id}` : ""}
          </h2>
          <div className="text-[11px] text-ink-faint mt-0.5">
            Text edits + restyling run the local compositor — zero Higgsfield credits.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select className="bg-bg-soft border border-line rounded-lg text-[12px] px-2 py-1.5"
            value={pkg?.style ?? ""} disabled={busy !== null}
            onChange={(e) => e.target.value && redesignAll(e.target.value)}>
            <option value="" disabled>Redesign style…</option>
            {styles.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
          <button className="btn btn-ghost" onClick={reload}><RefreshCw size={15} /></button>
        </div>
      </div>

      {error && <div className="glass card-pad text-sm text-danger">{error}</div>}

      {!pkg || !pkg.slides.length ? (
        <EmptyState title="No slides yet" hint="Run the pipeline from the Dashboard first." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {pkg.slides.map((s) => {
            const prompt = pkg.slide_prompts.find((p) => p.slide_number === s.slide_number);
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
                  <div className="mt-auto flex gap-2 pt-2">
                    <button className="btn btn-ghost text-xs" disabled={busy !== null}
                      onClick={() => regen(s.slide_number)}>
                      <Wand2 size={13} /> {busy === s.slide_number ? "Rendering…" : "Regenerate"}
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
