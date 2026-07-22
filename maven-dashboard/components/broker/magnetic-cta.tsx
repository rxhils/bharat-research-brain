"use client";

// Anchor variant of the shared MagneticButton (components/motion.tsx is frozen
// and only ships a <button>). Same recipe: pointer offset → motion values →
// springs (stiffness 350 / damping 25 per the /broker plan), capped ±10px,
// reset on leave. Degrades to a plain link under coarse pointers — press
// feedback only. Motion-value driven, so the lean plays under OS reduced-motion.

import { motion, useMotionValue, useSpring } from "framer-motion";
import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";

function clamp(v: number, limit: number) {
  return Math.max(-limit, Math.min(limit, v));
}

export function MagneticCTA({ href, children, className, strength = 0.25, maxOffset = 10 }: {
  href: string;
  children: ReactNode;
  className?: string;
  strength?: number;
  maxOffset?: number;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 350, damping: 25 });
  const sy = useSpring(y, { stiffness: 350, damping: 25 });
  // false on server + first client render (hydration-safe), then the real
  // pointer capability after mount — mirrors MagneticButton.
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFine(mq.matches);
    const on = (e: MediaQueryListEvent) => setFine(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const onPointerMove = (e: PointerEvent<HTMLAnchorElement>) => {
    if (!fine || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    x.set(clamp((e.clientX - (r.left + r.width / 2)) * strength, maxOffset));
    y.set(clamp((e.clientY - (r.top + r.height / 2)) * strength, maxOffset));
  };
  const reset = () => {
    x.set(0);
    y.set(0);
  };
  return (
    <motion.a
      ref={ref}
      href={href}
      className={className ? `brand-motion ${className}` : "brand-motion"}
      style={{ x: sx, y: sy }}
      onPointerMove={onPointerMove}
      onPointerLeave={reset}
      whileTap={{ scale: 0.97 }}
    >
      {children}
    </motion.a>
  );
}
