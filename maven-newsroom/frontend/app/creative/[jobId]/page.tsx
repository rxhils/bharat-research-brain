"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, EmptyState } from "@/components/ui/Card";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { fmtBytes } from "@/lib/format";

export default function CreativePage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [creative, setCreative] = useState<any>(null);
  const [images, setImages] = useState<any>(null);
  const [arts, setArts] = useState<any[]>([]);
  const [openPrompt, setOpenPrompt] = useState<number | null>(null);

  useEffect(() => {
    fetch(api.artifactUrl(jobId, "03_creative_direction.json")).then((x) => x.ok ? x.json() : null).then(setCreative).catch(() => {});
    fetch(api.artifactUrl(jobId, "04_images.json")).then((x) => x.ok ? x.json() : null).then(setImages).catch(() => {});
    api.artifacts(jobId).then((a) => setArts(a.artifacts.filter((x) => x.name.match(/^slide_\d\.jpg$/)))).catch(() => {});
  }, [jobId]);

  const selected = creative?.selected;
  const dirs = creative?.directions ?? [];
  const jobs = images?.jobs ?? [];

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-5">
      <div>
        <div className="eyebrow">Creative Studio · Art Director + Prompt Forge + Nano Studio</div>
        <h2 className="text-xl font-semibold tracking-tight mt-1">Design system &amp; carousel generation</h2>
      </div>

      {/* direction */}
      {dirs.length > 0 && (
        <div className="grid md:grid-cols-3 gap-3">
          {dirs.map((d: any) => (
            <div key={d.concept_name} className={`glass card-pad ${d.concept_name === selected ? "border-teal/50 shadow-glow" : ""}`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm">{d.concept_name}</span>
                {d.concept_name === selected && <span className="chip border-teal/40 text-teal bg-teal/10">Selected</span>}
              </div>
              <p className="text-xs text-ink-muted mt-2">{d.style}</p>
              <dl className="mt-2 space-y-1 text-[11px] text-ink-faint">
                <div>Background: <span className="text-ink-muted">{d.background}</span></div>
                <div>Type: <span className="text-ink-muted">{d.typography}</span></div>
                <div>Chart: <span className="text-ink-muted">{d.chart_style}</span></div>
              </dl>
            </div>
          ))}
        </div>
      )}

      {/* slide previews */}
      {arts.length === 0 ? <EmptyState title="No generated slides yet" hint="Nano Studio (Higgsfield) produces images in the Claude Code conductor." /> : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {arts.sort((a, b) => a.name.localeCompare(b.name)).map((a, i) => (
            <div key={a.artifact_id} className="glass overflow-hidden">
              <div className="bg-black/30 grid place-items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={api.artifactUrl(jobId, a.name)} alt={a.name} className="w-full object-cover" style={{ aspectRatio: "4/5" }} />
              </div>
              <div className="p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Slide {i + 1}</span>
                  <span className="text-[10px] text-ink-faint">{(a.metadata as any)?.w}×{(a.metadata as any)?.h} · {fmtBytes((a.metadata as any)?.bytes)}</span>
                </div>
                <div className="text-[10px] text-ink-faint mt-1">nano_banana_pro · postprocessed</div>
                {jobs[i] && (
                  <button onClick={() => setOpenPrompt(openPrompt === i ? null : i)} className="btn btn-ghost border-line w-full mt-2 text-xs">
                    {openPrompt === i ? "Hide prompt" : "View prompt"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {openPrompt != null && jobs[openPrompt] && (
        <Card>
          <div className="eyebrow mb-2">Slide {openPrompt + 1} · Prompt Forge output</div>
          <JsonViewer data={{ prompt: jobs[openPrompt].prompt, negative_prompt: jobs[openPrompt].negative_prompt, regenerate_rule: jobs[openPrompt].regenerate_rule }} maxHeight="40vh" />
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <button className="btn btn-ghost border-line" onClick={() => api.regenerateImages(jobId)}>Regenerate All</button>
        <button className="btn btn-primary" onClick={() => location.assign(`/review/${jobId}`)}>Send to Review →</button>
      </div>
      <p className="text-[11px] text-mcp">Regeneration runs Nano Studio (Higgsfield MCP) in the Claude Code conductor — the dashboard queues it and marks the node pending; nothing is faked.</p>
    </div>
  );
}
