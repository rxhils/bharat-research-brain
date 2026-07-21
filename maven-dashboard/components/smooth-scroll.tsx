"use client";

// Lenis smooth scroll, driven by framer-motion's frame loop (autoRaf: false)
// so scroll smoothing and MotionValue scrubs share one rAF — no double loops,
// no drift. Wraps native scroll, so position: sticky pinning and useScroll
// keep working untouched.
//
// Gating: this deliberately does NOT check the OS prefers-reduced-motion query.
// The page's signature moments are user-driven scroll scrubs that must stay
// smooth under the OS flag (house rule — see .brand-motion in globals.css).
// When an app-level "reduce motion" setting lands, pass `disabled` from it and
// children render without Lenis.

import { ReactLenis, type LenisRef } from "lenis/react";
import { cancelFrame, frame } from "framer-motion";
import { useEffect, useRef, type ReactNode } from "react";

export function SmoothScroll({ children, disabled = false }: {
  children: ReactNode;
  disabled?: boolean;
}) {
  const lenisRef = useRef<LenisRef>(null);
  useEffect(() => {
    if (disabled) return;
    function raf(data: { timestamp: number }) {
      lenisRef.current?.lenis?.raf(data.timestamp);
    }
    frame.update(raf, true);
    return () => cancelFrame(raf);
  }, [disabled]);
  if (disabled) return <>{children}</>;
  return (
    <ReactLenis root options={{ lerp: 0.1, autoRaf: false }} ref={lenisRef}>
      {children}
    </ReactLenis>
  );
}
