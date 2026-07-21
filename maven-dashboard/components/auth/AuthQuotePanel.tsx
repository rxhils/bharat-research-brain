"use client";

// Right-hand visual panel of the Maven Google gate (desktop only). Pure
// presentation: the brand quote and ONE living artifact — the "Draft Study",
// a self-drawing index study inside a glass card (the page's only signature
// animation), a compact honest desk manifest beneath it (figures verbatim from
// app/backtest/page.tsx), and the product film demoted to a small quiet tile.
// Colors/fonts come from the app theme (emerald #34d399, --font-serif Fraunces).
//
// DraftStudy lives locally (not components/auth/DraftStudy.tsx) because this
// wave's file-ownership rules limit edits to this file; it consumes the shared
// PathDraw primitive, which is motion-value-driven and therefore plays under
// the OS reduced-motion flag (brand-motion signature surface).

import { motion, useMotionValue, useSpring, type Variants } from "framer-motion";
import { useEffect, useState, type PointerEvent } from "react";
import { EASE, EASE_SOFT, PathDraw } from "../motion";
import { GlassPanel } from "../glass-panel";
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

// ---------------------------------------------------------------------------
// The Draft Study — the page's single signature moment. An illustrative
// (clearly labeled) index-style line draws itself once via the shared PathDraw
// primitive; a gold annotation dot (gold use #1 of 2 on the page) and a mono
// callout settle in after the draw. Never loops, never replays.
// ---------------------------------------------------------------------------

const STUDY_D =
  "M8 118 L34 104 L58 112 L82 88 L106 96 L128 70 L150 92 L174 100 L198 78 L224 62 L252 70 L278 44 L306 34";
const STUDY_AREA = `${STUDY_D} L306 150 L8 150 Z`;

function DraftStudy() {
  return (
    <div className="brand-motion">
      <svg viewBox="0 0 320 150" className="block w-full" aria-hidden>
        {/* dim baseline beneath the study line */}
        <path d="M8 122 L306 96" stroke="rgba(255,255,255,0.10)" strokeWidth={1.5} fill="none" strokeDasharray="1 5" strokeLinecap="round" />
        <PathDraw
          d={STUDY_D}
          stroke="#34d399"
          strokeWidth={2}
          duration={1.8}
          delay={0.5}
          areaD={STUDY_AREA}
          areaFill="rgba(52,211,153,0.07)"
          dot={{ cx: 306, cy: 34, r: 4, fill: "#c9a961" }}
        />
        {/* mono callout, settles in after the draw completes */}
        <motion.g initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: 2.5, ease: EASE_SOFT }}>
          <text x={298} y={22} textAnchor="end" fontSize={9} letterSpacing="0.06em" fill="rgba(214,211,205,0.72)" style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}>
            drawdown study · F+ model
          </text>
        </motion.g>
      </svg>
      <p className="m-0 mt-2 font-mono text-[9.5px] tracking-[0.08em] text-dim">Illustrative research view — not live data</p>
    </div>
  );
}

/** One row of the desk manifest (mono, tabular numerals). */
function ManifestRow({ k, v, tone }: { k: string; v: string; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="font-mono text-[10.5px] tracking-[0.04em] text-dim">{k}</span>
      <span className={`tnum font-mono text-[10.5px] tracking-[0.02em] ${tone ?? "text-muted"}`}>{v}</span>
    </div>
  );
}

function clampDeg(v: number, limit: number) {
  return Math.max(-limit, Math.min(limit, v));
}

