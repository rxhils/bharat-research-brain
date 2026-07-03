"use client";
import { useCallback, useEffect, useState } from "react";
import { Brain, MapPin, Camera, BookOpen, Gavel, ChevronDown, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";

/** Maven Reels Newsroom — creative intelligence for this reel: why this story,
 *  why this footage world, which model per scene, and the Editor-in-Chief verdict.
 *  Reads artifacts 25–29. Read-only, no credits. */
export function CreativeIntelPanel({ jobId }: { jobId: string }) {
  const [ts, setTs] = useState<any>(null);
  const [ls, setLs] = useState<any>(null);
  const [cr, setCr] = useState<any>(null);
  const [pb, setPb] = useState<any>(null);
  const [ei, setEi] = useState<any>(null);
  const [open, setOpen] = useState<string | null>("editor");

  const load = useCallback(() => {
    const g = (f: string, set: (v: any) => void) =>
      fetch(api.artifactUrl(jobId, f)).then((x) => (x.ok ? x.json() : null)).then(set).catch(() => {});
    g("25_trendscout.json", setTs); g("26_location_scout.json", setLs);
    g("27_model_routing_plan.json", setCr); g("28_prompt_bible.json", setPb);
    g("29_editor_in_chief.json", setEi);
  }, [jobId]);
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  if (!ts && !ls && !cr && !ei) return null;

  const Section = ({ id, icon, title, chip, chipTone, children }: any) => (
    <div className="border border-line rounded-lg overflow-hidden">
      <button className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-white/[0.02]"
              onClick={() => setOpen(open === id ? null : id)}>
        {icon}<span className="font-medium">{title}</span>
        {chip && <span className={`chip ml-1 ${chipTone}`}>{chip}</span>}
        <ChevronDown size={14} className={`ml-auto transition-transform ${open === id ? "rotate-180" : ""}`} />
      </button>
      {open === id && <div className="px-3 pb-3 pt-1 text-xs text-ink-muted space-y-1.5">{children}</div>}
    </div>
  );

  return (
    <div className="glass card-pad">
      <div className="eyebrow flex items-center gap-1.5 mb-3"><Brain size={13} /> Creative Intelligence · Maven Reels Newsroom</div>
      <div className="space-y-2">
        {ei && (
          <Section id="editor" icon={<Gavel size={14} className="text-teal" />} title="Editor-in-Chief"
                   chip={ei.passed ? "PASS" : "HOLD"} chipTone={ei.passed ? "border-ok/40 text-ok bg-ok/10" : "border-amber-500/40 text-amber-400 bg-amber-500/10"}>
            <div className="text-ink">{ei.editor_note}</div>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {Object.entries(ei.scores || {}).map(([k, v]: any) => (
                <span key={k} className="chip border-line">{k.replace(/_/g, " ")}: {v}</span>
              ))}
            </div>
            {ei.required_fixes?.length > 0 && <div className="text-amber-400 mt-1">Fixes: {ei.required_fixes.join("; ")}</div>}
            {ei.is_simulation_preview && <div className="text-ink-faint">Simulation preview — realism unverified until real footage.</div>}
          </Section>
        )}
        {ls && (
          <Section id="loc" icon={<MapPin size={14} className="text-teal" />} title="Location Scout" chip={ls.selected_footage_world} chipTone="border-teal/40 text-teal bg-teal/10">
            <div className="text-ink">{ls.why_this_world_fits}</div>
            <div>Style: {Object.entries(ls.shot_style || {}).map(([k, v]: any) => `${k} ${v}`).join(" · ")}</div>
            <div className="text-ink-faint">Refs: {(ls.realistic_visual_references || []).join(" · ")}</div>
          </Section>
        )}
        {cr && (
          <Section id="cam" icon={<Camera size={14} className="text-teal" />} title="Camera Router" chip={`${(cr.per_scene_model_plan||[]).length} shots`} chipTone="border-line text-ink-muted">
            {(cr.per_scene_model_plan || []).map((s: any) => (
              <div key={s.scene_id} className="flex items-center gap-2">
                <span className="text-ink-faint w-14">{s.scene_id}</span>
                <span className="text-ink">{s.selected_model}</span>
                <span className="chip border-line">{s.footage_type}</span>
                <span className={`chip ${s.needs_pricing_confirmation ? "border-amber-500/40 text-amber-400" : "border-ok/40 text-ok"}`}>
                  {s.cost_tier}{s.needs_pricing_confirmation ? " · needs pricing" : ` · ${s.estimated_cost}cr`}
                </span>
              </div>
            ))}
            {cr.unavailable_requested?.length > 0 && <div className="text-ink-faint">Excluded (not in catalog): {cr.unavailable_requested.join(", ")}</div>}
          </Section>
        )}
        {ts && (
          <Section id="trend" icon={<TrendingUp size={14} className="text-teal" />} title="Trendscout" chip={ts.footage_world_detected} chipTone="border-line text-ink-muted">
            <div className="text-ink">{ts.recommended_reel_structure}</div>
            <div>Visual: {ts.recommended_visual_style}</div>
            <div className="text-ink-faint">Avoid: {(ts.ai_slop_traps || []).slice(0, 4).join("; ")}</div>
          </Section>
        )}
        {pb && (
          <Section id="bible" icon={<BookOpen size={14} className="text-teal" />} title="Prompt Bible" chip={`${(pb.shots||[]).length} shots`} chipTone="border-line text-ink-muted">
            <div className="text-ink">{pb.story_summary}</div>
            <div>World: {pb.footage_world} · Style: {pb.reel_style}</div>
            {(pb.shots || []).map((s: any) => (
              <div key={s.shot_id} className="text-ink-faint">{s.shot_id} · {s.purpose} → {s.model} ({s.footage_type})</div>
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}
