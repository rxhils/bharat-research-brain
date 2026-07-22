// StyleGrid — the nine style tilts as a visible bento grid. Replaces the old
// pill row whose one-liners lived only in title= tooltips (invisible on touch,
// invisible to everyone who never hovered). Tier labels sit as a mono-caps
// left column on lg, stacked headers below that. The signature card gets the
// CSS conic Border Beam (decorative loop — deliberately NOT .brand-motion, so
// it freezes under the OS reduced-motion flag) plus a gold Signature tag.
//
// Server-component-safe: no hooks here; Reveal is a client leaf.

import { Reveal } from "@/components/motion";

export interface StyleTier {
  tier: string;
  items: { name: string; oneLine: string; signature?: boolean }[];
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
                <div
                  key={s.name}
                  className={`relative rounded-xl2 border p-4 transition-colors duration-300 ${
                    s.signature
                      ? "border-beam border-emerald/30 bg-emerald/[0.05]"
                      : "border-border bg-white/[0.03] hover:border-emerald/20"
                  }`}
                >
                  {s.signature && (
                    <span className="absolute right-3 top-[1.05rem] font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-gold-soft">
                      Signature
                    </span>
                  )}
                  <div className="text-sm font-medium text-ink">{s.name}</div>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted">{s.oneLine}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      ))}
    </div>
  );
}
