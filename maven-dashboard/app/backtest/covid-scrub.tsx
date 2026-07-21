"use client";

// ─────────────── signature moment — "The Crash, Scrubbed" ───────────────
// Sticky 300vh scroll-scrubbed COVID de-risk proof. One sprung MotionValue
// (useScrollScrub — house pattern from explainer.tsx DrawdownScrub) drives:
//   (a) pathLength on both equity lines (market slate, Enhanced F+ emerald),
//   (b) a clip-rect that reveals the GOLD gap band between the two curves as
//       the index falls away (the page's single gold data moment),
//   (c) the live max-drawdown readouts (written straight to the DOM — no
//       re-render per frame),
//   (d) the four graded-cash exposure-step cards (100→50→25→50%) popping in
//       as the draw front passes each step's date.
// User-driven scrub → NEVER gated by useReducedMotionSafe: it plays under the
// OS reduced-motion flag (wrapped in .brand-motion, per house policy). Faint
// static tracks render underneath so the proof reads with JS off / at SSR.
// Anchors (troughs −13.88% vs ~−38%, step dates/exposures) are verbatim from
// the frozen engine — see data/covid-equity.ts.

import { motion, useMotionValueEvent, useTransform, type MotionValue } from "framer-motion";
import { useRef, useState } from "react";
import { useScrollScrub } from "@/components/motion";
import {
  COVID_SERIES,
  ENGINE_COMMIT,
  EXPOSURE_STEPS,
  stepFraction,
  type ExposureStep,
} from "./data/covid-equity";

/* ---------- geometry (module scope — computed once) ---------- */
const W = 740;
const H = 380;
const padL = 14;
const padR = 16;
const padT = 22;
const padB = 26;
const Y_MAX = 102;
const Y_MIN = 58;

const N = COVID_SERIES.length;
const xs = (i: number) => padL + (i / (N - 1)) * (W - padL - padR);
const ys = (v: number) => padT + ((Y_MAX - v) / (Y_MAX - Y_MIN)) * (H - padT - padB);
const xAt = (frac: number) => padL + frac * (W - padL - padR);

type P = readonly [number, number];
/** Catmull-Rom → cubic Bézier smoothing (same helper as DrawdownScrub). */
function smooth(pts: P[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2;
    d += ` C ${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]},${p2[1]}`;
  }
  return d;
}

const mPts: P[] = COVID_SERIES.map((p, i) => [xs(i), ys(p.market)]);
const fPts: P[] = COVID_SERIES.map((p, i) => [xs(i), ys(p.fplus)]);
const marketD = smooth(mPts);
const fplusD = smooth(fPts);
const lastM = mPts[mPts.length - 1];
/** Closed region between the two curves — the gold "gap" the de-risk kept. */
const bandD = fplusD + ` L ${lastM[0]},${lastM[1]}` + smooth([...mPts].reverse()).replace(/^M[^C]*/, "") + " Z";

const STEP_FRACS = EXPOSURE_STEPS.map((s) => stepFraction(s.date));
const TROUGH_I = COVID_SERIES.reduce((lo, p, i) => (p.market < COVID_SERIES[lo].market ? i : lo), 0);

/* ---------- pieces ---------- */

function StepCard({ step, active }: { step: ExposureStep; active: boolean }) {
  return (
    <motion.div
      className="rounded-xl border border-hairline bg-bg/50 px-3 py-2.5"
      initial={{ opacity: 0.25, y: 8, scale: 0.97 }}
      animate={active ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0.25, y: 8, scale: 0.97 }}
      transition={{ type: "spring", stiffness: 340, damping: 26 }}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[10px] text-dim">{step.date}</span>
        <span className="font-mono text-sm font-semibold text-ink">
          {step.exp}%<span className="ml-1 font-sans text-[10px] font-normal text-muted">invested</span>
        </span>
      </div>
      <p className="mt-0.5 text-[11px] leading-snug text-muted">{step.note}</p>
    </motion.div>
  );
}

