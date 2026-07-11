"use client";

// MavenGoogleGate — full-viewport onboarding / Google sign-in gate.
//
// Rendered as a fixed overlay (like components/intro.tsx) so it escapes the
// dashboard's Nav/footer chrome and gets the full black + emerald canvas. It
// owns only the idle→signing→done *animation* timing (mirrors the design
// handoff); the actual "signed in" persistence lives in useMavenAuth and is
// delegated up via props, so the landing flow and the chat gate stay the single
// source of truth for access.
//
// Auth is a mock — persistSignIn() writes a placeholder localStorage flag. See
// TODO(auth) in useMavenAuth.ts for the real Google OAuth wiring.

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useId, useRef, useState } from "react";
import { EASE, useReducedMotionSafe } from "../motion";
import { GoogleSignInCard, type SignInStatus } from "./GoogleSignInCard";
import { AuthQuotePanel } from "./AuthQuotePanel";
import { type SignInResult } from "./useMavenAuth";

const GLOW_K: Record<string, number> = { subtle: 0.5, balanced: 0.85, intense: 1.2 };

export function MavenGoogleGate({
  open,
  dismissible = false,
  showGuest = false,
  glow = "balanced",
  googleMark = "color",
  initialError = null,
  onGoogleSignIn,
  onComplete,
  onGuest,
  onReset,
  onDismiss,
}: {
  open: boolean;
  dismissible?: boolean;
  showGuest?: boolean;
  glow?: "subtle" | "balanced" | "intense";
  googleMark?: "color" | "mono";
  /** Error to show on open (e.g. a failed OAuth callback bounced back with
   *  ?auth_error=1) — rendered as the same inline alert as sign-in errors. */
  initialError?: string | null;
  /** Starts sign-in. Real (Supabase) mode redirects to Google → the spinner
   *  stays until navigation. Mock mode returns { mock: true } → the gate plays
   *  the local confirmation. An { error } reverts to idle and surfaces it. */
  onGoogleSignIn: () => Promise<SignInResult>;
  /** Fired after the mock "signed in" confirmation holds — the parent persists
   *  the session (markSignedIn) and then navigates / reveals. Persisting here
   *  rather than mid-animation keeps the gate's `open` prop true through the
   *  confirmation so the done card isn't torn down early. (Mock mode only; in
   *  supabase mode the OAuth callback handles the redirect.) */
  onComplete?: () => void;
  /** Continue-as-guest — parent's continueAsGuest() + reveal/navigate. */
  onGuest?: () => void;
  /** "Not you?" during the done state — parent's signOut(). */
  onReset?: () => void;
  /** Dismiss without signing in (landing only) — Esc / backdrop. */
  onDismiss?: () => void;
}) {
  const reduce = useReducedMotionSafe();
  const [status, setStatus] = useState<SignInStatus>("idle");
  const [error, setError] = useState<string | null>(initialError);
  const headingId = useId();
  const primaryRef = useRef<HTMLButtonElement>(null);
  const mounted = useRef(true);
  const t1 = useRef<number | undefined>(undefined);
  const t2 = useRef<number | undefined>(undefined);
  // Latest onDismiss lives in a ref so the focus/scroll-lock effect below can
  // depend only on [open, dismissible] — an inline arrow from the parent would
  // otherwise re-run it every parent render, re-stealing keyboard focus.
  const onDismissRef = useRef(onDismiss);
  useEffect(() => {
    onDismissRef.current = onDismiss;
  });

  // Surface a late-arriving initial error (e.g. parsed from the URL after mount).
  useEffect(() => {
    if (initialError) setError(initialError);
  }, [initialError]);

  const gk = GLOW_K[glow] ?? 0.85;

  // Focus the primary button on open (keyboard users land inside the dialog);
  // Escape dismisses when allowed; body scroll is locked while the gate is up.
  useEffect(() => {
    if (!open) return;
    const focusTimer = window.setTimeout(() => primaryRef.current?.focus(), 60);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) onDismissRef.current?.();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, dismissible]);

  // Track mounted state (set true on every mount so React StrictMode's
  // mount→unmount→remount dev cycle doesn't leave it stuck false) and clear
  // timers on unmount so no setState fires after the gate closes.
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      window.clearTimeout(t1.current);
      window.clearTimeout(t2.current);
    };
  }, []);

  const handleSignIn = async () => {
    if (status !== "idle") return;
    setError(null);
    setStatus("signing");
    const res = await onGoogleSignIn();
    if (!mounted.current) return;
    if (res?.error) {
      setError(res.error);
      setStatus("idle");
      return;
    }
    if (res?.mock) {
      // Mock backend: play the confirmation locally. Persistence happens in
      // onComplete so the parent-derived `open` prop stays true through the
      // "done" card (the card isn't unmounted mid-animation).
      t1.current = window.setTimeout(() => {
        setStatus("done");
        t2.current = window.setTimeout(() => onComplete?.(), 1100);
      }, 1500);
    }
    // Real sign-in: the browser is redirecting to Google — keep the spinner up.
  };

  const handleReset = () => {
    window.clearTimeout(t1.current);
    window.clearTimeout(t2.current);
    setStatus("idle");
    onReset?.();
  };

  const glowA = {
    background: `radial-gradient(58% 52% at 50% 43%, rgba(52,211,153,${0.2 * gk}), rgba(52,211,153,${0.05 * gk}) 42%, transparent 68%)`,
    filter: "blur(6px)",
  };
  const glowB = {
    background: `radial-gradient(46% 40% at 50% 96%, rgba(52,211,153,${0.16 * gk}), transparent 66%)`,
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby={headingId}
          className="fixed inset-0 z-[90] grid place-items-center overflow-y-auto"
          style={{
            // full black + emerald canvas; safe-area aware so nothing hides under
            // the notch / home indicator on phones
            background: "radial-gradient(125% 120% at 50% 28%, #0b0e10 0%, #08090b 55%, #060708 100%)",
            paddingTop: "max(28px, var(--sat))",
            paddingRight: "max(18px, var(--sar))",
            paddingBottom: "max(28px, var(--sab))",
            paddingLeft: "max(18px, var(--sal))",
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.45, ease: EASE }}
        >
          {/* backdrop click closes the gate when dismissible (landing only) */}
          {dismissible && (
            <button type="button" aria-label="Dismiss sign-in" onClick={onDismiss} className="absolute inset-0 cursor-default" tabIndex={-1} />
          )}

          {/* ambient layers: two glow pulses, faint grid, noise, vignette */}
          <div className="pointer-events-none absolute inset-0 motion-safe:animate-gate-glow" style={glowA} />
          <div className="pointer-events-none absolute inset-0 motion-safe:animate-gate-glow2" style={glowB} />
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.55]"
            style={{
              backgroundImage: "linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)",
              backgroundSize: "46px 46px",
              WebkitMaskImage: "radial-gradient(circle at 50% 44%, #000 0%, transparent 72%)",
              maskImage: "radial-gradient(circle at 50% 44%, #000 0%, transparent 72%)",
            }}
          />
          <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(120% 100% at 50% 50%, transparent 52%, rgba(0,0,0,0.55) 100%)" }} />

          {/* the glass card */}
          <motion.div
            className="relative z-[2] flex w-full max-w-[460px] flex-col overflow-hidden rounded-[22px] border border-white/[0.08] min-[880px]:max-w-[1080px] min-[880px]:flex-row min-[880px]:rounded-[28px]"
            style={{
              background: "linear-gradient(155deg, rgba(21,24,27,0.80), rgba(10,12,14,0.90))",
              backdropFilter: "blur(20px) saturate(120%)",
              WebkitBackdropFilter: "blur(20px) saturate(120%)",
              boxShadow: "0 50px 130px -50px rgba(0,0,0,0.92), inset 0 1px 0 rgba(255,255,255,0.045)",
            }}
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.985, y: 12 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.99 }}
            transition={{ duration: 0.6, ease: EASE }}
          >
            {/* shimmer hairline along the top edge */}
            <span
              aria-hidden
              className="absolute inset-x-0 top-0 z-[5] h-[1.5px] opacity-90 motion-safe:animate-gate-shimmer"
              style={{ background: "linear-gradient(90deg, transparent, rgba(52,211,153,0.6), transparent)", backgroundSize: "55% 100%", backgroundRepeat: "no-repeat" }}
            />

            <GoogleSignInCard
              reduce={reduce}
              status={status}
              error={error}
              onSignIn={handleSignIn}
              onReset={handleReset}
              showGuest={showGuest}
              onGuest={() => onGuest?.()}
              headingId={headingId}
              googleMark={googleMark}
              primaryRef={primaryRef}
            />
            <AuthQuotePanel reduce={reduce} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
