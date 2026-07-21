"use client";

// Hero stat band — the four headline numbers as count-ups (shared CountUp:
// useMotionValue + animate(), so it plays under the OS reduced-motion flag),
// plus a slim mono strip of the secondary figures. All values verbatim from
// the frozen engine's committed simulations.

import { GlassPanel } from "@/components/glass-panel";
import { CountUp } from "@/components/motion";

function BandStat({
  label,
  children,
  tone = "text-ink",
}: {
  label: string;
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold sm:text-3xl ${tone}`}>{children}</div>
    </div>
  );
}

export function StatTicker() {
  return (
    <GlassPanel noise innerClassName="p-5 sm:p-6">
      <div className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4">
        <BandStat label="2021–26 return" tone="text-emerald">
          <CountUp to={129.97} prefix="+" suffix="%" decimals={2} />
        </BandStat>
        <BandStat label="vs Nifty 500 TRI" tone="text-muted">
          <CountUp to={82.17} prefix="+" suffix="%" decimals={2} />
        </BandStat>
        <BandStat label="Max drawdown" tone="text-emerald">
          <CountUp to={14.05} suffix="%" decimals={2} />
        </BandStat>
        <BandStat label="Bull windows beaten" tone="text-emerald">
          <CountUp to={4} suffix=" / 4" decimals={0} />
        </BandStat>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-1.5 border-t border-hairline pt-4 font-mono text-[11px] text-muted">
        <span>
          COVID-window DD <span className="text-ink">13.88%</span> vs market <span className="text-ink">~38%</span>
        </span>
        <span aria-hidden className="text-dim">·</span>
        <span>
          vs Nifty 500 DD <span className="text-ink">18.59%</span>
        </span>
        <span aria-hidden className="text-dim">·</span>
        <span>
          2021–26 Sharpe <span className="text-ink">0.95</span>
        </span>
      </div>
    </GlassPanel>
  );
}
