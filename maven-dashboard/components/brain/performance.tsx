// /brain — the "Is it working?" live-record card (wave-4 audit fix 4 + 5).
//
// Wraps the honest paper record in the house glass recipe and gives it a
// data-rich frame: a mono readout row above the chart (Enhanced F+ vs Nifty
// 500 TRI, with the as-of date) instead of the chart floating under a one-line
// sub. The "research agents are offline and do NOT affect picks" honesty line
// lives here as a styled system footnote rather than a loose page-bottom
// paragraph.
//
// Every figure is derived by arithmetic over the real equity curve (the paper
// source) — nothing invented. When the curve is empty the readout row is
// omitted entirely (honest omission beats fake data); the chart + note still
// render and say so.

import type { ABReadout, EquityPoint } from "@/lib/types";
import { ABChart } from "@/components/client";
import { GlassPanel } from "@/components/glass-panel";
import { SectionEyebrow } from "@/components/motion";
import { fmtDate, inrCompact, pct, signClass } from "@/lib/format";

/** One mono readout cell — label caps, value in mono tnum, optional signed sub. */
function Readout({ label, value, sub, subClass = "text-dim", valueClass = "text-ink" }: {
  label: string; value: string; sub?: string; subClass?: string; valueClass?: string;
}) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-dim">{label}</div>
      <div className={`mt-1 font-mono text-lg tnum ${valueClass}`}>{value}</div>
      {sub && <div className={`mt-0.5 font-mono text-[11px] tnum ${subClass}`}>{sub}</div>}
    </div>
  );
}

export function BrainPerformance({ curve, readout }: {
  curve: EquityPoint[]; readout: ABReadout;
}) {
  const first = curve[0];
  const last = curve[curve.length - 1];
  const has = curve.length >= 2 && !!first && !!last && first.fplus > 0 && first.nifty500 > 0;
  const fplusRet = has ? (last.fplus / first.fplus - 1) * 100 : 0;
  const niftyRet = has ? (last.nifty500 / first.nifty500 - 1) * 100 : 0;

  return (
    <GlassPanel as="section" noise innerClassName="p-4 sm:p-6">
      <SectionEyebrow number="02">Live record</SectionEyebrow>
      <div className="mt-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-serif text-xl text-ink">Is it working?</h2>
        <p className="text-xs text-dim">Enhanced F+ paper record vs Nifty 500 TRI</p>
      </div>

      {/* mono readout row — real figures off the equity curve, or omitted */}
      {has ? (
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 border-y border-hairline py-3 sm:grid-cols-3">
          <Readout
            label="Enhanced F+"
            value={inrCompact(last.fplus)}
            sub={`${pct(fplusRet)} since inception`}
            subClass={signClass(fplusRet)}
            valueClass="text-emerald"
          />
          <Readout
            label="Nifty 500 TRI"
            value={inrCompact(last.nifty500)}
            sub={`${pct(niftyRet)} since inception`}
            subClass={signClass(niftyRet)}
          />
          <Readout label="As of" value={fmtDate(last.date)} sub="paper · end-of-day" />
        </div>
      ) : (
        <p className="mt-4 border-y border-hairline py-3 font-mono text-[11px] text-dim">
          No paper record yet — the live curve populates once the nightly engine has marked a
          trading day.
        </p>
      )}

      <div className="mt-4">
        <ABChart data={curve} readout={readout} />
      </div>

      {/* honesty footnote — moved in from the loose page-bottom paragraph */}
      <p className="mt-4 flex items-start gap-2 border-t border-hairline pt-3 text-[11px] leading-relaxed text-dim">
        <span aria-hidden className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-white/20" />
        <span>
          The frozen Enhanced F+ engine decides the book from real end-of-day prices. The research
          agents are built but offline and do <span className="text-muted">not</span> affect the
          live picks.
        </span>
      </p>
    </GlassPanel>
  );
}
