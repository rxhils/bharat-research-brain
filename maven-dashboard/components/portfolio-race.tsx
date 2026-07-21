"use client";

// "The Race" — the /portfolio signature moment. All three paper books plus the
// Nifty 500 TRI benchmark, all normalized to % return over one shared window,
// drawn as one hand-built SVG. Each line draws left-to-right (PathDraw =
// motion.path pathLength) with a staggered delay per book, then the terminal
// return per series counts up in the legend (CountUp). Everything is
// MotionValue/animate()-driven inside .brand-motion so it plays on the
// operator's reduced-motion machine. No numbers are invented: every point is a
// real paper_equity_curve row passed down from the server page.

import { useMemo, useState } from "react";
import { CountUp, PathDraw } from "@/components/motion";
import { fmtDate } from "@/lib/format";
import type { EquityPoint } from "@/lib/types";

export type RaceBook = {
  /** Display name (already mapped, e.g. "Enhanced F+"). */
  name: string;
  /** Book accent color (emerald / slate / gold — matches the desk below). */
  color: string;
  curve: EquityPoint[];
};

const W = 800;
const H = 300;
const PAD_L = 10;
const PAD_R = 14;
const PAD_T = 18;
const PAD_B = 22;
const BENCH_COLOR = "#5a616a";
const MAX_PTS = 110; // keep every path well under the 120-point budget

function downsample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr;
  const step = (arr.length - 1) / (max - 1);
  const out: T[] = [];
  for (let i = 0; i < max; i++) out.push(arr[Math.round(i * step)]);
  return out;
}

type Series = {
  key: string;
  label: string;
  color: string;
  isBenchmark: boolean;
  /** % return since first point, positioned on the shared date axis. */
  pts: { x: number; ret: number }[];
  terminalPct: number;
};

