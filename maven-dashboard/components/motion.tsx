"use client";

// Shared, reduced-motion-safe motion primitives used across the dashboard.
// Consolidates the near-duplicate Reveal / CountUp / useReducedMotionSafe that
// previously lived inline in explainer.tsx and strategies.tsx.

import {
  animate,
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useSpring,
  type HTMLMotionProps,
  type MotionValue,
} from "framer-motion";
import { useEffect, useId, useRef, useState, type PointerEvent, type ReactNode } from "react";

/** House easing — entrances (fast start, gentle settle). */
export const EASE = [0.22, 1, 0.36, 1] as const;
/** Softer variant — count-ups and value interpolation. */
export const EASE_SOFT = [0.16, 1, 0.3, 1] as const;

/** Press-feedback convention (Tailwind): compose onto any interactive element.
 *  Overrides transition-property under motion-safe — elements that also fade
 *  colors on hover should use motion-safe:transition-[color,border-color,transform]
 *  instead of the transition-transform piece. Non-interactive divs acting as
 *  buttons need role="button" + tabIndex={0} for :active to fire on iOS. */
export const PRESS = "motion-safe:transition-transform motion-safe:duration-150 motion-safe:active:scale-[0.97]";

/** Press feedback for framer motion.* elements; spread the result as props. */
export function pressTap(reduce: boolean) {
  return reduce ? {} : { whileTap: { scale: 0.97 } };
}

/** Reduced-motion that is hydration-safe: false on the server + first client
 *  render (so trees match), then the real prefers-reduced-motion after mount. */
export function useReducedMotionSafe(): boolean {
  const reduce = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? !!reduce : false;
}

