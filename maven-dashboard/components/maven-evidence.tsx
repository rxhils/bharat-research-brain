"use client";
import { useState } from "react";
import type { MavenEvidenceSummary, MavenChecklistItem } from "@/lib/maven-types";

const COVERAGE: Record<string, { label: string; dot: string; text: string }> = {
  strong: { label: "Strong coverage", dot: "bg-emerald", text: "text-emerald" },
  partial: { label: "Partial coverage", dot: "bg-gold", text: "text-gold-soft" },
  thin: { label: "Thin coverage", dot: "bg-amber", text: "text-amber" },
  unavailable: { label: "Coverage unavailable", dot: "bg-white/30", text: "text-dim" },
};

function depthLabel(depth?: string, budget?: number): string | null {
  if (depth === "deep") return budget ? `${budget}-source research pack` : "Deep research pack";
  if (depth === "standard") return "Standard evidence pack";
  if (depth === "light") return "Quick context pack";
  return null;
}

function Pill({ children, tone = "muted" }: { children: React.ReactNode; tone?: "emerald" | "muted" | "dim" }) {
  const cls = tone === "emerald" ? "border-emerald/30 bg-emerald/10 text-emerald" : tone === "dim" ? "border-hairline text-dim" : "border-hairline text-muted";
  return <span className={"rounded-full border px-2 py-0.5 text-[10px] leading-relaxed " + cls}>{children}</span>;
}

export function MavenEvidenceSummaryCard({ evidence }: { evidence?: MavenEvidenceSummary }) {
  if (!evidence) return null;
  const { sourceCount = 0, verifiedSourceCount = 0, retrievedSourceCount = 0, analysisOnlySourceCount = 0, evidenceDepth, sourceBudget, coverageStatus, latestPeriodFound } = evidence;
  if (sourceCount === 0 && !evidenceDepth) return null;
  const depth = depthLabel(evidenceDepth, sourceBudget);
  const cov = coverageStatus ? COVERAGE[coverageStatus] : null;

  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-1.5 rounded-xl border border-hairline bg-white/[0.02] px-3.5 py-2.5">
      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-dim">Evidence</span>
      {sourceCount > 0 && <Pill>{sourceCount} source{sourceCount === 1 ? "" : "s"} reviewed</Pill>}
      {verifiedSourceCount > 0 && <Pill tone="emerald">{verifiedSourceCount} verified</Pill>}
      {retrievedSourceCount > 0 && <Pill>{retrievedSourceCount} retrieved</Pill>}
      {analysisOnlySourceCount > 0 && <Pill tone="dim">{analysisOnlySourceCount} analysis</Pill>}
      {depth && <Pill tone="dim">{depth}</Pill>}
      {latestPeriodFound && <Pill tone="dim">Latest period: {latestPeriodFound}</Pill>}
      {cov && (
        <span className={"ml-auto inline-flex items-center gap-1.5 text-[10px] " + cov.text}>
          <span className={"h-1.5 w-1.5 rounded-full " + cov.dot} />{cov.label}
        </span>
      )}
    </div>
  );
}

export function MavenLatestDataChecklist({ items }: { items?: MavenChecklistItem[] }) {
  const [open, setOpen] = useState(false);
  const list = (items ?? []).filter((i) => i.status !== "not_required");
  if (!list.length) return null;
  const foundCount = list.filter((i) => i.status === "found").length;
  const preview = list.slice(0, 4);

  return (
    <div className="mt-2 rounded-xl border border-hairline bg-white/[0.015] px-3.5 py-2.5">
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 text-left">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-dim">Latest data checked</span>
        <span className="text-[10px] text-dim">{foundCount}/{list.length} found</span>
        <span className="ml-auto text-[10px] text-emerald">{open ? "Hide" : "Show"}</span>
      </button>
      {!open && (
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
          {preview.map((i) => (
            <span key={i.item} className="inline-flex items-center gap-1 text-[10px] text-dim">
              <span className={"h-1 w-1 rounded-full " + (i.status === "found" ? "bg-emerald" : "bg-white/25")} />
              {i.label}
            </span>
          ))}
          {list.length > preview.length && <span className="text-[10px] text-dim">+{list.length - preview.length} more</span>}
        </div>
      )}
      {open && (
        <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
          {list.map((i) => (
            <div key={i.item} className="flex items-center gap-1.5 text-[10px] text-ink/70">
              <span className={"h-1.5 w-1.5 shrink-0 rounded-full " + (i.status === "found" ? "bg-emerald" : "bg-white/25")} />
              <span className="text-ink/85">{i.label}:</span>
              <span className={i.status === "found" ? "text-emerald" : "text-dim"}>{i.status === "found" ? (i.latestPeriod ? `found (${i.latestPeriod})` : "found") : "unavailable"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
