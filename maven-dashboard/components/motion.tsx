"use client";

// Shared, reduced-motion-safe motion primitives used across the dashboard.
// Consolidates the near-duplicate Reveal / CountUp / useReducedMotionSafe that
// previously lived inline in explainer.tsx and strategies.tsx.

import { animate, motion, useInView, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

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
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
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
    const c = animate(0, to, { duration, ease: [0.16, 1, 0.3, 1], onUpdate: setV });
    return () => c.stop();
  }, [inView, to, duration, reduce]);
  return <span ref={ref} className="tnum">{prefix}{v.toFixed(decimals)}{suffix}</span>;
}