export function PortfolioRace({ books }: { books: RaceBook[] }) {
  const [focus, setFocus] = useState<string | null>(null);

  const model = useMemo(() => {
    // Common window: every series — benchmark included — is normalized from the
    // LATEST inception across books, so terminal returns stay comparable even
    // when books started on different dates (a book-vs-benchmark chart where
    // each line has a different base date would silently mislead).
    const withCurves = books.filter((b) => b.curve.length >= 2);
    if (!withCurves.length) return null;
    const commonStart = withCurves.map((b) => b.curve[0].date).sort().pop()!;
    const valid = withCurves
      .map((b) => ({ ...b, curve: b.curve.filter((p) => p.date >= commonStart) }))
      .filter((b) => b.curve.length >= 2);
    if (!valid.length) return null;

    // Shared date axis over the common window, sorted.
    const dateSet = new Set<string>();
    for (const b of valid) for (const p of b.curve) dateSet.add(p.date);
    const dates = Array.from(dateSet).sort();
    if (dates.length < 2) return null;
    const xOfDate = new Map(dates.map((d, i) => [d, i / (dates.length - 1)]));

    const series: Series[] = [];

    // Benchmark: Nifty 500 TRI over the same common window as the books.
    const longest = valid.reduce((a, b) => (b.curve.length > a.curve.length ? b : a));
    const triBase = longest.curve[0].nifty500;
    if (triBase > 0) {
      const pts = longest.curve.map((p) => ({
        x: xOfDate.get(p.date) ?? 0,
        ret: (p.nifty500 / triBase - 1) * 100,
      }));
      series.push({
        key: "bench",
        label: "Nifty 500 TRI",
        color: BENCH_COLOR,
        isBenchmark: true,
        pts: downsample(pts, MAX_PTS),
        terminalPct: pts[pts.length - 1].ret,
      });
    }

    for (const b of valid) {
      const base = b.curve[0].fplus;
      if (base <= 0) continue;
      const pts = b.curve.map((p) => ({
        x: xOfDate.get(p.date) ?? 0,
        ret: (p.fplus / base - 1) * 100,
      }));
      series.push({
        key: b.name,
        label: b.name,
        color: b.color,
        isBenchmark: false,
        pts: downsample(pts, MAX_PTS),
        terminalPct: pts[pts.length - 1].ret,
      });
    }
    if (!series.some((s) => !s.isBenchmark)) return null;

    let min = Infinity;
    let max = -Infinity;
    for (const s of series) for (const p of s.pts) { min = Math.min(min, p.ret); max = Math.max(max, p.ret); }
    min = Math.min(min, 0);
    max = Math.max(max, 0);
    const span = max - min || 1;

    const xPx = (x: number) => PAD_L + x * (W - PAD_L - PAD_R);
    const yPx = (ret: number) => PAD_T + (1 - (ret - min) / span) * (H - PAD_T - PAD_B);
    const toPath = (pts: { x: number; ret: number }[]) =>
      pts.map((p, i) => `${i === 0 ? "M" : "L"}${xPx(p.x).toFixed(1)} ${yPx(p.ret).toFixed(1)}`).join(" ");

    return {
      series: series.map((s) => {
        const end = s.pts[s.pts.length - 1];
        return { ...s, d: toPath(s.pts), endX: xPx(end.x), endY: yPx(end.ret) };
      }),
      zeroY: yPx(0),
      firstDate: dates[0],
      lastDate: dates[dates.length - 1],
    };
  }, [books]);

  if (!model) return null;
  const bookCount = model.series.filter((s) => !s.isBenchmark).length;

  const dimmed = (key: string) => focus !== null && focus !== key;

  return (
    <div className="brand-motion">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${bookCount} paper books vs the Nifty 500 TRI, all normalized to percent return over the same shared window.`}
      >
        {/* quiet horizontal guides + the 0% baseline */}
        <line x1={PAD_L} x2={W - PAD_R} y1={PAD_T} y2={PAD_T} stroke="rgba(255,255,255,0.04)" />
        <line x1={PAD_L} x2={W - PAD_R} y1={H - PAD_B} y2={H - PAD_B} stroke="rgba(255,255,255,0.04)" />
        <line x1={PAD_L} x2={W - PAD_R} y1={model.zeroY} y2={model.zeroY} stroke="rgba(255,255,255,0.09)" strokeDasharray="2 5" />

        {model.series.map((s, i) => (
          <g
            key={s.key}
            style={{ opacity: dimmed(s.key) ? 0.22 : 1, transition: "opacity 0.25s ease" }}
          >
            <PathDraw
              d={s.d}
              stroke={s.color}
              strokeWidth={s.isBenchmark ? 1.5 : 2.5}
              duration={1.6}
              // benchmark settles in behind; the three books stagger 0/0.25/0.5s
              delay={s.isBenchmark ? 0.65 : (i - (model.series[0].isBenchmark ? 1 : 0)) * 0.25}
              dot={s.isBenchmark ? undefined : { cx: s.endX, cy: s.endY, r: 4, fill: s.color }}
            />
          </g>
        ))}
      </svg>

      {/* legend chips: hover/focus isolates a line; terminal returns count up */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        {model.series.map((s) => (
          <button
            key={s.key}
            type="button"
            onMouseEnter={() => setFocus(s.key)}
            onMouseLeave={() => setFocus(null)}
            onFocus={() => setFocus(s.key)}
            onBlur={() => setFocus(null)}
            className={`flex items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 ${
              dimmed(s.key) ? "opacity-40" : "opacity-100"
            }`}
            aria-label={`Highlight ${s.label}`}
          >
            <span
              aria-hidden
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: s.color, boxShadow: s.isBenchmark ? "none" : `0 0 6px ${s.color}66` }}
            />
            <span className={s.isBenchmark ? "text-dim" : "text-muted"}>{s.label}</span>
            <CountUp
              to={s.terminalPct}
              prefix={s.terminalPct >= 0 ? "+" : ""}
              suffix="%"
              decimals={2}
              className="font-mono text-xs"
            />
          </button>
        ))}
        <span className="ml-auto font-mono text-[10px] text-dim">
          {fmtDate(model.firstDate)} → {fmtDate(model.lastDate)}
        </span>
      </div>
    </div>
  );
}