/** Fade + gentle rise once the element scrolls into view. */
export function Reveal({ children, y = 16, delay = 0, className }: {
  children: ReactNode; y?: number; delay?: number; className?: string;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 1 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.6, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/** Reveal tuned for chart panels: slightly tighter rise, renders a plain div
 *  under reduced motion so recharts never mounts inside a transformed parent. */
export function ChartReveal({ children, delay = 0, className }: {
  children: ReactNode; delay?: number; className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-8% 0px" });
  const reduce = useReducedMotionSafe();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: 14 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 14 }}
      transition={{ duration: 0.55, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/** Smooth count-up to a fixed target, formatted Intl `en-IN` (lakh/crore
 *  grouping). Starts at 0 on the server + first client render (hydration-safe),
 *  then animates once scrolled into view. Driven by useMotionValue + animate()
 *  so it plays even when the OS prefers-reduced-motion flag is on (numbers are
 *  a signature moment, not a decorative loop). */
export function CountUp({ to, prefix = "", suffix = "", decimals = 2, duration = 1.3, className }: {
  to: number; prefix?: string; suffix?: string; decimals?: number; duration?: number; className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const mv = useMotionValue(0);
  const [text, setText] = useState(() =>
    new Intl.NumberFormat("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(0));
  useEffect(() => {
    if (!inView) return;
    const fmt = new Intl.NumberFormat("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    const c = animate(mv, to, { duration, ease: EASE_SOFT, onUpdate: (v) => setText(fmt.format(v)) });
    return () => c.stop();
  }, [inView, to, duration, decimals, mv]);
  return <span ref={ref} className={className ? `tnum ${className}` : "tnum"}>{prefix}{text}{suffix}</span>;
}

/** Clamp helper for pointer offsets. */
function clamp(v: number, limit: number) {
  return Math.max(-limit, Math.min(limit, v));
}

/** CTA that leans toward the cursor (pointer-tracked x/y through springs);
 *  capped offset, resets on leave. Degrades to a plain button under coarse
 *  pointers (touch) — no tracking, press feedback only. */
export function MagneticButton({ children, className, strength = 0.25, maxOffset = 10, ...rest }: {
  strength?: number; maxOffset?: number;
} & HTMLMotionProps<"button">) {
  const ref = useRef<HTMLButtonElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 320, damping: 22 });
  const sy = useSpring(y, { stiffness: 320, damping: 22 });
  // false on server + first client render (hydration-safe), then the real
  // pointer capability after mount.
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFine(mq.matches);
    const on = (e: MediaQueryListEvent) => setFine(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const onPointerMove = (e: PointerEvent<HTMLButtonElement>) => {
    if (!fine || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    x.set(clamp((e.clientX - (r.left + r.width / 2)) * strength, maxOffset));
    y.set(clamp((e.clientY - (r.top + r.height / 2)) * strength, maxOffset));
  };
  const reset = () => { x.set(0); y.set(0); };
  return (
    <motion.button
      ref={ref}
      className={className}
      style={{ x: sx, y: sy }}
      onPointerMove={onPointerMove}
      onPointerLeave={reset}
      whileTap={{ scale: 0.97 }}
      {...rest}
    >
      {children}
    </motion.button>
  );
}

/** SVG path that draws itself in when scrolled into view (motion.path
 *  pathLength). Optional gradient stroke, area-fill fade-in, and endpoint dot.
 *  Render inside an <svg>; JS-driven, so it plays under OS reduced-motion (the
 *  .brand-motion class also exempts it from the global CSS damp). */
export function PathDraw({
  d, stroke = "#34d399", strokeWidth = 2, duration = 1.4, delay = 0,
  gradient, areaD, areaFill = "rgba(52,211,153,0.08)", dot, className,
}: {
  d: string;
  stroke?: string;
  strokeWidth?: number;
  duration?: number;
  delay?: number;
  /** Left→right linear gradient stroke; overrides `stroke`. */
  gradient?: { from: string; to: string };
  /** Closed area path under the line; fades in as the line finishes. */
  areaD?: string;
  areaFill?: string;
  /** Endpoint dot, revealed once the draw completes. */
  dot?: { cx: number; cy: number; r?: number; fill?: string };
  className?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const gradId = `pathdraw-${uid}`;
  const viewport = { once: true, margin: "-10% 0px" } as const;
  return (
    <g className={className ? `brand-motion ${className}` : "brand-motion"}>
      {gradient && (
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={gradient.from} />
            <stop offset="100%" stopColor={gradient.to} />
          </linearGradient>
        </defs>
      )}
      {areaD && (
        <motion.path
          d={areaD}
          fill={areaFill}
          stroke="none"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={viewport}
          transition={{ duration: 0.8, delay: delay + duration * 0.55, ease: EASE_SOFT }}
        />
      )}
      <motion.path
        d={d}
        fill="none"
        stroke={gradient ? `url(#${gradId})` : stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={viewport}
        transition={{ duration, delay, ease: EASE }}
      />
      {dot && (
        <motion.circle
          cx={dot.cx}
          cy={dot.cy}
          r={dot.r ?? 3}
          fill={dot.fill ?? (gradient ? gradient.to : stroke)}
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
          initial={{ opacity: 0, scale: 0 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={viewport}
          transition={{ duration: 0.35, delay: delay + duration, ease: EASE_SOFT }}
        />
      )}
    </g>
  );
}

type ScrollOptions = NonNullable<Parameters<typeof useScroll>[0]>;

/** House scroll-scrub: useScroll({target, offset}) piped through a spring
 *  (stiffness 100, damping 30 by default). Returns the sprung progress
 *  MotionValue — feed it to useTransform for scrubbed signature moments.
 *  Pass `spring` to stiffen/soften a specific scrub; existing callers keep
 *  the house default untouched. */
export function useScrollScrub(
  target: ScrollOptions["target"],
  offset: ScrollOptions["offset"] = ["start end", "end start"],
  spring: { stiffness?: number; damping?: number; restDelta?: number } = {},
): MotionValue<number> {
  const { scrollYProgress } = useScroll({ target, offset });
  return useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001, ...spring });
}

/** layoutId-based active-tab indicator: render inside the ACTIVE item only
 *  (absolute-positioned via className) and framer animates position/size
 *  between tabs. Use one layoutId per tab group. */
export function LayoutPill({ layoutId = "layout-pill", className, children }: {
  layoutId?: string; className?: string; children?: ReactNode;
}) {
  return (
    <motion.span
      layoutId={layoutId}
      className={className}
      transition={{ type: "spring", stiffness: 420, damping: 34 }}
      aria-hidden
    >
      {children}
    </motion.span>
  );
}

/** Section eyebrow: mono caps 11px, wide tracking. Optional numbered variant
 *  ("01 — LABEL") and gold/emerald tone. */
export function SectionEyebrow({ children, number, tone = "emerald", className }: {
  children: ReactNode; number?: string; tone?: "emerald" | "gold"; className?: string;
}) {
  const toneCls = tone === "gold" ? "text-gold-soft" : "text-emerald";
  return (
    <p className={`font-mono text-[11px] font-semibold uppercase tracking-[0.16em] ${toneCls}${className ? ` ${className}` : ""}`}>
      {number && <span className="text-dim">{number} — </span>}
      {children}
    </p>
  );
}
