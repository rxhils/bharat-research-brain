// StyleGrid — the nine style tilts as a visible bento grid. Replaces the old
// pill row whose one-liners lived only in title= tooltips (invisible on touch,
// invisible to everyone who never hovered). Tier labels sit as a mono-caps
// left column on lg, stacked headers below that.
//
// The signature card gets the CSS conic Border Beam (decorative loop —
// deliberately NOT .brand-motion, so it freezes under the OS reduced-motion
// flag) PLUS a static emerald gradient p-px border so the flagship still reads
// as special when the beam is frozen (the operator's machine has reduced-motion
// on). Each card carries a truthful status chip — Live paper / Backtested /
// Planned — sourced only from real props, never invented.
//
// Server-component-safe: no hooks here; Reveal is a client leaf.

import { Reveal } from "@/components/motion";

export type StyleStatusTone = "live" | "backtested" | "planned";

export interface StyleItem {
  name: string;
  oneLine: string;
  signature?: boolean;
  status?: { label: string; tone: StyleStatusTone };
}

export interface StyleTier {
  tier: string;
  items: StyleItem[];
}

const STATUS_CLS: Record<StyleStatusTone, string> = {
  live: "border border-emerald/25 bg-emerald/10 text-emerald",
  backtested: "border border-border bg-white/[0.03] text-muted",
  planned: "border border-dashed border-border text-dim",
};

function StatusChip({ status }: { status: NonNullable<StyleItem["status"]> }) {
  return (
    <span
      className={`mt-3 inline-flex w-fit items-center rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] ${STATUS_CLS[status.tone]}`}
    >
      {status.label}
    </span>
  );
}

function StyleCard({ s }: { s: StyleItem }) {
  const inner = (
    <>
      {s.signature && (
        <span className="absolute right-3 top-[1.05rem] font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald">
          Signature
        </span>
      )}
      <div className="text-sm font-medium text-ink">{s.name}</div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">{s.oneLine}</p>
      {s.status && <StatusChip status={s.status} />}
    </>
  );

  if (s.signature) {
    // Static emerald gradient p-px border = the frozen-state "special" cue;
    // border-beam rides on top when motion is allowed.
    return (
      <div className="rounded-xl2 bg-gradient-to-br from-emerald/45 via-emerald/15 to-emerald/[0.05] p-px">
        <div className="border-beam relative flex h-full flex-col rounded-[inherit] bg-emerald/[0.05] p-4">
          {inner}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col rounded-xl2 border border-border bg-white/[0.03] p-4 transition-[border-color,transform] duration-300 hover:border-emerald/20 motion-safe:hover:-translate-y-0.5">
      {inner}
    </div>
  );
}

export function StyleGrid({ tiers }: { tiers: StyleTier[] }) {
  return (
    <div className="mt-6 space-y-4">
      {tiers.map((grp, gi) => (
        <Reveal key={grp.tier} delay={gi * 0.06}>
          <div className="grid gap-2 lg:grid-cols-[6.5rem_1fr] lg:gap-4">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-dim lg:pt-4 lg:text-right">
              {grp.tier}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {grp.items.map((s) => (
                <StyleCard key={s.name} s={s} />
              ))}
            </div>
          </div>
        </Reveal>
      ))}
    </div>
  );
}
