"use client";
import { useCallback, useEffect, useState } from "react";
import { Type, Loader2, Sparkles, AlignVerticalJustifyCenter, RefreshCw, ArrowUp, Wand2 } from "lucide-react";
import { api } from "@/lib/api";

/** Text Layer review room — voice/subtitle alignment, typography + kinetic
 *  scores, and text-only reassembly actions. NONE of these spend Higgsfield
 *  credits: they reuse the existing clips + voiceover and only rebuild overlays. */
export function TextLayerPanel({ jobId }: { jobId: string }) {
  const [tq, setTq] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [align, setAlign] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(() => {
    const get = (f: string, set: (v: any) => void) =>
      fetch(api.artifactUrl(jobId, f)).then((x) => (x.ok ? x.json() : null)).then(set).catch(() => {});
    get("24_text_quality.json", setTq);
    get("21_kinetic_text_plan.json", setPlan);
    get("20_text_alignment.json", setAlign);
  }, [jobId]);

  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  async function act(action: string, moveUp = false, label = "") {
    setBusy(action); setNote(null);
    try {
      const r = await api.improveText(jobId, action, moveUp);
      setNote(r.message || `${label} done — text ${r.text_verdict ?? ""}.`);
      setTimeout(load, 800);
    } catch { setNote("Text reassembly failed — see backend logs."); }
    finally { setBusy(null); }
  }

  const s = tq?.scores ?? {};
  const hook = plan?.hook_text;
  const subs: any[] = plan?.subtitles ?? [];
  const transcript = (align?.segments ?? []).map((g: any) => g.spoken_text).join(" ");

  const B = ({ id, mv, label, icon }: { id: string; mv?: boolean; label: string; icon: React.ReactNode }) => (
    <button className="btn btn-ghost text-xs" disabled={!!busy} onClick={() => act(id, mv, label)}>
      {busy === id ? <Loader2 size={13} className="animate-spin" /> : icon} {label}
    </button>
  );

  return (
    <div className="glass card-pad">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="eyebrow flex items-center gap-1.5"><Type size={13} /> Text Layer · voice-synced kinetic subtitles</div>
        {tq && (
          <span className={`chip ${tq.passed ? "border-ok/40 text-ok bg-ok/10" : "border-amber-500/40 text-amber-400 bg-amber-500/10"}`}>
            {tq.verdict}
          </span>
        )}
      </div>

      {tq ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-center">
            {[["Voice match", s.text_voice_match_score, 90], ["Sync", s.subtitle_sync_score, 90],
              ["Readability", s.subtitle_readability_score, 90], ["Overall", s.overall_text_quality_score, 90]].map(
              ([label, v, g]: any) => (
                <div key={label} className="rounded-lg border border-line py-2">
                  <div className={`text-lg font-semibold ${v >= g ? "text-ok" : "text-amber-400"}`}>{v ?? "—"}</div>
                  <div className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
                </div>
              ))}
          </div>

          {hook?.text && (
            <div className="mb-2 text-sm">
              <span className="text-ink-faint text-xs">Hook overlay: </span>
              <span className="font-semibold">“{hook.text}”</span>
              {hook.emphasis_words?.length > 0 && <span className="text-teal"> · {hook.emphasis_words.join(", ")}</span>}
            </div>
          )}

          {transcript && (
            <div className="mb-2 text-[11px] text-ink-muted"><span className="text-ink-faint">Voiceover: </span>{transcript}</div>
          )}

          {subs.length > 0 && (
            <div className="mb-3 max-h-40 overflow-y-auto rounded-lg border border-line divide-y divide-line/60">
              {subs.map((c, i) => (
                <div key={i} className="flex items-baseline gap-2 px-2.5 py-1 text-xs">
                  <span className="text-ink-faint tabular-nums w-16 shrink-0">{c.start.toFixed(1)}–{c.end.toFixed(1)}s</span>
                  <span className="flex-1">{(c.lines ?? [c.text]).join(" ")}</span>
                  {c.emphasis_words?.length > 0 && <span className="text-teal text-[10px]">{c.emphasis_words[0]}</span>}
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-1.5">
            <B id="improve_text" label="Improve Text" icon={<Wand2 size={13} />} />
            <B id="resync" label="Resync Subtitles" icon={<RefreshCw size={13} />} />
            <B id="make_viral" label="Make Text More Viral" icon={<Sparkles size={13} />} />
            <B id="move_up" mv label="Move Subtitles Up" icon={<ArrowUp size={13} />} />
            <B id="reassemble_text" label="Reassemble Text Only" icon={<AlignVerticalJustifyCenter size={13} />} />
          </div>
          <div className="text-[10px] text-ink-faint mt-2">These reuse the existing clips + voiceover — zero Higgsfield credits.</div>
          {note && <div className="text-[11px] text-teal mt-1.5">{note}</div>}
        </>
      ) : (
        <div className="text-xs text-ink-muted">Text layer builds when the reel is assembled. Generate the reel first, then Improve Text here.</div>
      )}
    </div>
  );
}
