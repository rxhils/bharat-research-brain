"use client";

// PipelineDiagram — /portfolio-mode's ONE signature moment.
//
// A vertical tracing beam (Aceternity Tracing Beam / Magic UI Animated Beam
// pattern) scrubbed by scroll: useScrollScrub drives pathLength on a gradient
// motion.path, and each stage node lights up via useTransform on the SAME
// MotionValue — no parallel formulas (hard-won lesson: readouts and drawn
// elements must share one motion value). Four stages — Universe → Quality
// gate → Rank → Weight — then the pipeline forks into its two clocks
// (quarterly full re-pick that loops back to the top, weekly de-risk check)
// plus the 15% hard stop, drawn as annotated PathDraw branches.
//
// Reduced-motion reality: the operator machine has OS reduced-motion ON.
// The beam and node lighting are motion-value-driven inside .brand-motion,
// so they play regardless of the OS flag (signature, not decorative).
// Static fallback: if JS never hydrates, the dim base rail + nodes at their
// resting opacity remain fully readable.

import { motion, useTransform, type MotionStyle, type MotionValue } from "framer-motion";
import { useId, useRef } from "react";

import { PathDraw, useScrollScrub } from "@/components/motion";

const STAGES = [
  {
    num: "S1",
    name: "Universe",
    body: "Every portfolio starts from the same stock universe — the investable market, not a hand-picked shortlist.",
  },
  {
    num: "S2",
    name: "Quality gate",
    body: "Each style applies its own strategy-specific filters — the bar every name must clear before it can be held.",
  },
  {
    num: "S3",
    name: "Rank",
    body: "The eligible names are ranked by the style's own signal — which signal it ranks by is the tilt.",
  },
  {
    num: "S4",
    name: "Weight",
    body: "Target weights are set from that ranking — capped at four names per sector, so no single theme can dominate.",
  },
] as const;

/** One stage row: dot on the rail + copy, both lit by the shared scrub MV. */
function StageNode({ scrub, index, total, num, name, body }: {
  scrub: MotionValue<number>;
  index: number;
  total: number;
  num: string;
  name: string;
  body: string;
}) {
  const from = index / total;
  const to = Math.min(1, (index + 0.75) / total);
  const opacity = useTransform(scrub, [from, to], [0.4, 1]);
  const dotOn = useTransform(scrub, [from, Math.min(1, from + 0.08)], [0, 1]);
  return (
    <li className="relative grid grid-cols-[2.5rem_1fr] gap-x-3 sm:grid-cols-[3rem_1fr] sm:gap-x-5">
      <div className="relative" aria-hidden>
        <span className="absolute left-1/2 top-2 h-2.5 w-2.5 -translate-x-1/2 rounded-full border border-white/25 bg-panel" />
        <motion.span
          style={{ opacity: dotOn }}
          className="absolute left-1/2 top-2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-emerald shadow-[0_0_14px_rgba(52,211,153,0.7)]"
        />
      </div>
      <motion.div style={{ opacity }} className="pb-9 sm:pb-11">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald">
          <span className="text-dim">{num} — </span>
          {name}
        </p>
        <p className="mt-1.5 max-w-md text-sm leading-relaxed text-muted">{body}</p>
      </motion.div>
    </li>
  );
}

/** Annotated branch card — the two clocks and the hard stop. Its opacity is
 *  driven by the SAME scrub MotionValue as the rail (passed in as `style`), so
 *  the fork reveals in lockstep with the beam — no parallel timer. */
function BranchCard({ kicker, title, body, tone = "emerald", loop = false, style }: {
  kicker: string;
  title: string;
  body: string;
  tone?: "emerald" | "rose";
  loop?: boolean;
  style?: MotionStyle;
}) {
  const rose = tone === "rose";
  return (
    <motion.div
      style={style}
      className={`rounded-xl2 border p-4 ${
        rose ? "border-rose/25 bg-rose/[0.04]" : "border-border bg-white/[0.03]"
      }`}
    >
      <p
        className={`font-mono text-[10px] font-semibold uppercase tracking-[0.14em] ${
          rose ? "text-rose" : "text-emerald"
        }`}
      >
        {kicker}
      </p>
      <div className="mt-1.5 flex items-center gap-2">
        <span className="text-sm font-medium text-ink tnum">{title}</span>
        {loop && (
          <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0" fill="none" aria-hidden>
            <PathDraw
              d="M14.6 5.4 A6.5 6.5 0 1 0 16.5 10"
              stroke="#34d399"
              strokeWidth={1.5}
              duration={1.1}
              dot={{ cx: 16.5, cy: 10, r: 1.6 }}
            />
          </svg>
        )}
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">{body}</p>
    </motion.div>
  );
}

