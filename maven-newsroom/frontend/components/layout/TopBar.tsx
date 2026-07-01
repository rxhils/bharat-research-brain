"use client";
import { useEffect, useState } from "react";
import { CalendarDays, CircleDot, Clock } from "lucide-react";
import { api } from "@/lib/api";
import type { Job, Meta } from "@/lib/types";
import { statusMeta } from "@/lib/constants";

export function TopBar() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [latest, setLatest] = useState<Job | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.jobs().then((r) => setLatest(r.jobs[0] ?? null)).catch(() => {});
  }, []);

  const marketOpen = meta?.market.open;
  const js = latest ? statusMeta(latest.status) : null;

  return (
    <header className="sticky top-0 z-20 h-[68px] border-b border-line bg-bg/70 backdrop-blur-md">
      <div className="h-full px-6 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[17px] font-semibold tracking-tight leading-none">
            Maven Newsroom OS
          </h1>
          <p className="text-xs text-ink-muted mt-1 truncate">
            Post-market Indian market intelligence engine
          </p>
        </div>

        <div className="flex items-center gap-2.5 text-sm">
          <div className="chip border-line text-ink-muted">
            <CalendarDays size={13} className="text-ink-faint" />
            {meta?.date_ist ?? "—"}
          </div>
          <div
            className={`chip ${marketOpen ? "border-ok/40 text-ok bg-ok/10" : "border-line text-ink-muted"}`}
            title={meta?.market.reason}
          >
            <CircleDot size={13} className={marketOpen ? "text-ok" : "text-ink-faint"} />
            {marketOpen ? "Market Open" : `Market Closed${meta?.market.reason ? ` · ${meta.market.reason}` : ""}`}
          </div>
          <div className="chip border-line text-ink-muted">
            <Clock size={13} className="text-teal" />
            Next run {meta?.next_run ?? "5:00 PM IST"}
          </div>
          {latest && js && (
            <div className={`chip ${js.ring} ${js.text} bg-white/[0.03]`}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: js.color }} />
              {latest.job_id} · {js.label}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
