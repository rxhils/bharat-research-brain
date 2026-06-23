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

          {/* video card */}
          <motion.div
            className="relative w-full max-w-5xl"
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.985 }}
            transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          >
            <div
              className="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] opacity-70 blur-3xl"
              style={{ background: "radial-gradient(closest-side, rgba(52,211,153,0.22), transparent 75%)" }}
            />
            <video
              ref={videoRef}
              className="w-full rounded-2xl border border-white/10 shadow-[0_50px_140px_-40px_rgba(52,211,153,0.5)]"
              src="/intro.mp4"
              autoPlay
              muted
              playsInline
              preload="auto"
              onEnded={dismiss}
              onError={dismiss}
            />
          </motion.div>

          {/* skip */}
          <motion.button
            type="button"
            onClick={dismiss}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9, duration: 0.5 }}
            className="group absolute bottom-7 right-7 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-4 py-2 text-sm text-muted backdrop-blur-md transition-colors hover:border-emerald/40 hover:text-ink sm:bottom-9 sm:right-9"
          >
            Skip intro
            <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-0.5">→</span>
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
