"use client";

// First-visit intro: dims the page behind, plays the brand video centered, with
// a "Skip intro" button. Shows once per browser (localStorage), and auto-dismisses
// when the video ends. UI only — no data/network beyond the static /intro.mp4.

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const SEEN_KEY = "maven_intro_seen_v1";

export function IntroOverlay() {
  const [show, setShow] = useState(false);
  const [ready, setReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    setReady(true);
    try {
      if (!window.localStorage.getItem(SEEN_KEY)) setShow(true);
    } catch {
      /* localStorage unavailable — just don't show the intro */
    }
  }, []);

  const dismiss = () => {
    try { window.localStorage.setItem(SEEN_KEY, "1"); } catch { /* ignore */ }
    setShow(false);
  };

  // Avoid a hydration flash: render nothing until mounted (the gate is client-only).
  if (!ready) return null;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* dim + blur the page (How it works) behind */}
          <div className="absolute inset-0 bg-bg/90 backdrop-blur-md" />

          {/* video card — bounded by BOTH width and height so it never overflows
              on phones (portrait = full width strip; landscape = capped height). */}
          <motion.div
            className="relative flex w-full max-w-5xl items-center justify-center"
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.985 }}
            transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
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

          {/* skip — positioned clear of the iOS home indicator (safe-area), large tap target */}
          <motion.button
            type="button"
            onClick={dismiss}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9, duration: 0.5 }}
            style={{
              bottom: "calc(env(safe-area-inset-bottom, 0px) + 1.25rem)",
              right: "calc(env(safe-area-inset-right, 0px) + 1.25rem)",
            }}
            className="group absolute inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-4 py-2.5 text-sm text-muted backdrop-blur-md transition-colors hover:border-emerald/40 hover:text-ink active:scale-95 sm:px-5"
          >
            Skip intro
            <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-0.5">→</span>
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
