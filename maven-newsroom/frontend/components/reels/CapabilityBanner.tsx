"use client";
import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Info, Settings } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";

type Caps = Awaited<ReturnType<typeof api.reelCapabilities>>;

/** Reads /api/reels/capabilities and renders the exact backend readiness state.
 *  Never says "Claude Code" — every gap names the env var to set in Settings. */
export function CapabilityBanner() {
  const [caps, setCaps] = useState<Caps | null>(null);
  useEffect(() => {
    const load = () => api.reelCapabilities().then(setCaps).catch(() => {});
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  if (!caps) return null;

  const real = caps.can_generate_real_clips;
  const publish = caps.composio_available;
  const tone = real && publish ? "ok" : real ? "info" : "warn";
  const Icon = tone === "ok" ? CheckCircle2 : tone === "info" ? Info : AlertTriangle;

  const headline =
    real && publish
      ? "Production ready: research, Higgsfield generation, TTS, ffmpeg and Composio are configured."
      : real && !publish
      ? "Generation ready. Instagram publishing (Composio) is not connected."
      : "Simulation mode: Reels run end-to-end with simulated clips. Add Higgsfield credentials for real animated clips.";

  const ring =
    tone === "ok" ? "border-ok/40 bg-ok/[0.06]"
    : tone === "info" ? "border-teal/40 bg-teal/[0.06]"
    : "border-amber-500/40 bg-amber-500/[0.06]";
  const color =
    tone === "ok" ? "text-ok" : tone === "info" ? "text-teal" : "text-amber-400";

  return (
    <div className={`glass card-pad mb-4 border ${ring}`}>
      <div className="flex items-start gap-3">
        <Icon size={18} className={`${color} mt-0.5 shrink-0`} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{headline}</div>
          <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
            <Cap ok={caps.research_provider_available} label={`Research (${caps.research_providers.join(", ") || "none"})`} />
            <Cap ok={caps.higgsfield_available} label="Higgsfield" />
            <Cap ok={caps.voiceover_production_ready} label={`Voiceover (${caps.tts_mode})`} soft={!caps.voiceover_production_ready} />
            <Cap ok={caps.ffmpeg_available} label="Assembly (ffmpeg)" />
            <Cap ok={caps.composio_available} label="Publishing (Composio)" />
          </div>
          {caps.missing.length > 0 && (
            <ul className="mt-2 space-y-1">
              {caps.missing.map((m) => (
                <li key={m.capability} className="text-[11px] text-ink-muted flex items-start gap-1.5">
                  <span className="text-amber-400">•</span>{m.message}
                </li>
              ))}
            </ul>
          )}
        </div>
        <Link href="/settings" className="btn btn-ghost shrink-0 text-xs"><Settings size={13} /> Settings</Link>
      </div>
    </div>
  );
}

function Cap({ ok, label, soft }: { ok: boolean; label: string; soft?: boolean }) {
  const cls = ok ? "border-ok/40 text-ok bg-ok/10"
    : soft ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
    : "border-line text-ink-faint";
  return <span className={`chip ${cls}`}>{ok ? "✓" : soft ? "~" : "✗"} {label}</span>;
}
