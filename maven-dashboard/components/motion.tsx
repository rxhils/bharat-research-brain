"use client";

// Shared, reduced-motion-safe motion primitives used across the dashboard.
// Consolidates the near-duplicate Reveal / CountUp / useReducedMotionSafe that
// previously lived inline in explainer.tsx and strategies.tsx.

import { animate, motion, useInView, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

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

/** Smooth count-up to a fixed target. Starts at 0 on the server + first client
 *  render (hydration-safe), then animates once scrolled into view. */
export function CountUp({ to, prefix = "", suffix = "", decimals = 2, duration = 1.3 }: {
  to: number; prefix?: string; suffix?: string; decimals?: number; duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const reduce = useReducedMotionSafe();
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!inView) return;
    if (reduce) { setV(to); return; }
    const c = animate(0, to, { duration, ease: EASE_SOFT, onUpdate: setV });
    return () => c.stop();
  }, [inView, to, duration, reduce]);
  return <span ref={ref} className="tnum">{prefix}{v.toFixed(decimals)}{suffix}</span>;
}
