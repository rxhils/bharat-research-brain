"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { EASE, useReducedMotionSafe } from "./motion";
import type { MavenSource } from "@/lib/maven-types";

const INLINE_COUNT = 6;

// Monogram derived from the clean label — a favicon-shaped mark without any
// external image request (house discipline: hand-built, no remote assets).
function Monogram({ label }: { label: string }) {
  const ch = (label.replace(/[^A-Za-z0-9]/, "").charAt(0) || "•").toUpperCase();
  return (
    <span
      className="grid h-5 w-5 shrink-0 place-items-center rounded-[5px] border border-white/10 bg-white/[0.04] text-[10px] font-semibold text-muted"
      aria-hidden
    >
      {ch}
    </span>
  );
}

// Maps a raw source domain to a clean, human label. Only ever shown to the user, so this must
// never surface a provider/backend name (Tavily, SearXNG, Yahoo, API, env, scraper, etc.) -
// domains here are always the publisher's own domain, not the retrieval provider.
function labelFor(s: MavenSource): string {
  const d = (s.domain || s.name || "").toLowerCase();
  if (/nseindia\.com/.test(d)) return "NSE";
  if (/bseindia\.com/.test(d)) return "BSE";
  if (/rbi\.org\.in/.test(d)) return "RBI";
  if (/sebi\.gov\.in/.test(d)) return "SEBI";
  if (/moneycontrol/.test(d)) return "Moneycontrol";
  if (/livemint|(^|\W)mint\./.test(d)) return "Mint";
  if (/businessline|thehindubusinessline/.test(d)) return "BusinessLine";
  if (/economictimes/.test(d)) return "Economic Times";
  if (/business-standard/.test(d)) return "Business Standard";
  if (/reuters/.test(d)) return "Reuters";
  if (/bloomberg/.test(d)) return "Bloomberg";
  if (/cnbctv18/.test(d)) return "CNBC-TV18";
  if (/ndtvprofit/.test(d)) return "NDTV Profit";
  if (s.type === "market_data") return "Market data";
  if (s.type === "analysis") return "Maven analysis";
  if (/investor|(^|\.)ir\./.test(d)) return "Company IR";
  const seg = d.replace(/^www\./, "").split(".")[0];
  return seg ? seg.charAt(0).toUpperCase() + seg.slice(1) : s.name || "Source";
}

function bucketFor(s: MavenSource, label: string): string {
  if (s.type === "analysis") return "Maven analysis";
  if (s.type === "market_data") return "Data sources";
  if (label === "Company IR") return "Company / Investor Relations";
  if (["NSE", "BSE", "RBI", "SEBI"].includes(label)) return "Official filings";
  if (s.confidence === "retrieved") return "News and market context";
  return "Other";
}
const BUCKET_ORDER = ["Official filings", "Company / Investor Relations", "News and market context", "Data sources", "Maven analysis", "Other"];

function ConfidenceBadge({ confidence }: { confidence?: string }) {
  const base = "rounded-full border px-1.5 py-px text-[9px] font-medium uppercase tracking-wider";
  if (confidence === "verified") return <span className={base + " border-emerald/30 bg-emerald/10 text-emerald"}>Verified</span>;
  if (confidence === "retrieved") return <span className={base + " border-hairline text-muted"}>Retrieved</span>;
  if (confidence === "analysis_only") return <span className={base + " border-hairline text-dim"}>Analysis</span>;
  return null;
}

function SourceRow({ s }: { s: MavenSource }) {
  const label = labelFor(s);
  const meta = s.date || s.recency;
  const domain = (s.domain || "").replace(/^www\./, "");
  const inner = (
    <div className="flex items-start gap-2">
      <Monogram label={label} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
          <span className="text-[11px] font-medium text-ink">{label}</span>
          <ConfidenceBadge confidence={s.confidence} />
          {meta && <span className="text-[10px] text-dim">{meta}</span>}
        </div>
        {s.title && <div className="mt-0.5 text-[11px] leading-snug text-ink/75">{s.title}</div>}
        {s.snippet && <div className="mt-0.5 text-[10px] leading-snug text-dim line-clamp-2">{s.snippet.slice(0, 180)}</div>}
        {domain && <div className="mt-1 truncate font-mono text-[9px] tracking-tight text-dim/80">{domain}</div>}
      </div>
    </div>
  );
  // real <a> → :active fires for PRESS; color fade needs the combined transition so PRESS doesn't clobber it
  return s.url ? (
    <a href={s.url} target="_blank" rel="noopener noreferrer"
      className={`block rounded-lg border border-hairline bg-white/[0.02] p-2.5 motion-safe:transition-[color,border-color,background-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.98] hover:border-emerald/30 hover:bg-white/[0.04] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60`}>{inner}</a>
  ) : (
    <div className="rounded-lg border border-hairline bg-white/[0.01] p-2.5 opacity-70">{inner}</div>
  );
}

export function MavenSourcePanel({ sources }: { sources: MavenSource[] }) {
  const reduce = useReducedMotionSafe();
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;

  const inline = sources.slice(0, INLINE_COUNT);
  const extra = sources.length - inline.length;

  const groups = new Map<string, MavenSource[]>();
  for (const s of sources) {
    const label = labelFor(s);
    const key = bucketFor(s, label);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10px] uppercase tracking-wider text-dim">Sources</span>
        {inline.map((s, i) => {
          const label = labelFor(s);
          const meta = s.date || s.recency;
          const dot = s.confidence === "verified" ? "bg-emerald" : s.confidence === "retrieved" ? "bg-white/40" : "bg-white/20";
          const chip = (
            <span className="inline-flex items-center gap-1.5">
              <span className={"h-1 w-1 rounded-full " + dot} aria-hidden />
              {label}{meta ? " · " + meta : ""}
            </span>
          );
          return s.url ? (
            <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className={`rounded-md border border-hairline bg-white/[0.03] px-2.5 py-1 text-[11px] text-muted motion-safe:transition-[color,border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/40 hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60`}>{chip}</a>
          ) : (
            <span key={i} className="rounded-md border border-hairline bg-white/[0.03] px-2.5 py-1 text-[11px] text-muted">{chip}</span>
          );
        })}
        {extra > 0 && (
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
            className={`rounded-md border border-hairline bg-white/[0.03] px-2.5 py-1 text-[11px] text-emerald motion-safe:transition-[border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60`}>
            {open ? "Show fewer" : `+${extra} more source${extra === 1 ? "" : "s"}`}
          </button>
        )}
        {extra === 0 && sources.length > INLINE_COUNT - 2 && (
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className={`rounded-md border border-hairline bg-white/[0.03] px-2.5 py-1 text-[11px] text-emerald motion-safe:transition-[border-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] hover:border-emerald/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60`}>
            {open ? "Hide details" : "View all sources"}
          </button>
        )}
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: EASE }}
            className="overflow-hidden">
            <div className="mt-3 space-y-3.5 border-t border-hairline pt-3.5">
              {BUCKET_ORDER.filter((b) => groups.has(b)).map((bucket) => (
                <div key={bucket}>
                  <div className="mb-1.5 text-[10px] uppercase tracking-wider text-dim">{bucket}</div>
                  <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                    {groups.get(bucket)!.map((s, i) => <SourceRow key={i} s={s} />)}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