export function PipelineDiagram() {
  const ref = useRef<HTMLDivElement>(null);
  // Offset reserves the final ~15% of the scrub range for the fork reveal.
  const scrub = useScrollScrub(ref, ["start 0.85", "end 0.35"]);
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const gradId = `pipe-beam-${uid}`;
  const forkGradId = `pipe-fork-${uid}`;

  // Fork geometry + branch cards all read the SAME scrub value — the beam draws
  // and each card fades up across the last 15% of the scroll range, staggered.
  const forkDraw = useTransform(scrub, [0.8, 1], [0, 1]);
  const forkDot = useTransform(scrub, [0.95, 1], [0, 1]);
  const card0 = useTransform(scrub, [0.85, 0.9], [0.4, 1]);
  const card1 = useTransform(scrub, [0.9, 0.95], [0.4, 1]);
  const card2 = useTransform(scrub, [0.95, 1], [0.4, 1]);

  return (
    <div ref={ref} className="relative mt-6">
      {/* ── Stages + tracing beam ─────────────────────────────────────── */}
      <div className="relative">
        {/* Rail: dim base path + scroll-scrubbed gradient beam. viewBox x is
            stretched (preserveAspectRatio none) so x=20 stays the rail centre
            at both column widths; non-scaling-stroke keeps the line crisp. */}
        <div aria-hidden className="brand-motion absolute bottom-0 left-0 top-2 w-10 sm:w-12">
          <svg className="h-full w-full" viewBox="0 0 40 100" preserveAspectRatio="none" fill="none">
            <defs>
              <linearGradient id={gradId} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="100">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
            <path d="M20 0 V100" stroke="rgba(255,255,255,0.08)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
            <motion.path
              d="M20 0 V100"
              stroke={`url(#${gradId})`}
              strokeWidth={2.5}
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
              style={{ pathLength: scrub }}
            />
          </svg>
        </div>
        <ol className="relative m-0 list-none p-0">
          {STAGES.map((s, i) => (
            <StageNode key={s.num} scrub={scrub} index={i} total={STAGES.length} num={s.num} name={s.name} body={s.body} />
          ))}
        </ol>
      </div>

      {/* ── Fork: two clocks + the hard stop ──────────────────────────── */}
      <div className="grid grid-cols-[2.5rem_1fr] gap-x-3 sm:grid-cols-[3rem_1fr] sm:gap-x-5">
        <div className="brand-motion relative" aria-hidden>
          {/* Beam exits the rail toward the branch cards — its pathLength is the
              SAME scrub value that drives the rail, not a separate duration. */}
          <svg className="absolute left-0 top-0 h-12 w-full" viewBox="0 0 40 48" fill="none">
            <defs>
              <linearGradient id={forkGradId} gradientUnits="userSpaceOnUse" x1="20" y1="0" x2="38" y2="40">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
            <path d="M20 0 C20 18 22 30 38 40" stroke="rgba(255,255,255,0.08)" strokeWidth={2} />
            <motion.path
              d="M20 0 C20 18 22 30 38 40"
              stroke={`url(#${forkGradId})`}
              strokeWidth={2}
              strokeLinecap="round"
              style={{ pathLength: forkDraw }}
            />
            <motion.circle
              cx={38} cy={40} r={2.5} fill="#34d399"
              style={{ opacity: forkDot, scale: forkDot, transformBox: "fill-box", transformOrigin: "center" }}
            />
          </svg>
        </div>
        <div className="pt-1">
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-dim">
            Then it runs on two clocks — plus one hard rule
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <BranchCard
              style={{ opacity: card0 }}
              kicker="Clock A — quarterly"
              title="Full re-pick"
              loop
              body="The whole pipeline runs again from the top — universe, gate, rank, weights — every quarter."
            />
            <BranchCard
              style={{ opacity: card1 }}
              kicker="Clock B — weekly"
              title="De-risk check"
              body="A weekly check in between scales exposure down if the market's own trend breaks."
            />
            <BranchCard
              style={{ opacity: card2 }}
              kicker="Hard rule — any day"
              title="−15% cut"
              tone="rose"
              body="Any single position is cut immediately if it falls 15% from entry, regardless of the calendar."
            />
          </div>
        </div>
      </div>
    </div>
  );
}
