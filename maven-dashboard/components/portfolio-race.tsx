"use client";

// "The Race" — the /portfolio signature moment. All three paper books plus the
// Nifty 500 TRI benchmark, all normalized to % return over one shared window,
// drawn as one hand-built SVG. Each line draws left-to-right (PathDraw =
// motion.path pathLength) with a staggered delay per book. A head-riding tracer
// then rides each book's line: ONE animate()-driven MotionValue per line drives
// both the dot's cx/cy (useTransform index-interpolation over the precomputed
// pixel arrays) AND the terminal % count-up at the line's endpoint — one motion
// value, no parallel timers (the hard-won readout/draw law). A left-gutter %
// scale (min / 0 / max) and a pointer crosshair make it quantitatively
// readable. Everything is MotionValue/animate()-driven inside .brand-motion so
// it plays on the operator's reduced-motion machine. No numbers are invented:
// every point is a real paper_equity_curve row passed down from the server page.

import { useEffect, useMemo, useRef, useState } from "react";
import { animate, motion, useInView, useMotionValue, useTransform } from "framer-motion";
import { EASE, PathDraw } from "@/components/motion";
import { fmtDate, pct } from "@/lib/format";
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
const PAD_L = 44; // left gutter holds the % scale labels
const PAD_R = 62; // right gutter holds the per-series terminal % readouts
const PAD_T = 18;
const PAD_B = 22;
const BENCH_COLOR = "#5a616a";
const MAX_PTS = 110; // keep every path well under the 120-point budget
const DRAW_DUR = 1.6;

function downsample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr;
  const step = (arr.length - 1) / (max - 1);
  const out: T[] = [];
  for (let i = 0; i < max; i++) out.push(arr[Math.round(i * step)]);
  return out;
}

/** Index-interpolated sample of a per-point pixel/value array at fraction t. */
function sampleAt(arr: number[], t: number): number {
  const n = arr.length;
  if (n === 0) return 0;
  if (n === 1) return arr[0];
  const f = Math.max(0, Math.min(1, t)) * (n - 1);
  const i = Math.floor(f);
  if (i >= n - 1) return arr[n - 1];
  return arr[i] + (arr[i + 1] - arr[i]) * (f - i);
}

type Series = {
  key: string;
  label: string;
  color: string;
  isBenchmark: boolean;
  delay: number;
  d: string;
  endX: number;
  endY: number;
  terminalPct: number;
  /** Precomputed pixel + value arrays for the tracer + crosshair. */
  xs: number[];
  ys: number[];
  rets: number[];
};

/** One race line: the PathDraw stroke + (books only) a head-riding tracer dot,
 *  plus a terminal % that counts up in lockstep — all off ONE MotionValue. */
function RaceLine({ s, dim }: { s: Series; dim: boolean }) {
  const gRef = useRef<SVGGElement>(null);
  const inView = useInView(gRef, { once: true, margin: "-10% 0px" });
  const p = useMotionValue(1); // 1 = settled at the endpoint (honest first paint)
  const cx = useTransform(p, (t) => sampleAt(s.xs, t));
  const cy = useTransform(p, (t) => sampleAt(s.ys, t));
  const [label, setLabel] = useState(() => pct(s.terminalPct));

  useEffect(() => {
    if (!inView) return;
    p.set(0);
    const controls = animate(p, 1, { duration: DRAW_DUR, delay: s.delay, ease: EASE });
    const unsub = p.on("change", (t) => setLabel(pct(sampleAt(s.rets, t))));
    return () => { controls.stop(); unsub(); };
  }, [inView, p, s]);

  return (
    <g ref={gRef} style={{ opacity: dim ? 0.22 : 1, transition: "opacity 0.25s ease" }}>
      <PathDraw
        d={s.d}
        stroke={s.color}
        strokeWidth={s.isBenchmark ? 1.5 : 2.5}
        duration={DRAW_DUR}
        delay={s.delay}
      />
      {!s.isBenchmark && (
        <>
          <motion.circle
            cx={cx} cy={cy} r={7} fill={s.color} aria-hidden
            style={{ opacity: 0.25, filter: "blur(3px)" }}
          />
          <motion.circle cx={cx} cy={cy} r={4} fill={s.color} aria-hidden />
        </>
      )}
      <text
        x={s.endX + 8}
        y={s.endY}
        dominantBaseline="middle"
        className="font-mono tnum"
        fontSize={10}
        fill={s.isBenchmark ? BENCH_COLOR : s.color}
        opacity={s.isBenchmark ? 0.85 : 1}
      >
        {label}
      </text>
    </g>
  );
}

