"use client";

// Right-hand visual panel of the Maven Google gate (desktop only). Pure
// presentation: the brand quote, a live NSE/BSE pill, a mini research-chat
// mockup with a self-drawing emerald chart line, and the "what you get" pills.
// Colors/fonts come from the app theme (emerald #34d399, --font-serif Fraunces).

import { motion, type Variants } from "framer-motion";
import { EASE } from "../motion";
import { GateFilm } from "./GateFilm";

const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

function MiniMark() {
  return (
    <span className="grid h-[31px] w-[31px] shrink-0 place-items-center rounded-[9px] border border-white/10" style={{ background: "#0d0e11" }}>
      <svg width="17" height="17" viewBox="0 0 100 100" fill="none" aria-hidden>
        <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="89" cy="17" r="8" fill="#34d399" />
      </svg>
    </span>
  );
}

export function AuthQuotePanel({ reduce }: { reduce: boolean }) {
  return (
    <motion.section
      aria-hidden
      className="relative hidden min-w-0 flex-[1_1_55%] flex-col justify-between overflow-hidden border-l border-white/[0.06] p-[clamp(38px,3.4vw,56px)] min-[880px]:flex"
      style={{ gap: "clamp(22px,2.6vw,32px)", background: "linear-gradient(160deg, rgba(15,18,20,0.55), rgba(8,10,11,0.35))" }}
      variants={{ show: { transition: { staggerChildren: 0.06, delayChildren: 0.12 } } }}
      initial={reduce ? false : "hidden"}
      animate="show"
    >
      {/* ambient corner wash + oversized ghost mark */}
      <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(60% 50% at 82% 6%, rgba(52,211,153,0.10), transparent 60%)" }} />
      <div className="pointer-events-none absolute -bottom-12 -right-9 opacity-[0.05]">
        <svg viewBox="0 0 100 100" width="230" height="230" fill="none">
          <path d="M15 77 L30 29 L44 59 L55 34" stroke="#eaf1ee" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      {/* eyebrow row: workspace label + live market pill */}
      <motion.div variants={rise} className="relative z-[2] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <MiniMark />
          <span className="font-sans text-[10.5px] font-semibold uppercase leading-none tracking-[0.18em] text-dim">Maven · Workspace</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald/25 bg-emerald/[0.06] px-2.5 py-[5px]">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_8px_#34d399] motion-safe:animate-gate-spark" />
          <span className="font-sans text-[9.5px] font-semibold uppercase leading-none tracking-[0.12em] text-emerald/90">Live · NSE / BSE</span>
        </div>
      </motion.div>

      {/* the quote */}
      <motion.div variants={rise} className="relative z-[2]">
        <p className="m-0 font-serif text-[clamp(26px,2.9vw,38px)] font-normal leading-[1.2] tracking-[-0.005em] text-ink">
          Ask better questions.<br />
          <em className="font-serif italic motion-safe:animate-[gateShimmer_8s_linear_infinite]" style={{ background: "linear-gradient(100deg,#34d399,#7ce7bd,#10b981)", backgroundSize: "200% 100%", WebkitBackgroundClip: "text", backgroundClip: "text", WebkitTextFillColor: "transparent", color: "transparent" }}>
            Build better conviction.
          </em>
        </p>
        <p className="mt-3.5 max-w-[42ch] font-sans text-sm leading-[1.6] text-muted">
          Personalized market memory with Google sign-in — every chat and research thread saved to your account.
        </p>
      </motion.div>

      {/* the product film — /intro.mp4 playing inside a browser frame */}
      <motion.div
        variants={rise}
        whileHover={reduce ? undefined : { scale: 1.012 }}
        transition={{ duration: 0.35, ease: EASE }}
        className="relative z-[2] overflow-hidden rounded-2xl border border-white/[0.07]"
        style={{ background: "linear-gradient(160deg, rgba(13,16,18,0.94), rgba(9,11,13,0.94))", boxShadow: "0 30px 70px -40px rgba(0,0,0,0.9), 0 0 50px -22px rgba(52,211,153,0.3), inset 0 1px 0 rgba(255,255,255,0.03)" }}
      >
        <div className="flex items-center gap-1.5 border-b border-white/[0.05] px-3.5 py-2.5">
          <span className="h-2 w-2 rounded-full bg-[#38373a]" />
          <span className="h-2 w-2 rounded-full bg-[#2e2d30]" />
          <span className="h-2 w-2 rounded-full bg-[#252427]" />
          <span className="ml-2 font-sans text-[11px] font-medium text-dim">maven · see it work</span>
        </div>
        <GateFilm />
      </motion.div>

      {/* feature pills */}
      <motion.div variants={rise} className="relative z-[2] flex flex-wrap gap-2.5">
        <span className="inline-flex items-center gap-2 rounded-[11px] border border-white/[0.07] px-3 py-2 font-sans text-xs font-medium text-muted" style={{ background: "linear-gradient(180deg, rgba(20,23,26,0.6), rgba(12,14,16,0.6))" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M7 4h10a1 1 0 0 1 1 1v15l-6-3.3L6 20V5a1 1 0 0 1 1-1z" stroke="#34d399" strokeWidth="1.6" strokeLinejoin="round" /></svg>
          Saved chats
        </span>
        <span className="inline-flex items-center gap-2 rounded-[11px] border border-white/[0.07] px-3 py-2 font-sans text-xs font-medium text-muted" style={{ background: "linear-gradient(180deg, rgba(20,23,26,0.6), rgba(12,14,16,0.6))" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M5 20V12M12 20V5M19 20v-8" stroke="#34d399" strokeWidth="1.9" strokeLinecap="round" /></svg>
          Personal research
        </span>
        <span className="inline-flex items-center gap-2 rounded-[11px] border border-emerald/25 bg-emerald/[0.07] px-3 py-2 font-sans text-xs font-medium text-emerald/90">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><rect x="5" y="10.5" width="14" height="9.5" rx="2" stroke="#34d399" strokeWidth="1.5" /><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" stroke="#34d399" strokeWidth="1.5" strokeLinecap="round" /></svg>
          Google-secured
        </span>
      </motion.div>
    </motion.section>
  );
}
