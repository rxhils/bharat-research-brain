"use client";
import { useEffect, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";

export default function SettingsPage() {
  const [s, setS] = useState<any>(null);
  useEffect(() => { api.settings().then(setS).catch(() => {}); }, []);
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