export function CovidScrub() {
  const wrapRef = useRef<HTMLDivElement>(null);
  // Sprung scrub — user-driven, so it deliberately ignores the OS
  // reduced-motion flag (house DrawdownScrub convention).
  const spring: MotionValue<number> = useScrollScrub(wrapRef, ["start start", "end end"], {
    stiffness: 120,
    damping: 24,
    restDelta: 0.001,
  });

  // Single source of truth: the same value drives both path draws, the gold
  // gap clip, the counters, and the step activations — desync is impossible.
  const lineProg = useTransform(spring, [0.06, 0.6], [0, 1], { clamp: true });
  const marketDotOpacity = useTransform(lineProg, [TROUGH_I / (N - 1), TROUGH_I / (N - 1) + 0.06], [0, 1]);

  // Gold gap band reveal — clip rect width follows the draw front. Written via
  // setAttribute (motion-value event) so SVG geometry updates everywhere.
  const clipRef = useRef<SVGRectElement>(null);
  useMotionValueEvent(lineProg, "change", (v) => {
    clipRef.current?.setAttribute("width", String(v * W));
  });

  // Live max-drawdown-so-far readouts, computed from the real series values.
  const marketNumRef = useRef<HTMLSpanElement>(null);
  const fplusNumRef = useRef<HTMLSpanElement>(null);
  useMotionValueEvent(lineProg, "change", (v) => {
    const covered = Math.max(0, Math.min(N - 1, Math.floor(v * (N - 1))));
    let minM = 100, minF = 100;
    for (let i = 0; i <= covered; i++) {
      minM = Math.min(minM, COVID_SERIES[i].market);
      minF = Math.min(minF, COVID_SERIES[i].fplus);
    }
    if (marketNumRef.current)
      marketNumRef.current.textContent = minM >= 100 ? "0%" : `−${(100 - minM).toFixed(1)}%`;
    if (fplusNumRef.current)
      fplusNumRef.current.textContent = minF >= 100 ? "0%" : `−${(100 - minF).toFixed(2)}%`;
  });

  // Exposure steps activate as the draw front passes each step's date.
  const [activeSteps, setActiveSteps] = useState(0);
  useMotionValueEvent(lineProg, "change", (v) => {
    const count = STEP_FRACS.filter((f) => v >= f).length;
    setActiveSteps(count); // React bails out when unchanged
  });

  return (
    <div ref={wrapRef} className="relative h-[300vh] [@media(max-width:640px)]:h-[220vh]">
      {/* h-svh tracks mobile toolbars; short viewports top-align + scroll
          internally instead of clipping (explainer DrawdownScrub pattern). */}
      <div className="brand-motion sticky top-0 flex h-screen h-svh items-center [@media(max-height:640px)]:items-start [@media(max-height:640px)]:overflow-y-auto [@media(max-height:640px)]:py-3">
        <div className="w-full rounded-[20px] bg-gradient-to-b from-white/[0.14] to-white/[0.03] p-px">
          <div className="rounded-[19px] bg-panel/95 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] sm:p-6">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-dim">
                  Feb–Jun 2020 · indexed to the pre-crash peak
                </p>
                <p className="mt-1 font-serif text-lg text-ink">The COVID de-risk, step by step</p>
              </div>
              <div className="flex items-center gap-4 text-xs text-muted">
                <span className="flex items-center gap-2">
                  <svg width="18" height="6" aria-hidden>
                    <line x1="0" y1="3" x2="18" y2="3" stroke="#5a616a" strokeWidth="2.4" strokeDasharray="4 3" />
                  </svg>
                  Nifty 500
                </span>
                <span className="flex items-center gap-2">
                  <svg width="18" height="6" aria-hidden>
                    <line x1="0" y1="3" x2="18" y2="3" stroke="#34d399" strokeWidth="2.8" />
                  </svg>
                  Enhanced F+
                </span>
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_236px]">
              {/* chart */}
              <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
                <svg
                  viewBox={`0 0 ${W} ${H}`}
                  className="block h-full w-full"
                  role="img"
                  aria-label="COVID crash, scrubbed by scroll: the market troughs at about −38% while Enhanced F+ troughs at −13.88%, with graded-cash exposure steps of 100, 50, 25 and back to 50 percent."
                >
                  <defs>
                    <linearGradient id="covidgap" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#c9a961" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#c9a961" stopOpacity="0.03" />
                    </linearGradient>
                    <clipPath id="covidgapclip">
                      <rect ref={clipRef} x="0" y="0" width="0" height={H} />
                    </clipPath>
                  </defs>

                  {/* gridlines + faint static tracks — the proof reads with JS off */}
                  {[100, 90, 80, 70, 60].map((g) => (
                    <line key={g} x1={padL} x2={W - padR} y1={ys(g)} y2={ys(g)} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
                  ))}
                  <path d={marketD} fill="none" stroke="rgba(90,97,106,0.28)" strokeWidth={1.5} strokeDasharray="5 5" strokeLinecap="round" />
                  <path d={fplusD} fill="none" stroke="rgba(52,211,153,0.20)" strokeWidth={1.5} strokeLinecap="round" />

                  {/* exposure-step markers — dashed verticals at the committed dates */}
                  {EXPOSURE_STEPS.map((s, i) => (
                    <motion.line
                      key={s.date}
                      x1={xAt(STEP_FRACS[i])}
                      x2={xAt(STEP_FRACS[i])}
                      y1={padT}
                      y2={H - padB}
                      stroke="rgba(233,235,237,0.16)"
                      strokeWidth={1}
                      strokeDasharray="3 4"
                      initial={{ opacity: 0 }}
                      animate={activeSteps > i ? { opacity: 1 } : { opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    />
                  ))}

                  {/* GOLD gap band — the drawdown the de-risk did not take;
                      revealed by the clip rect that follows the draw front. */}
                  <g clipPath="url(#covidgapclip)">
                    <path d={bandD} fill="url(#covidgap)" />
                  </g>

                  {/* scrubbed lines — same MotionValue as counters and steps */}
                  <motion.path d={marketD} fill="none" stroke="#5a616a" strokeWidth={2} strokeDasharray="5 5" strokeLinecap="round" style={{ pathLength: lineProg }} />
                  <motion.path d={fplusD} fill="none" stroke="#34d399" strokeWidth={3} strokeLinecap="round" style={{ pathLength: lineProg }} />
                  <motion.circle cx={xs(TROUGH_I)} cy={ys(COVID_SERIES[TROUGH_I].market)} r={4} fill="#0a0b0d" stroke="#5a616a" strokeWidth={2} style={{ opacity: marketDotOpacity }} />
                  <motion.circle cx={xs(TROUGH_I)} cy={ys(COVID_SERIES[TROUGH_I].fplus)} r={4.5} fill="#0a0b0d" stroke="#34d399" strokeWidth={2.5} style={{ opacity: marketDotOpacity }} />
                </svg>

                {/* HTML overlays — fixed px so they stay readable at 375px */}
                {[100, 90, 80, 70, 60].map((g) => (
                  <span
                    key={g}
                    aria-hidden
                    className="tnum absolute left-1 font-mono text-[10px] leading-none text-dim"
                    style={{ top: `calc(${((ys(g) / H) * 100).toFixed(2)}% - 12px)` }}
                  >
                    {g}
                  </span>
                ))}
                {EXPOSURE_STEPS.map((s, i) => (
                  <motion.span
                    key={s.date}
                    aria-hidden
                    className="absolute -translate-x-1/2 whitespace-nowrap rounded-full border border-hairline bg-panel2/90 px-1.5 py-0.5 font-mono text-[10px] leading-none text-muted"
                    style={{
                      left: `${((xAt(STEP_FRACS[i]) / W) * 100).toFixed(2)}%`,
                      top: i === 2 ? 22 : 2,
                    }}
                    initial={{ opacity: 0, y: 6 }}
                    animate={activeSteps > i ? { opacity: 1, y: 0 } : { opacity: 0, y: 6 }}
                    transition={{ type: "spring", stiffness: 380, damping: 26 }}
                  >
                    {s.exp}%
                  </motion.span>
                ))}
                <div className="absolute inset-x-0 -bottom-1 flex items-center justify-between font-mono text-[10px] text-dim">
                  <span>Feb 2020</span>
                  <span>Jun 2020</span>
                </div>
              </div>

              {/* exposure-step rail — pops in as the draw front passes each date */}
              <div className="grid grid-cols-2 content-start gap-2 lg:grid-cols-1">
                {EXPOSURE_STEPS.map((s, i) => (
                  <StepCard key={s.date} step={s} active={activeSteps > i} />
                ))}
              </div>
            </div>

            {/* live readouts — max drawdown so far, from the real series */}
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-hairline bg-bg/50 p-4">
                <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Market fell</p>
                <p className="mt-1 font-mono text-2xl text-muted sm:text-3xl">
                  <span ref={marketNumRef} className="tnum">0%</span>
                </p>
              </div>
              <div className="rounded-xl border border-emerald/30 bg-emerald/[0.06] p-4">
                <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Enhanced F+ fell</p>
                <p className="mt-1 font-mono text-2xl text-emerald sm:text-3xl">
                  <span ref={fplusNumRef} className="tnum">0%</span>
                </p>
              </div>
            </div>

            <p className="mt-3 text-[11px] leading-relaxed text-dim">
              Scroll to scrub. Exposure steps (100 / 50 / 25 / 50%) and both troughs (−13.88% vs the
              market&apos;s ~−38%) are verbatim from the frozen engine (commit {ENGINE_COMMIT}); the weekly
              line shape between those anchors is illustrative. Backtested, not a live track record.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
