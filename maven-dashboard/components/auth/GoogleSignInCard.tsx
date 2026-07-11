"use client";

// Left-hand auth panel of the Maven Google gate: brand mark, welcome copy, the
// Google sign-in button (idle → signing → done state machine, driven by props),
// privacy microcopy, and an optional guest escape. Also renders a compact quote
// block that only appears on mobile (where the right visual panel is hidden).

import { motion, type Variants } from "framer-motion";
import { type RefObject } from "react";
import { EASE } from "../motion";
import { GateFilm } from "./GateFilm";

export type SignInStatus = "idle" | "signing" | "done";

const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

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
  return (
    <motion.section
      className="relative flex min-w-0 flex-[1_1_auto] flex-col justify-center p-[clamp(26px,7vw,38px)] min-[880px]:flex-[1_1_45%] min-[880px]:p-[clamp(38px,3.4vw,56px)]"
      style={{ gap: "clamp(16px,2.1vw,24px)" }}
      variants={{ show: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } } }}
      initial={reduce ? false : "hidden"}
      animate="show"
    >
      {/* brand lockup */}
      <motion.div variants={rise} className="flex items-center gap-3">
        <BrandMark />
        <span className="flex flex-col gap-[3px]">
          <span className="font-sans text-[18px] font-semibold leading-none tracking-[0.005em] text-ink">Maven</span>
          <span className="font-sans text-[9.5px] font-medium uppercase leading-none tracking-[0.17em] text-dim">India Market Intelligence</span>
        </span>
      </motion.div>

      {/* eyebrow with sweeping underline */}
      <motion.div variants={rise} className="flex items-center gap-2.5">
        <span className="relative h-0.5 w-[34px] shrink-0 overflow-hidden rounded-sm bg-emerald/20">
          <span className="absolute inset-0 motion-safe:animate-gate-sweep" style={{ background: "linear-gradient(90deg, transparent, #34d399, transparent)" }} />
        </span>
        <span className="font-sans text-[10.5px] font-semibold uppercase leading-none tracking-[0.2em] text-muted">Secure Google Sign-In</span>
      </motion.div>

      {/* headline + subheadline */}
      <motion.h1 variants={rise} id={headingId} className="m-0 font-serif text-[clamp(30px,4.2vw,45px)] font-normal leading-[1.06] tracking-[-0.01em] text-ink">
        Welcome to <em className="font-serif italic text-ink">Maven</em>
      </motion.h1>
      <motion.p variants={rise} className="m-0 max-w-[40ch] font-sans text-[clamp(14px,1.35vw,15.5px)] leading-[1.6] text-muted">
        Your India market research workspace, saved securely to your account.
      </motion.p>

      {/* mobile-only compact quote (right panel is hidden under 880px) */}
      <motion.div variants={rise} className="flex flex-col gap-3 rounded-2xl border border-white/[0.06] p-[14px] min-[880px]:hidden" style={{ background: "linear-gradient(160deg, rgba(16,19,22,0.7), rgba(9,11,13,0.5))" }}>
        {/* the product film — same /intro.mp4, already cached from the intro */}
        <GateFilm className="rounded-xl border border-white/[0.06]" />
        <p className="m-0 font-serif text-[19px] font-normal italic leading-[1.35] text-ink">
          Ask better questions.{" "}
          <span className="font-serif italic motion-safe:animate-[gateShimmer_8s_linear_infinite]" style={{ background: "linear-gradient(100deg,#34d399,#7ce7bd,#10b981)", backgroundSize: "200% 100%", WebkitBackgroundClip: "text", backgroundClip: "text", WebkitTextFillColor: "transparent", color: "transparent" }}>Build better conviction.</span>
        </p>
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded-[9px] border border-white/[0.07] bg-white/[0.03] px-2.5 py-1.5 font-sans text-[11px] font-medium text-muted">Saved chats</span>
          <span className="rounded-[9px] border border-white/[0.07] bg-white/[0.03] px-2.5 py-1.5 font-sans text-[11px] font-medium text-muted">Personal research</span>
          <span className="rounded-[9px] border border-emerald/25 bg-emerald/[0.07] px-2.5 py-1.5 font-sans text-[11px] font-medium text-emerald/90">Google-secured</span>
        </div>
      </motion.div>

      {/* action zone */}
      <motion.div variants={rise} className="flex flex-col gap-3.5">
        {status === "idle" && (
          <button
            ref={primaryRef}
            type="button"
            onClick={onSignIn}
            aria-label="Continue with Google"
            className="relative flex min-h-[54px] w-full items-center justify-center gap-3 overflow-hidden rounded-[14px] border border-white/[0.11] px-5 font-sans text-[15px] font-medium text-ink transition-[transform,border-color,box-shadow] duration-200 hover:border-emerald/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60 motion-safe:hover:-translate-y-px motion-safe:active:translate-y-0"
            style={{ background: "linear-gradient(180deg, rgba(30,34,38,0.92), rgba(16,19,22,0.96))", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 10px 28px -14px rgba(0,0,0,0.85)" }}
          >
            {/* slow light sweep across the CTA — the one moving highlight on the left panel */}
            <span aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-1/2 -skew-x-12 motion-safe:animate-[gateSweep_6s_ease-in-out_infinite]" style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.055), transparent)" }} />
            <GoogleGlyph mono={googleMark === "mono"} />
            <span>Continue with Google</span>
          </button>
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
    </motion.section>
  );
}
