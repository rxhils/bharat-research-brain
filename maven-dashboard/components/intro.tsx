"use client";

// First-visit intro: dims the page behind, plays the brand video centered, with
// a "Skip intro" button. Shows once per browser (localStorage), and auto-dismisses
// when the video ends. UI only — no data/network beyond the static /intro.mp4.

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { EASE, pressTap, useReducedMotionSafe } from "./motion";

const SEEN_KEY = "maven_intro_seen_v1";

// onFinished (optional, non-visual): fires when the intro phase ends — the video
// played/errored, the user pressed Skip, or the intro was already seen and won't
// show. The landing flow uses it to reveal the Google gate afterwards. Adding it
// changes nothing about the intro's appearance, timing, or layout.
export function IntroOverlay({ onFinished }: { onFinished?: () => void } = {}) {
  const reduce = useReducedMotionSafe();
  const [show, setShow] = useState(false);
  const [ready, setReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const skipRef = useRef<HTMLButtonElement>(null);

  // onFinished must fire exactly once: Skip near the video's natural end would
  // otherwise fire dismiss() twice (the exiting <video> stays mounted through
  // the AnimatePresence exit and its onEnded still fires), and StrictMode
  // double-invokes the mount effect in dev.
  const finishedRef = useRef(false);
  const finish = () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onFinished?.();
  };

  useEffect(() => {
    setReady(true);
    try {
      if (!window.localStorage.getItem(SEEN_KEY)) setShow(true);
      else finish(); // already seen → intro phase is already over
    } catch {
      /* localStorage unavailable — just don't show the intro */
      finish();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const dismiss = () => {
    try { window.localStorage.setItem(SEEN_KEY, "1"); } catch { /* ignore */ }
    setShow(false);
    finish(); // intro played / skipped → hand off to the gate
  };

  // Modal focus + escape hatch: the overlay's only control (Skip) takes focus on
  // open so keyboard users aren't stranded behind the dialog, and Escape dismisses.
  useEffect(() => {
    if (!show) return;
    skipRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [show]); // eslint-disable-line react-hooks/exhaustive-deps

  // Avoid a hydration flash: render nothing until mounted (the gate is client-only).
  if (!ready) return null;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          // full dynamic-viewport cover; safe-area-aware inset so the card never
          // hides under the notch or home indicator on phones
          role="dialog"
          aria-modal="true"
          aria-label="Maven intro video"
          className="fixed inset-0 z-[100] flex h-dvh items-center justify-center"
          style={{
            paddingTop: "max(1.25rem, var(--sat))",
            paddingRight: "max(1.25rem, var(--sar))",
            paddingBottom: "max(1.25rem, var(--sab))",
            paddingLeft: "max(1.25rem, var(--sal))",
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          {/* dim + blur the page (How it works) behind */}
          <div className="absolute inset-0 bg-bg/90 backdrop-blur-md" />

          {/* video card — bounded by BOTH width and height so it never overflows
              on phones (portrait = full width strip; landscape = capped height). */}
          <motion.div
            className="relative flex w-full max-w-5xl items-center justify-center"
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 10 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.985 }}
            transition={{ duration: 0.7, delay: 0.08, ease: EASE }}
          >
            <div
              className="pointer-events-none absolute -inset-4 -z-10 rounded-[2rem] opacity-70 blur-3xl sm:-inset-6"
              style={{ background: "radial-gradient(closest-side, rgba(52,211,153,0.22), transparent 75%)" }}
            />
            <video
              ref={videoRef}
              className="max-h-[78svh] max-w-full rounded-xl border border-white/10 shadow-[0_40px_120px_-40px_rgba(52,211,153,0.5)] sm:rounded-2xl"
              src="/intro.mp4"
              autoPlay
              muted
              playsInline
              preload="auto"
              onEnded={dismiss}
              onError={dismiss}
            />
          </motion.div>

          {/* skip — clear of the iOS home indicator / notch (safe-area vars),
              >=44px tap target; press feedback gated via pressTap */}
          <motion.button
            ref={skipRef}
            type="button"
            onClick={dismiss}
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 6 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ delay: 0.9, duration: 0.5, ease: EASE }}
            {...pressTap(reduce)}
            style={{
              bottom: "max(1.25rem, var(--sab))",
              right: "max(1.25rem, var(--sar))",
            }}
            className="group absolute inline-flex min-h-[44px] items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-4 py-2.5 text-sm text-muted backdrop-blur-md transition-[color,border-color] hover:border-emerald/40 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60 sm:px-5"
          >
            Skip intro
            <span aria-hidden className="motion-safe:transition-transform motion-safe:duration-300 motion-safe:group-hover:translate-x-0.5">→</span>
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
