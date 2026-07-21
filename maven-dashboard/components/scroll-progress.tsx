"use client";

// ScrollProgress — fixed 2px reading-progress bar along the top of the page.
// scaleX driven by page scroll through the house spring (stiffness 100,
// damping 30). Motion-value-driven + .brand-motion, so it tracks scroll even
// under the OS prefers-reduced-motion flag (it is scrubbed, not autonomous).

import { motion, useScroll, useSpring } from "framer-motion";

/** Fixed 2px top scroll-progress bar with the emerald house gradient. */
export function ScrollProgress({ className }: { className?: string }) {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });
  return (
    <motion.div
      aria-hidden
      style={{ scaleX }}
      className={`brand-motion fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-gradient-to-r from-emerald-deep via-emerald to-emerald/50${className ? ` ${className}` : ""}`}
    />
  );
}