type Hover = {
  x: number;
  date: string;
  rows: { label: string; color: string; ret: number; px: number; y: number; bench: boolean }[];
};

export function PortfolioRace({ books }: { books: RaceBook[] }) {
  const [pinned, setPinned] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const focus = hovered ?? pinned;

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

    type Raw = { key: string; label: string; color: string; isBenchmark: boolean; pts: { x: number; ret: number }[]; terminalPct: number };
    const raw: Raw[] = [];

    // Benchmark: Nifty 500 TRI over the same common window as the books.
    const longest = valid.reduce((a, b) => (b.curve.length > a.curve.length ? b : a));
    const triBase = longest.curve[0].nifty500;
    if (triBase > 0) {
      const pts = longest.curve.map((p) => ({
        x: xOfDate.get(p.date) ?? 0,
        ret: (p.nifty500 / triBase - 1) * 100,
      }));
      raw.push({ key: "bench", label: "Nifty 500 TRI", color: BENCH_COLOR, isBenchmark: true, pts: downsample(pts, MAX_PTS), terminalPct: pts[pts.length - 1].ret });
    }

    for (const b of valid) {
      const base = b.curve[0].fplus;
      if (base <= 0) continue;
      const pts = b.curve.map((p) => ({ x: xOfDate.get(p.date) ?? 0, ret: (p.fplus / base - 1) * 100 }));
      raw.push({ key: b.name, label: b.name, color: b.color, isBenchmark: false, pts: downsample(pts, MAX_PTS), terminalPct: pts[pts.length - 1].ret });
    }
    if (!raw.some((s) => !s.isBenchmark)) return null;

    let min = Infinity;
    let max = -Infinity;
    for (const s of raw) for (const p of s.pts) { min = Math.min(min, p.ret); max = Math.max(max, p.ret); }
    min = Math.min(min, 0);
    max = Math.max(max, 0);
    const span = max - min || 1;

    const xPx = (x: number) => PAD_L + x * (W - PAD_L - PAD_R);
    const yPx = (ret: number) => PAD_T + (1 - (ret - min) / span) * (H - PAD_T - PAD_B);
    const toPath = (pts: { x: number; ret: number }[]) =>
      pts.map((p, i) => `${i === 0 ? "M" : "L"}${xPx(p.x).toFixed(1)} ${yPx(p.ret).toFixed(1)}`).join(" ");

    let bookIndex = 0;
    const series: Series[] = raw.map((s) => {
      const end = s.pts[s.pts.length - 1];
      const delay = s.isBenchmark ? 0.65 : (bookIndex++ * 0.25);
      return {
        key: s.key, label: s.label, color: s.color, isBenchmark: s.isBenchmark, delay,
        d: toPath(s.pts), endX: xPx(end.x), endY: yPx(end.ret), terminalPct: s.terminalPct,
        xs: s.pts.map((p) => xPx(p.x)),
        ys: s.pts.map((p) => yPx(p.ret)),
        rets: s.pts.map((p) => p.ret),
      };
    });

    return {
      series,
      zeroY: yPx(0),
      minLabelY: yPx(min),
      maxLabelY: yPx(max),
      min, max,
      dates,
      firstDate: dates[0],
      lastDate: dates[dates.length - 1],
    };
  }, [books]);

  if (!model) return null;
  const bookCount = model.series.filter((s) => !s.isBenchmark).length;
  const dimmed = (key: string) => focus !== null && focus !== key;

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const vbX = ((e.clientX - r.left) / r.width) * W;
    const clampedX = Math.max(PAD_L, Math.min(W - PAD_R, vbX));
    const rows = model.series.map((s) => {
      let best = 0;
      for (let i = 1; i < s.xs.length; i++) if (Math.abs(s.xs[i] - clampedX) < Math.abs(s.xs[best] - clampedX)) best = i;
      return { label: s.label, color: s.color, ret: s.rets[best], px: s.xs[best], y: s.ys[best], bench: s.isBenchmark };
    });
    const di = Math.round(((clampedX - PAD_L) / (W - PAD_L - PAD_R)) * (model.dates.length - 1));
    setHover({ x: clampedX, date: model.dates[Math.max(0, Math.min(model.dates.length - 1, di))], rows });
  };

  // Crosshair readout panel geometry (kept fully inside the viewBox).
  const PANEL_W = 148;
  const panelX = hover ? Math.max(PAD_L, Math.min(W - PANEL_W - 4, hover.x + 12)) : 0;
  const panelH = hover ? 16 + hover.rows.length * 13 + 6 : 0;

  return (
    <div className="brand-motion">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full touch-pan-y"
        role="img"
        aria-label={`${bookCount} paper books vs the Nifty 500 TRI, all normalized to percent return over the same shared window.`}
      >
        {/* quiet horizontal guides + the 0% baseline */}
        <line x1={PAD_L} x2={W - PAD_R} y1={PAD_T} y2={PAD_T} stroke="rgba(255,255,255,0.04)" />
        <line x1={PAD_L} x2={W - PAD_R} y1={H - PAD_B} y2={H - PAD_B} stroke="rgba(255,255,255,0.04)" />
        <line x1={PAD_L} x2={W - PAD_R} y1={model.zeroY} y2={model.zeroY} stroke="rgba(255,255,255,0.09)" strokeDasharray="2 5" />

        {/* left-gutter % scale: max / 0 / min */}
        <g className="font-mono tnum" fontSize={9} fill="rgba(255,255,255,0.4)" textAnchor="end">
          <text x={PAD_L - 6} y={model.maxLabelY + 3}>{pct(model.max, 1)}</text>
          {Math.abs(model.max) > 0.5 && Math.abs(model.min) > 0.5 && (
            <text x={PAD_L - 6} y={model.zeroY + 3}>0%</text>
          )}
          <text x={PAD_L - 6} y={model.minLabelY - 1}>{pct(model.min, 1)}</text>
        </g>

        {model.series.map((s) => (
          <RaceLine key={s.key} s={s} dim={dimmed(s.key)} />
        ))}

        {/* pointer crosshair + per-series readout at the nearest shared date */}
        {hover && (
          <g pointerEvents="none">
            <line x1={hover.x} x2={hover.x} y1={PAD_T} y2={H - PAD_B} stroke="rgba(255,255,255,0.18)" />
            {hover.rows.map((row) => (
              <circle key={row.label} cx={row.px} cy={row.y} r={3} fill={row.color} stroke="#0a0b0d" strokeWidth={1} />
            ))}
            <g>
              <rect
                x={panelX} y={PAD_T} width={PANEL_W} height={panelH} rx={6}
                fill="rgba(10,11,13,0.94)" stroke="rgba(255,255,255,0.1)"
              />
              <text x={panelX + 9} y={PAD_T + 13} className="font-mono" fontSize={9} fill="#94a3b8">
                {fmtDate(hover.date)}
              </text>
              {hover.rows.map((row, i) => {
                const ry = PAD_T + 16 + 13 * (i + 1) - 4;
                return (
                  <g key={row.label}>
                    <circle cx={panelX + 11} cy={ry - 3} r={3} fill={row.color} />
                    <text x={panelX + 19} y={ry} fontSize={9.5} fill={row.bench ? "#94a3b8" : "#e2e8f0"}>
                      {row.label}
                    </text>
                    <text x={panelX + PANEL_W - 8} y={ry} textAnchor="end" className="font-mono tnum" fontSize={9.5} fill={row.bench ? "#94a3b8" : row.color}>
                      {pct(row.ret)}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>
        )}

        {/* transparent capture layer for the crosshair (kept on top) */}
        <rect
          x={0} y={0} width={W} height={H} fill="transparent" pointerEvents="all"
          style={{ touchAction: "pan-y" }}
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        />
      </svg>

      {/* legend chips: hover previews / tap pins an isolated line. Terminal
          returns now live on the chart, so the chips carry only the swatch. */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        {model.series.map((s) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={pinned === s.key}
            onClick={() => setPinned((f) => (f === s.key ? null : s.key))}
            onMouseEnter={() => setHovered(s.key)}
            onMouseLeave={() => setHovered(null)}
            onFocus={() => setHovered(s.key)}
            onBlur={() => setHovered(null)}
            className={`flex items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60 ${
              dimmed(s.key) ? "opacity-40" : "opacity-100"
            }`}
            aria-label={`Isolate ${s.label}`}
          >
            <span
              aria-hidden
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: s.color, boxShadow: s.isBenchmark ? "none" : `0 0 6px ${s.color}66` }}
            />
            <span className={s.isBenchmark ? "text-dim" : "text-muted"}>{s.label}</span>
          </button>
        ))}
        <span className="w-full font-mono text-[10px] text-dim sm:ml-auto sm:w-auto">
          {fmtDate(model.firstDate)} → {fmtDate(model.lastDate)}
        </span>
      </div>
    </div>
  );
}
