"use client";

import { animate, motion, useInView, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

export function useReducedMotionSafe(): boolean {
  const reduce = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? !!reduce : false;
}

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

export function CountUp({ to, prefix = "", suffix = "", decimals = 2, duration = 1.1 }: {
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

export function Stagger({ children, className, delay = 0, gap = 0.07 }: {
  children: ReactNode; className?: string; delay?: number; gap?: number;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      className={className}
      initial="hide"
      whileInView="show"
      viewport={{ once: true, margin: "-8% 0px" }}
      variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : gap, delayChildren: delay } } }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, y = 14, className }: {
  children: ReactNode; y?: number; className?: string;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      className={className}
      variants={{
        hide: reduce ? { opacity: 1 } : { opacity: 0, y },
        show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
      }}
    >
      {children}
    </motion.div>
  );
}