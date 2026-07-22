"use client";
import { useSyncExternalStore } from "react";
import type { Quote, SectorPerf } from "@/lib/maven/types";

// Single source of truth for the chat page's live market snapshot.
//
// MarketTicker is the ONLY fetcher (it already polls /api/market/ticker). It
// publishes each parsed payload here; the Hero status line and the suggestion
// cards subscribe. No component polls a second time - one fetch, many readers.
//
// The store starts null and stays null until the first real payload lands, so
// every consumer can honestly omit its data instead of inventing a placeholder.

export type MarketSnapshot = {
  indices: Quote[];
  sectors: SectorPerf[];
  asOf: string | null;
};

export type StatTone = "emerald" | "rose";

let current: MarketSnapshot | null = null;
const listeners = new Set<() => void>();

/** Called by MarketTicker after each successful fetch. */
export function publishMarketSnapshot(snap: MarketSnapshot): void {
  current = snap;
  for (const l of listeners) l();
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => { listeners.delete(cb); };
}
function getSnapshot(): MarketSnapshot | null { return current; }
function getServerSnapshot(): MarketSnapshot | null { return null; } // stable SSR value: nothing fetched yet

/** Read the shared snapshot. `null` until MarketTicker's first payload arrives. */
export function useMarketSnapshot(): MarketSnapshot | null {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

// ---- pure selectors (return null when the datum genuinely isn't present) ----

export function findIndex(snap: MarketSnapshot | null, label: string): Quote | null {
  if (!snap) return null;
  const l = label.toLowerCase();
  return snap.indices.find((q) => q.label.toLowerCase() === l) ?? null;
}

export function findSector(snap: MarketSnapshot | null, name: string): SectorPerf | null {
  if (!snap) return null;
  const l = name.toLowerCase();
  return snap.sectors.find((s) => s.name.toLowerCase() === l) ?? null;
}

export function fmtSignedPct(n: number | null | undefined): string | null {
  if (n == null || !isFinite(n)) return null;
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

export function fmtIndexValue(n: number | null | undefined): string | null {
  if (n == null || !isFinite(n)) return null;
  return n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtIstTime(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" });
}

/** Resolve a suggestion's optional stat descriptor against the live snapshot. */
export function resolveStat(
  snap: MarketSnapshot | null,
  stat: { kind: "index" | "sector"; key: string; label: string } | undefined,
): { label: string; value: string; tone: StatTone } | null {
  if (!stat) return null;
  const pct = stat.kind === "index" ? findIndex(snap, stat.key)?.changePct ?? null : findSector(snap, stat.key)?.changePct ?? null;
  const value = fmtSignedPct(pct);
  if (value == null || pct == null) return null; // honest omission
  return { label: stat.label, value, tone: pct >= 0 ? "emerald" : "rose" };
}
