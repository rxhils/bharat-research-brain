"use client";
import { motion } from "framer-motion";
import { EASE, useReducedMotionSafe } from "./motion";
import { MavenChartRenderer } from "./maven-charts";
import { MavenEvidenceSummaryCard, MavenLatestDataChecklist } from "./maven-evidence";
import { MavenSourcePanel } from "./maven-source-panel";
import type { MavenAskResponse, MavenReportSection, MavenBlock, MavenReportMetric } from "@/lib/maven-types";

function blockGlyph(type: string): { dot: string; label: string } {
  const t = (type || "").toLowerCase();
  if (t === "risk") return { dot: "bg-amber shadow-[0_0_8px_rgba(251,191,36,0.7)]", label: "text-amber" };
  if (t === "takeaway") return { dot: "bg-gold shadow-[0_0_8px_rgba(201,169,97,0.7)]", label: "text-gold-soft" };
  if (t === "data") return { dot: "bg-emerald-deep shadow-[0_0_8px_rgba(16,185,129,0.7)]", label: "text-emerald" };
  return { dot: "bg-white/50", label: "text-muted" };
}

// Compact outline entries - short labels distinct from the full section titles.
const OUTLINE_LABEL: Record<string, string> = {
  business_overview: "Business", price_action: "Price", latest_results: "Results", catalysts: "Catalysts",
  financial_metrics: "Metrics", valuation: "Metrics", shareholding: "Ownership", peer_comparison: "Peers",
  sector_macro: "Sector", risks: "Risks", watch_items: "Watch", evidence: "Evidence",
};

function MetricPill({ m }: { m: MavenReportMetric }) {
  const badge = m.confidence === "verified" || m.confidence === "cross_verified" ? "border-emerald/30 bg-emerald/10 text-emerald" : "border-hairline text-muted";
  return (
    <div className="rounded-lg border border-hairline bg-white/[0.02] px-2.5 py-2">
      <div className="truncate text-[10px] uppercase tracking-wider text-dim">{m.label}{m.period ? ` · ${m.period}` : ""}</div>
      <div className="mt-1.5 flex items-center justify-between gap-1.5">
        <span className="tnum text-[0.95rem] font-medium leading-none text-ink">{m.value}{m.unit ?? ""}</span>
        <span className={"shrink-0 rounded-full border px-1.5 py-px text-[8px] uppercase tracking-wider " + badge}>{m.confidence === "cross_verified" ? "cross-verified" : m.confidence}</span>
      </div>
    </div>
  );
}

function ReportBlock({ b }: { b: MavenBlock }) {
  const g = blockGlyph(b.type);
  return (
    <div className="rounded-lg border border-hairline bg-white/[0.015] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={"h-1.5 w-1.5 shrink-0 rounded-full " + g.dot} />
        <span className={"text-[9px] font-semibold uppercase tracking-[0.14em] " + g.label}>{b.type}</span>
        {b.title && <span className="text-[0.85rem] font-medium text-ink">{b.title}</span>}
      </div>
      <p className="mt-2 pl-3.5 text-[0.85rem] leading-[1.65] text-ink/70">{b.body}</p>
    </div>
  );
}

function ReportSectionView({ section, reduce }: { section: MavenReportSection; reduce: boolean }) {
  return (
    <motion.section id={`report-${section.id}`} className="scroll-mt-24 rounded-2xl border border-hairline bg-white/[0.015] p-4 sm:p-5"
      initial={reduce ? { opacity: 1 } : { opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.45, ease: EASE }}>
      <h4 className="text-balance font-serif text-[1.2rem] leading-snug tracking-[-0.01em] text-ink">{section.title}</h4>
      {section.summary && <p className="mt-2 text-[0.88rem] leading-[1.7] text-ink/75">{section.summary}</p>}

      {!!section.metrics?.length && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {section.metrics.map((m, i) => <MetricPill key={i} m={m} />)}
        </div>
      )}

      {!!section.charts?.length && <div className="mt-3"><MavenChartRenderer charts={section.charts} /></div>}

      {!!section.blocks?.length && (
        <div className="mt-3 space-y-2">
          {section.blocks.map((b, i) => <ReportBlock key={i} b={b} />)}
        </div>
      )}

      {!!section.sources?.length && <MavenSourcePanel sources={section.sources} />}

      {!!section.limitations?.length && (
        <div className="mt-2.5 text-[10px] leading-snug text-dim">Limitations: {section.limitations.join("; ")}</div>
      )}
    </motion.section>
  );
}

export function MavenReportCard({ a, onFollow }: { a: MavenAskResponse; onFollow: (q: string) => void }) {
  const reduce = useReducedMotionSafe();
  const sections = a.reportSections ?? [];
  const followUps = a.followUps ?? [];

  function scrollTo(id: string) {
    document.getElementById(`report-${id}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  return (
    <motion.div initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: EASE }}>
      <div className="rounded-2xl bg-gradient-to-b from-gold/25 via-white/[0.06] to-transparent p-px">
        <div className="relative overflow-hidden rounded-2xl bg-panel/90 p-5 backdrop-blur-xl sm:p-7">
          <span className="pointer-events-none absolute -right-24 -top-28 h-56 w-56 rounded-full bg-gold/[0.08] blur-3xl" aria-hidden />

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.26em] text-dim">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_8px_rgba(52,211,153,0.9)]" />Maven
            </div>
            <span className="shrink-0 rounded-md bg-gold/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-gold-soft">Deep Research</span>
          </div>

          <h3 className="mt-3.5 text-balance font-serif text-[1.5rem] leading-[1.2] tracking-[-0.01em] text-ink sm:text-[1.75rem]">{a.reportTitle ?? a.headline}</h3>
          {(a.reportSummary ?? a.summary) && <p className="mt-3 text-[0.95rem] leading-[1.7] text-ink/75">{a.reportSummary ?? a.summary}</p>}

          <MavenEvidenceSummaryCard evidence={a.evidence} />
          <MavenLatestDataChecklist items={a.latestDataChecklist} />

          {sections.length > 0 && (
            <div className="mt-5 flex flex-wrap items-center gap-1.5 border-y border-hairline py-3">
              <span className="mr-1 text-[10px] uppercase tracking-wider text-dim">Sections</span>
              {sections.map((s) => (
                <button key={s.id} type="button" onClick={() => scrollTo(s.id)}
                  className="rounded-full border border-hairline px-2.5 py-1 text-[11px] text-muted motion-safe:transition-[color,border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/40 hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60">
                  {OUTLINE_LABEL[s.kind] ?? s.title}
                </button>
              ))}
            </div>
          )}

          <div className="mt-5 space-y-4">
            {sections.map((s) => <ReportSectionView key={s.id} section={s} reduce={!!reduce} />)}
          </div>

          {followUps.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2 border-t border-hairline pt-5">
              {followUps.map((f) => (
                <button key={f} type="button" onClick={() => onFollow(f)} className="group inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white/[0.02] px-3.5 py-1.5 text-xs text-muted motion-safe:transition-[color,border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/45 hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60">
                  {f}<span className="text-emerald opacity-0 transition-[transform,opacity] duration-300 group-hover:translate-x-0.5 group-hover:opacity-100" aria-hidden>&rarr;</span>
                </button>
              ))}
            </div>
          )}

          {a.disclaimer && a.disclaimerLevel !== "none" && (
            <div className="mt-4 border-t border-hairline pt-4 text-[10px] leading-relaxed text-dim">{a.disclaimer}</div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