export function AuthQuotePanel({ reduce }: { reduce: boolean }) {
  // Pointer parallax on the artifact card: ≤2deg, spring-smoothed, desktop
  // pointer-fine only (zero on touch). Interaction-driven, so it is naturally
  // still when nobody is hovering.
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const srx = useSpring(rx, { stiffness: 150, damping: 20 });
  const sry = useSpring(ry, { stiffness: 150, damping: 20 });
  const [finePointer, setFinePointer] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFinePointer(mq.matches);
    const on = (e: MediaQueryListEvent) => setFinePointer(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const onCardPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!finePointer) return;
    const r = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const py = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    ry.set(clampDeg(px * 2, 2));
    rx.set(clampDeg(-py * 2, 2));
  };
  const onCardPointerLeave = () => {
    rx.set(0);
    ry.set(0);
  };

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
      <div className="pointer-events-none absolute -bottom-12 -right-9 opacity-[0.03]">
        <svg viewBox="0 0 100 100" width="230" height="230" fill="none">
          <path d="M15 77 L30 29 L44 59 L55 34" stroke="#eaf1ee" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      {/* eyebrow row: workspace label + live market pill (static dot, soft glow) */}
      <motion.div variants={rise} className="relative z-[2] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <MiniMark />
          <span className="font-mono text-[10px] font-semibold uppercase leading-none tracking-[0.18em] text-dim">Maven · Workspace</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald/25 bg-emerald/[0.06] px-2.5 py-[5px]">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_8px_#34d399]" />
          <span className="font-mono text-[9.5px] font-semibold uppercase leading-none tracking-[0.12em] text-emerald/90">Live · NSE / BSE</span>
        </div>
      </motion.div>

      {/* the quote — static emerald gradient, no shimmer loop */}
      <motion.div variants={rise} className="relative z-[2]">
        <p className="m-0 font-serif font-normal leading-[1.2] tracking-[-0.005em] text-ink" style={{ fontSize: "clamp(1.6rem, 1rem + 2vw, 2.4rem)" }}>
          Ask better questions.<br />
          <em className="font-serif italic" style={{ background: "linear-gradient(100deg,#34d399,#7ce7bd,#10b981)", WebkitBackgroundClip: "text", backgroundClip: "text", WebkitTextFillColor: "transparent", color: "transparent" }}>
            Build better conviction.
          </em>
        </p>
        <p className="mt-3.5 max-w-[42ch] font-sans text-sm leading-[1.6] text-muted">
          Personalized market memory with Google sign-in — every chat and research thread saved to your account.
        </p>
      </motion.div>

      {/* the artifact: Draft Study + desk manifest, on glass, glow BEHIND it */}
      <motion.div variants={rise} className="relative z-[2]" style={{ perspective: 1200 }}>
        {/* Vercel light-source trick: blurred emerald radial behind the card */}
        <div aria-hidden className="pointer-events-none absolute -inset-7 rounded-[32px]" style={{ background: "radial-gradient(60% 60% at 50% 38%, rgba(52,211,153,0.15), transparent 70%)", filter: "blur(26px)" }} />
        <motion.div style={{ rotateX: srx, rotateY: sry, transformStyle: "preserve-3d" }} onPointerMove={onCardPointerMove} onPointerLeave={onCardPointerLeave}>
          <GlassPanel glow="emerald" noise innerClassName="p-[18px]">
            <DraftStudy />
            {/* desk manifest — figures verbatim from the frozen backtest export
                shown on /backtest; simulation, clearly captioned as such */}
            <div className="mt-3 flex flex-col gap-1.5 border-t border-white/[0.06] pt-3">
              <ManifestRow k="Backtest 2021–26" v="+129.97% · index +82.17%" tone="text-emerald/90" />
              <ManifestRow k="Max drawdown" v="14.05% · index 18.59%" />
              <ManifestRow k="Mode" v="paper-traded · read-only" />
            </div>
            <p className="m-0 mt-2.5 font-sans text-[10px] leading-snug text-dim">Backtested simulation, not a live track record.</p>
          </GlassPanel>
        </motion.div>
      </motion.div>

      {/* the product film — demoted to a small quiet tile (no chrome, no hover) */}
      <motion.div variants={rise} className="relative z-[2] max-w-[300px]">
        <GateFilm className="rounded-xl border border-white/[0.06]" />
      </motion.div>
    </motion.section>
  );
}
