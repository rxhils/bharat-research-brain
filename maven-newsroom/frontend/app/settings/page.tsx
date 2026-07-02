"use client";
import { useEffect, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";

export default function SettingsPage() {
  const [s, setS] = useState<any>(null);
  const [caps, setCaps] = useState<Awaited<ReturnType<typeof api.reelCapabilities>> | null>(null);
  useEffect(() => { api.settings().then(setS).catch(() => {}); }, []);
  useEffect(() => { api.reelCapabilities().then(setCaps).catch(() => {}); }, []);
  if (!s) return <div className="px-6 py-8 max-w-4xl mx-auto text-ink-faint">Loading settings…</div>;

  const integ = s.integrations ?? {};
  const th = s.thresholds ?? {};

  return (
    <div className="px-6 py-6 max-w-4xl mx-auto space-y-4">
      <div><div className="eyebrow">Settings</div><h2 className="text-xl font-semibold tracking-tight mt-1">Schedule, thresholds &amp; integrations</h2></div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <div className="eyebrow mb-3">Closing Bell schedule</div>
          <dl className="space-y-2 text-sm">
            <Row k="Run time">{s.schedule_label} · Mon–Fri</Row>
            <Row k="Run name">{s.run_name}</Row>
            <Row k="Trigger">{s.trigger_agent}</Row>
            <Row k="Trading-day check">{s.trading_day_check_enabled ? "Enabled" : "Off"}</Row>
            <Row k="Auto-publish">{s.auto_publish_enabled ? "Enabled" : "Off"}</Row>
            <Row k="Approval required">{s.human_approval_required ? "Yes" : "No"}</Row>
          </dl>
        </Card>
        <Card>
          <div className="eyebrow mb-3">Quality thresholds</div>
          <dl className="space-y-2 text-sm">
            <Row k="Content">≥ {th.content}</Row>
            <Row k="Design">≥ {th.design}</Row>
            <Row k="Compliance">≥ {th.compliance}</Row>
          </dl>
          <div className="eyebrow mt-4 mb-2">Storage</div>
          <dl className="space-y-2 text-xs text-ink-muted mono">
            <div className="truncate">out: {s.output_folder}</div>
            <div className="truncate">db: {s.database_path}</div>
          </dl>
        </Card>
      </div>

      <Card>
        <div className="eyebrow mb-3">Integrations &amp; MCP status</div>
        <div className="grid sm:grid-cols-2 gap-2.5">
          {Object.entries(integ).map(([k, v]: any) => {
            const ok = v?.status === "connected";
            return (
              <div key={k} className="flex items-center justify-between rounded-lg border border-line px-3 py-2.5">
                <div>
                  <div className="text-sm font-medium capitalize">{k}</div>
                  <div className="text-[11px] text-ink-faint">{v?.via || v?.account || v?.model || ""}</div>
                </div>
                <span className={`chip ${ok ? "border-ok/40 text-ok bg-ok/10" : "border-line text-ink-faint"}`}>
                  {ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />} {v?.status}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {caps && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="eyebrow">Reels — provider status</div>
            <span className={`chip ${caps.generation_mode === "real" ? "border-ok/40 text-ok bg-ok/10" : "border-teal/40 text-teal bg-teal/10"}`}>
              Generation mode: {caps.generation_mode}
            </span>
          </div>
          <div className="grid sm:grid-cols-2 gap-2.5">
            <StatusRow label="Research provider" detail={caps.research_providers.join(", ") || "none"} ok={caps.research_provider_available} />
            <StatusRow label="Higgsfield (real clips)" detail={caps.higgsfield_available ? "HIGGSFIELD_API_KEY set" : "HIGGSFIELD_API_KEY / SECRET missing"} ok={caps.higgsfield_available} />
            <StatusRow label="Voiceover / TTS" detail={caps.tts_mode} ok={caps.voiceover_production_ready} soft={!caps.voiceover_production_ready} />
            <StatusRow label="Assembly (ffmpeg)" detail={caps.ffmpeg_available ? "installed" : "not on PATH"} ok={caps.ffmpeg_available} />
            <StatusRow label="Composio (publishing)" detail={caps.composio_available ? "connected" : "COMPOSIO_API_KEY missing"} ok={caps.composio_available} />
            <StatusRow label="Content engine" detail={caps.content_engine} ok={caps.llm_provider_available} />
          </div>
          {caps.missing.length > 0 && (
            <ul className="mt-3 space-y-1 text-[11px] text-ink-muted">
              {caps.missing.map((m) => <li key={m.capability}>• {m.message}</li>)}
            </ul>
          )}
          <p className="text-[11px] text-ink-faint mt-3">Secret values are never shown — only connected / missing. Set keys as environment variables and restart the backend.</p>
        </Card>
      )}

      <Card>
        <div className="eyebrow mb-2">Brand</div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            {(s.brand?.palette ?? []).map((c: string) => <span key={c} className="h-7 w-7 rounded-md border border-line" style={{ background: c }} title={c} />)}
          </div>
          <div className="text-sm text-ink-muted">{s.brand?.name} · {s.brand?.handle} · {s.brand?.site}</div>
        </div>
      </Card>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="flex gap-3"><dt className="w-36 shrink-0 text-ink-faint text-xs pt-0.5">{k}</dt><dd className="text-ink-muted">{children}</dd></div>;
}

function StatusRow({ label, detail, ok, soft }: { label: string; detail: string; ok: boolean; soft?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-line px-3 py-2.5">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-[11px] text-ink-faint">{detail}</div>
      </div>
      <span className={`chip ${ok ? "border-ok/40 text-ok bg-ok/10" : soft ? "border-amber-500/40 text-amber-400 bg-amber-500/10" : "border-line text-ink-faint"}`}>
        {ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />} {ok ? "ready" : soft ? "preview only" : "missing"}
      </span>
    </div>
  );
}
