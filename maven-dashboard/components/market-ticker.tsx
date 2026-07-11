"use client";
import { Fragment, useEffect, useState } from "react";
import type { Quote, SectorPerf } from "@/lib/maven/types";

const POLL_MS = 120_000; // matches getIndexPerformance's tightest TTL

// mask (not painted overlays) so chips dissolve at both ends over any backdrop
const EDGE_FADE = "linear-gradient(to right, transparent, black 2.5rem, black calc(100% - 2.5rem), transparent)";
const edgeMask = { maskImage: EDGE_FADE, WebkitMaskImage: EDGE_FADE } as const;

// ghost-chip widths (px) — enough to fill one line on any viewport
const GHOST_W = [88, 64, 96, 72, 84, 68, 92, 76];

type Chip = { label: string; changePct: number | null; kind: "index" | "sector" };

function fmtPct(n: number | null): string {
  if (n == null) return "-";
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function Chip({ c }: { c: Chip }) {
  const tone = c.changePct == null ? "text-dim" : c.changePct >= 0 ? "text-emerald" : "text-rose";
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs">
      <span className={"h-1 w-1 rounded-full " + (c.kind === "index" ? "bg-emerald/70" : "bg-gold-soft/70")} aria-hidden />
      <span className="text-muted">{c.label}</span>
      <span className={"tnum font-medium " + tone}>{fmtPct(c.changePct)}</span>
    </span>
  );
}

/** Hairline dot between chips — placed after every chip so the loop seam keeps uniform spacing. */
function Dot() {
  return <span className="mx-3 h-0.5 w-0.5 shrink-0 rounded-full bg-white/15" aria-hidden />;
}

export function MarketTicker() {
  const [chips, setChips] = useState<Chip[] | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const r = await fetch("/api/market/ticker", { cache: "no-store" });
        if (!r.ok) { if (alive) setChips((prev) => prev ?? []); return; }
        const j: { indices?: Quote[]; sectors?: SectorPerf[] } = await r.json();
        if (!alive) return;
        const idx: Chip[] = (j.indices ?? []).filter((q) => q.changePct != null).map((q) => ({ label: q.label, changePct: q.changePct, kind: "index" as const }));
        const sec = j.sectors ?? [];
        const secChips: Chip[] = [...sec.slice(0, 3), ...sec.slice(-2)].map((s) => ({ label: s.name, changePct: s.changePct, kind: "sector" as const }));
        setChips([...idx, ...secChips]);
      } catch {
        // ticker is decorative — keep last-known chips; collapse (not skeleton forever) if nothing ever loaded
        if (alive) setChips((prev) => prev ?? []);
      }
    }
    load();
    const t = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (chips && chips.length === 0) return null; // loaded, confirmed nothing to show

  return (
    <div
      className="relative overflow-hidden rounded-xl border border-hairline bg-panel/40"
      aria-label="Today's market snapshot"
      aria-busy={!chips}
    >
      {!chips ? (
        // skeleton reserves the exact loaded height (py-2 + one h-4 text row) so nothing shifts;
        // one gentle opacity pulse on the whole row — single animated element, motion-safe gated
        <div className="py-2" style={edgeMask} aria-hidden>
          <div className="flex h-4 w-max items-center px-3 motion-safe:animate-[pulseDot_2.2s_ease-in-out_infinite]">
            {GHOST_W.map((w, i) => (
              <Fragment key={i}>
                <span className="h-1 w-1 shrink-0 rounded-full bg-white/10" />
                <span className="ml-1.5 h-2.5 shrink-0 rounded-full bg-white/[0.06]" style={{ width: w }} />
                {i < GHOST_W.length - 1 && <Dot />}
              </Fragment>
            ))}
          </div>
        </div>
      ) : (
        <div className="py-2" style={edgeMask}>
          {/* brand-motion: the marquee is the point of a ticker — it keeps
              scrolling even under the OS reduced-motion flag (hover pauses). */}
          <div className="brand-motion flex w-max animate-marquee [will-change:transform] hover:[animation-play-state:paused]">
            {[chips, chips].map((group, gi) => (
              <div key={gi} className="flex shrink-0 items-center" aria-hidden={gi === 1}>
                {group.map((c, i) => (
                  <Fragment key={i}>
                    <Chip c={c} />
                    <Dot />
                  </Fragment>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
