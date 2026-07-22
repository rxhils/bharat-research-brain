"use client";

// Left-hand auth panel of the Maven Google gate: brand mark, welcome copy, the
// Google sign-in button (idle → signing → done state machine, driven by props),
// privacy microcopy, and an optional guest escape. Also renders a compact quote
// block that only appears on mobile (where the right visual panel is hidden) —
// placed BELOW the action zone so the CTA lands in the first viewport on phones.
//
// Motion: no decorative loops. The idle CTA leans toward the cursor (magnetic,
// pointer-fine only — implemented locally because the shared MagneticButton
// doesn't forward the focus ref this dialog needs). The loading spinner and the
// done-state progress sweep are functional and kept.

import { motion, useMotionValue, useSpring, type Variants } from "framer-motion";
import { useEffect, useState, type PointerEvent, type RefObject } from "react";
import { EASE, PathDraw } from "../motion";
import { EQUITY_SERIES } from "@/app/backtest/data/equity-series";

export type SignInStatus = "idle" | "signing" | "done";

/** Compact study path for the mobile quote card — same source as the desktop
 *  Draft Study (the frozen Enhanced F+ equity export), downsampled harder and
 *  mapped into a small strip so phones get the page's signature moment too.
 *  Verbatim data; the between-anchor shape is the committed interpolation. */
const MOBILE_STUDY_D = (() => {
  const W = 200, H = 44, padL = 4, padR = 6, padT = 6, padB = 8;
  const pts = EQUITY_SERIES.filter((_, i) => i % 4 === 0);
  const last = EQUITY_SERIES[EQUITY_SERIES.length - 1];
  if (pts[pts.length - 1] !== last) pts.push(last);
  const vals = pts.map((p) => p.fplus);
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  return pts
    .map((p, i) => {
      const x = padL + (i / (pts.length - 1)) * (W - padL - padR);
      const y = padT + (1 - (p.fplus - lo) / span) * (H - padT - padB);
      return `${i === 0 ? "M" : "L"}${Math.round(x * 10) / 10} ${Math.round(y * 10) / 10}`;
    })
    .join(" ");
})();

const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

/** Static emerald gradient text (no shimmer loop — stillness is the signal). */
const GRADIENT_TEXT = {
  background: "linear-gradient(100deg,#34d399,#7ce7bd,#10b981)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  WebkitTextFillColor: "transparent",
  color: "transparent",
} as const;

function BrandMark() {
  return (
    <span className="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-[13px] border border-white/[0.08]" style={{ background: "linear-gradient(160deg,#171b1f,#0e1114)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 0 26px -8px rgba(52,211,153,0.4)" }}>
      <svg width="26" height="26" viewBox="0 0 100 100" fill="none" role="img" aria-label="Maven">
        <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="89" cy="17" r="8" fill="#34d399" />
      </svg>
    </span>
  );
}

function GoogleGlyph({ mono }: { mono: boolean }) {
  if (mono) {
    return (
      <svg width="19" height="19" viewBox="0 0 48 48" className="shrink-0" aria-hidden>
        <path fill="#e9ebec" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
        <path fill="#c6cace" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
        <path fill="#b0b4b9" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
        <path fill="#dde0e2" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      </svg>
    );
  }
  return (
    <svg width="19" height="19" viewBox="0 0 48 48" className="shrink-0" aria-hidden>
      <path fill="#ea4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285f4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#fbbc05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34a853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

function clampOffset(v: number, limit: number) {
  return Math.max(-limit, Math.min(limit, v));
}

export function GoogleSignInCard({
  reduce,
  status,
  error,
  onSignIn,
  onReset,
  showGuest,
  onGuest,
  headingId,
  googleMark = "color",
  primaryRef,
}: {
  reduce: boolean;
  status: SignInStatus;
  error?: string | null;
  onSignIn: () => void;
  onReset: () => void;
  showGuest: boolean;
  onGuest: () => void;
  headingId: string;
  googleMark?: "color" | "mono";
  primaryRef?: RefObject<HTMLButtonElement>;
}) {
  // Magnetic CTA (interaction-triggered, so OS reduced-motion is honored
  // naturally: no pointer, no motion). Pointer-fine gate keeps touch inert.
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 400, damping: 28 });
  const sy = useSpring(my, { stiffness: 400, damping: 28 });
  const [finePointer, setFinePointer] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFinePointer(mq.matches);
    const on = (e: MediaQueryListEvent) => setFinePointer(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const onCtaPointerMove = (e: PointerEvent<HTMLButtonElement>) => {
    if (!finePointer) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set(clampOffset((e.clientX - (r.left + r.width / 2)) * 0.12, 6));
    my.set(clampOffset((e.clientY - (r.top + r.height / 2)) * 0.12, 6));
  };
  const onCtaPointerLeave = () => {
    mx.set(0);
    my.set(0);
  };

  return (
    <motion.section
      className="relative flex min-w-0 flex-[1_1_auto] flex-col justify-center p-[clamp(26px,7vw,38px)] min-[880px]:flex-[1_1_45%] min-[880px]:p-[clamp(38px,3.4vw,56px)]"
      style={{ gap: "clamp(16px,2.1vw,24px)" }}
      variants={{ show: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } } }}
      initial={reduce ? false : "hidden"}
      animate="show"
    >
      {/* brand lockup — the tagline is gold use #2 (the only other gold on the page) */}
      <motion.div variants={rise} className="flex items-center gap-3">
        <BrandMark />
        <span className="flex flex-col gap-[3px]">
          <span className="font-sans text-[18px] font-semibold leading-none tracking-[0.005em] text-ink">Maven</span>
          <span className="font-sans text-[9.5px] font-medium uppercase leading-none tracking-[0.17em] text-[#c9a961]/80">India Market Intelligence</span>
        </span>
      </motion.div>

      {/* eyebrow — static emerald tick, mono technical label (no sweep loop) */}
      <motion.div variants={rise} className="flex items-center gap-2.5">
        <span className="h-0.5 w-[34px] shrink-0 rounded-sm bg-emerald/40" />
        <span className="font-mono text-[10px] font-semibold uppercase leading-none tracking-[0.2em] text-muted">Secure Google Sign-In</span>
      </motion.div>

      {/* headline + subheadline */}
      <motion.h1 variants={rise} id={headingId} className="m-0 font-serif font-normal leading-[1.02] tracking-[-0.02em] text-ink" style={{ fontSize: "clamp(2.15rem, 1rem + 3.8vw, 3.6rem)" }}>
        Your research desk, <em className="font-serif italic text-ink">after hours.</em>
      </motion.h1>
      <motion.p variants={rise} className="m-0 max-w-[40ch] font-sans text-[15px] leading-[1.6] text-muted">
        Your India market research workspace, saved securely to your account.
      </motion.p>

      {/* action zone — first in DOM after the copy so the CTA is in the first
          mobile viewport (the compact quote block renders below it) */}
      <motion.div variants={rise} className="flex flex-col gap-3.5">
        {status === "idle" && (
          <div className="group relative">
            {/* pool of light on the door — a soft emerald bloom behind the CTA
                makes it the single brightest object on the page; brightens on
                hover only (interaction-gated, no loop) */}
            <div
              aria-hidden
              className="pointer-events-none absolute -inset-4 rounded-[22px] opacity-70 blur-2xl transition-opacity duration-300 group-hover:opacity-100"
              style={{ background: "radial-gradient(55% 65% at 50% 45%, rgba(52,211,153,0.18), transparent 72%)" }}
            />
            <motion.button
              ref={primaryRef}
              type="button"
              onClick={onSignIn}
              onPointerMove={onCtaPointerMove}
              onPointerLeave={onCtaPointerLeave}
              whileTap={{ scale: 0.97 }}
              aria-label="Continue with Google"
              className="relative flex min-h-[54px] w-full items-center justify-center gap-3 overflow-hidden rounded-[14px] border border-white/[0.11] px-5 font-sans text-[15px] font-medium text-ink transition-[border-color,box-shadow] duration-200 group-hover:border-emerald/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60"
              style={{ x: sx, y: sy, background: "linear-gradient(180deg, rgba(30,34,38,0.92), rgba(16,19,22,0.96))", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 10px 28px -14px rgba(0,0,0,0.85)" }}
            >
              {/* top-edge hairline that brightens on hover */}
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald/50 to-transparent opacity-50 transition-opacity duration-200 group-hover:opacity-100"
              />
              <GoogleGlyph mono={googleMark === "mono"} />
              <span>Continue with Google</span>
            </motion.button>
          </div>
        )}

        {status === "signing" && (
          <button
            type="button"
            disabled
            aria-live="polite"
            className="flex min-h-[54px] w-full cursor-default items-center justify-center gap-3 rounded-[14px] border border-emerald/30 px-5 font-sans text-[15px] font-medium text-ink/90"
            style={{ background: "linear-gradient(180deg, rgba(30,34,38,0.92), rgba(16,19,22,0.96))", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)" }}
          >
            <span className="inline-block h-[18px] w-[18px] shrink-0 rounded-full border-2 border-white/20 border-t-emerald motion-safe:animate-gate-spin" />
            <span>Connecting to Google…</span>
          </button>
        )}

        {status === "done" && (
          <div className="flex flex-col gap-2.5 rounded-[14px] border border-emerald/30 p-4" role="status" aria-live="polite" style={{ background: "linear-gradient(180deg, rgba(20,32,27,0.72), rgba(12,18,16,0.72))", boxShadow: "0 0 44px -18px rgba(52,211,153,0.55)" }}>
            <div className="flex items-center gap-3">
              <svg width="30" height="30" viewBox="0 0 24 24" className="shrink-0" aria-hidden>
                <circle cx="12" cy="12" r="11" fill="rgba(52,211,153,0.16)" stroke="#10b981" strokeWidth="1.3" />
                <path d="M7.4 12.3 l3 3 6.2 -6.6" stroke="#34d399" strokeWidth="1.9" fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="flex flex-col gap-0.5">
                <span className="font-sans text-sm font-semibold leading-tight text-ink">Signed in with Google</span>
                <span className="font-sans text-xs leading-snug text-emerald/80">Restoring your saved chats &amp; research…</span>
              </span>
            </div>
            <div className="h-0.5 overflow-hidden rounded-sm bg-emerald/20">
              <div className="h-full w-[42%] motion-safe:animate-gate-sweep" style={{ background: "linear-gradient(90deg, transparent, #34d399, transparent)" }} />
            </div>
            <button type="button" onClick={onReset} className="self-start rounded font-sans text-xs font-medium text-dim transition-colors hover:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60">
              Not you? Use another account
            </button>
          </div>
        )}

        {error && (
          <p role="alert" className="m-0 font-sans text-[12.5px] leading-snug text-rose">
            {error}
          </p>
        )}

        {/* privacy support line */}
        <div className="flex items-start gap-2">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0" aria-hidden>
            <path d="M12 3l7 3v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V6l7-3z" stroke="#34d399" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M9 12l2 2 4-4" stroke="#34d399" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="m-0 font-sans text-[12.5px] leading-[1.5] text-muted">Your research history stays linked to your own Google account.</p>
        </div>

        {/* microcopy */}
        <p className="m-0 font-sans text-[11.5px] font-medium leading-snug tracking-[0.01em] text-dim">Private by default &nbsp;·&nbsp; Built for your market workflow.</p>

        {showGuest && (
          <button type="button" onClick={onGuest} className="self-start rounded font-sans text-[12.5px] font-medium text-muted transition-colors hover:text-emerald focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60">
            Continue as guest →
          </button>
        )}
      </motion.div>

      {/* mobile-only compact quote (right panel is hidden under 880px) — no
          film here: video below a CTA on a login is weight without persuasion */}
      <motion.div variants={rise} className="flex flex-col gap-2.5 rounded-2xl border border-white/[0.06] p-[14px] min-[880px]:hidden" style={{ background: "linear-gradient(160deg, rgba(16,19,22,0.7), rgba(9,11,13,0.5))" }}>
        <p className="m-0 font-serif text-[18px] font-normal italic leading-[1.35] text-ink">
          Ask better questions.{" "}
          <span className="font-serif italic" style={GRADIENT_TEXT}>Build better conviction.</span>
        </p>
        {/* the page's signature moment on phones: the real F+ equity study draws
            itself once (plays under OS reduced-motion — brand-motion surface) */}
        <svg viewBox="0 0 200 44" className="block h-9 w-full" preserveAspectRatio="none" aria-hidden>
          <PathDraw d={MOBILE_STUDY_D} stroke="#34d399" strokeWidth={1.8} duration={0.9} delay={0.2} />
        </svg>
        <p className="m-0 font-mono text-[10.5px] font-medium tracking-[0.06em] text-dim">Enhanced F+ backtest, 2021–26 &nbsp;·&nbsp; not a live track record</p>
      </motion.div>
    </motion.section>
  );
}
