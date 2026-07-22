"use client";

// /broker journey — (1) the 4-step loop with a SCROLL-SCRUBBED tracing beam
// (progress + traveling glow head driven by one sprung MotionValue; each step's
// glyph ignites off the SAME value as the beam passes its x-position),
// (2) after-you-connect outcomes with a scroll-tracked layoutId pill beside a
// scroll-tilt-flattening iPhone mockup of the app's Broker screen (real logos),
// (3) trust band with a slow conic border beam + final CTA. Presentational only.

import Image from "next/image";
import { motion, useMotionValueEvent, useTransform, type MotionValue } from "framer-motion";
import { useRef, useState, type CSSProperties } from "react";
import { EASE, LayoutPill, PathDraw, useReducedMotionSafe, useScrollScrub } from "../motion";
import { MagneticCTA } from "./magnetic-cta";

const GRAD_GOLD: CSSProperties = {
  background: "linear-gradient(180deg,#e3cb8f,#c9a961 60%,#9c8348)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};

const STEPS = [
  { n: "01", t: "Market mode", d: "Regime, sectors, why a stock moved.", icon: "M3 17l5-6 4 4 6-8" },
  { n: "02", t: "Portfolio styles", d: "Disciplined model books to measure against.", icon: "M4 6h16M4 12h10M4 18h14" },
  { n: "03", t: "Connect read-only", d: "Log in on your broker's page — Maven never sees your password.", icon: "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5z" },
  { n: "04", t: "Your holdings, graded", d: "Today's P&L, results due, concentration — computed from YOUR positions.", icon: "M9 12l2 2 4-5M12 3l7 3v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V6l7-3z" },
];

// Ignition thresholds: where each step's glyph sits along the beam's travel
// (beam head sweeps 4%→96%; glyphs are left-aligned in 4 equal columns).
const STEP_T = [0.05, 0.3, 0.56, 0.83];

const OUTCOMES = [
  { t: "Holdings imported", d: "Symbol, quantity, average buy price — pulled once you approve, refreshed on reconnect.", icon: "M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" },
  { t: "Encrypted at rest", d: "Access tokens are AES-encrypted against your Maven account. Your broker password never touches Maven.", icon: "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5z" },
  { t: "Portfolio mode unlocked", d: "Ask AI switches from generic market context to answers grounded in your actual stocks.", icon: "M12 3l1.9 5.6L20 10l-6.1 1.4L12 17l-1.9-5.6L4 10l6.1-1.4L12 3z" },
];

function Glyph({ d, emerald = false }: { d: string; emerald?: boolean }) {
  return (
    <span className={"grid h-10 w-10 shrink-0 place-items-center rounded-xl border " + (emerald ? "border-emerald/35 bg-emerald/[0.08]" : "border-hairline bg-white/[0.03]")}>
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke={emerald ? "#34d399" : "#9aa1a9"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d={d} />
      </svg>
    </span>
  );
}

// One journey step: reveal is the usual whileInView fade; the emerald ignition
// ring is driven off the SAME beam MotionValue as the tracing line (never a
// parallel formula), so glyph and beam can never desync.
function StepItem({ s, i, beam, reduce }: {
  s: (typeof STEPS)[number]; i: number; beam: MotionValue<number>; reduce: boolean;
}) {
  const last = i === STEPS.length - 1;
  const ignite = useTransform(beam, [Math.max(0, STEP_T[i] - 0.08), STEP_T[i]], [0, 1]);
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.5, delay: reduce ? 0 : i * 0.12, ease: EASE }}
      className="relative"
    >
      <span className="relative inline-block">
        <Glyph d={s.icon} emerald={last} />
        <motion.span
          aria-hidden
          className="brand-motion pointer-events-none absolute inset-0 rounded-xl border border-emerald/50 bg-emerald/[0.07] shadow-[0_0_18px_-6px_rgba(52,211,153,0.6)]"
          style={{ opacity: ignite }}
        />
      </span>
      <div className="mt-3 font-mono text-[10px] uppercase tracking-[0.2em] text-dim">Step {s.n}</div>
      <div className={"mt-1 text-[0.95rem] font-semibold " + (last ? "text-emerald" : "text-ink")}>{s.t}</div>
      <p className="mt-1 text-xs leading-relaxed text-muted">{s.d}</p>
    </motion.div>
  );
}

// Real app screenshot in a scroll-tilt frame (homepage HeroDeviceTilt pattern):
// starts leaned back 22°, flattens as it scrolls into view, then hands off to
// the idle floatY. Motion-value-driven (.brand-motion) — plays under OS RM.
function PhoneMockup({ reduce }: { reduce: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useScrollScrub(ref, ["start end", "end start"]);
  const rotateX = useTransform(progress, [0, 0.45], [22, 0]);
  const scale = useTransform(progress, [0, 0.45], [0.92, 1]);
  return (
    <div ref={ref} className="relative mx-auto w-[280px] sm:w-[300px]" style={{ perspective: 1200 }} aria-hidden>
      {/* split glow: emerald + gold, the app's two accents */}
      <div className="absolute -inset-10 rounded-full" style={{ background: "radial-gradient(60% 55% at 30% 40%, rgba(52,211,153,0.16), transparent 70%), radial-gradient(50% 45% at 75% 70%, rgba(201,169,97,0.12), transparent 70%)", filter: "blur(10px)" }} />
      <motion.div className="brand-motion" style={{ rotateX, scale, transformStyle: "preserve-3d" }}>
        <motion.div
          className={reduce ? "relative" : "brand-motion relative animate-floatY"}
          initial={reduce ? false : { opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10% 0px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          {/* frame around the ACTUAL app screenshot (it carries its own status
              bar + Dynamic Island, so the frame stays minimal) */}
          <div className="rounded-[3rem] border border-white/12 bg-[#101216] p-2.5 shadow-[0_50px_120px_-40px_rgba(0,0,0,0.95),inset_0_1px_0_rgba(255,255,255,0.08)]">
            <div className="relative overflow-hidden rounded-[2.5rem]">
              <Image
                src="/app/broker-screen.png"
                alt="The Maven app's Broker screen — connect HDFC Sky or Zerodha read-only"
                width={1320}
                height={2868}
                unoptimized
                className="block h-auto w-full"
                priority={false}
              />
              {/* faint inner edge so the screen sits into the frame */}
              <div className="pointer-events-none absolute inset-0 rounded-[2.5rem] ring-1 ring-inset ring-white/5" />
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

export function BrokerJourney() {
  const reduce = useReducedMotionSafe();

  // Tracing beam: one sprung scroll progress drives the line's pathLength,
  // the traveling glow head, AND every glyph ignition. Scrub is motion-value
  // driven, so it works under OS reduced-motion.
  const stepsRef = useRef<HTMLDivElement>(null);
  const beam = useScrollScrub(stepsRef, ["start 0.9", "start 0.3"]);
  const headLeft = useTransform(beam, (v) => `${4 + v * 92}%`);
  const headOpacity = useTransform(beam, [0, 0.04, 0.96, 1], [0, 1, 1, 0]);

  // Outcomes: active row tracked off a section scrub → layoutId pill glides
  // between rows as they cross the reading line.
  const outcomesRef = useRef<HTMLDivElement>(null);
  const outScrub = useScrollScrub(outcomesRef, ["start 0.75", "end 0.45"]);
  const [activeOutcome, setActiveOutcome] = useState(0);
  useMotionValueEvent(outScrub, "change", (v) => {
    setActiveOutcome(Math.max(0, Math.min(OUTCOMES.length - 1, Math.floor(v * OUTCOMES.length))));
  });

  return (
    <div className="space-y-20 sm:space-y-28">
      {/* ------------------------------------------------ the loop */}
      <section>
        <motion.div initial={reduce ? false : { opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-8% 0px" }} transition={{ duration: 0.6, ease: EASE }}>
          {/* the emerald thread continues from the grid */}
          <svg width="2" height="32" viewBox="0 0 2 32" className="mb-4 overflow-visible" aria-hidden>
            <PathDraw d="M1 0 V32" stroke="rgba(52,211,153,0.5)" strokeWidth={2} duration={0.7} />
          </svg>
          <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-gold-soft">
            <span className="h-px w-9 bg-gold-soft/40" />
            How it pays off
          </div>
          <h2 className="mt-3 font-serif text-[clamp(1.75rem,1.2rem+2.4vw,2.9rem)] leading-tight text-ink">
            From market research <em className="italic text-emerald">to your portfolio.</em>
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">Four steps from reading the market to grading what you actually hold.</p>
        </motion.div>

        <div ref={stepsRef} className="relative mt-10">
          {/* scroll-scrubbed tracing beam behind the steps (desktop) */}
          <svg className="brand-motion absolute left-0 right-0 top-5 hidden h-px w-full lg:block" preserveAspectRatio="none" viewBox="0 0 100 1" aria-hidden>
            <motion.line
              x1="4" y1="0.5" x2="96" y2="0.5"
              stroke="rgba(52,211,153,0.4)" strokeWidth="1" vectorEffect="non-scaling-stroke"
              style={{ pathLength: beam }}
            />
          </svg>
          {/* the beam's traveling glow head (HTML so it never distorts under
              the svg's non-uniform scaling) */}
          <motion.div
            aria-hidden
            className="brand-motion pointer-events-none absolute top-5 hidden h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-emerald shadow-[0_0_10px_2px_rgba(52,211,153,0.5)] lg:block"
            style={{ left: headLeft, opacity: headOpacity }}
          />
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
            {STEPS.map((s, i) => (
              <StepItem key={s.n} s={s} i={i} beam={beam} reduce={reduce} />
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------ after you connect + phone */}
      <section className="grid items-center gap-12 lg:grid-cols-2">
        <div>
          <motion.div initial={reduce ? false : { opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-8% 0px" }} transition={{ duration: 0.6, ease: EASE }}>
            <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-gold-soft">
              <span className="h-px w-9 bg-gold-soft/40" />
              After you connect
            </div>
            <h2 className="mt-3 font-serif text-[clamp(1.75rem,1.2rem+2.4vw,2.9rem)] leading-tight text-ink">
              Three quiet things happen <em className="italic" style={GRAD_GOLD}>the moment you link.</em>
            </h2>
          </motion.div>
          <div ref={outcomesRef} className="mt-8 space-y-6">
            {OUTCOMES.map((o, i) => (
              <motion.div
                key={o.t}
                className="relative flex items-start gap-4 pl-4"
                initial={reduce ? false : { opacity: 0, x: -14 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-10% 0px" }}
                transition={{ duration: 0.5, delay: reduce ? 0 : i * 0.1, ease: EASE }}
              >
                {activeOutcome === i && (
                  <LayoutPill
                    layoutId="broker-outcome"
                    className="absolute left-0 top-1 h-8 w-[3px] rounded-full bg-emerald shadow-[0_0_12px_rgba(52,211,153,0.55)]"
                  />
                )}
                <Glyph d={o.icon} emerald={i === 2} />
                <div>
                  <div className="text-[0.95rem] font-semibold text-ink">{o.t}</div>
                  <p className="mt-1 max-w-sm text-xs leading-relaxed text-muted">{o.d}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
        <div>
          <PhoneMockup reduce={reduce} />
          <p className="mt-5 text-center text-xs text-dim">Connecting happens in the Maven app.</p>
        </div>
      </section>

      {/* ------------------------------------------------ trust + CTA */}
      <section>
        <motion.div
          className="border-beam relative overflow-hidden rounded-3xl border border-emerald/15 bg-emerald/[0.04] px-6 py-10 sm:px-12 sm:py-14"
          initial={reduce ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-8% 0px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          <svg className="pointer-events-none absolute -right-8 -top-10 opacity-[0.05]" width="260" height="260" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="1" aria-hidden>
            <path d="M12 3l7 3v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V6l7-3z" />
            <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <h2 className="max-w-2xl font-serif text-[clamp(1.5rem,1.1rem+1.6vw,2.1rem)] leading-snug text-ink">
            Read-only. Maven can see your holdings — <em className="italic text-emerald">never trade or move funds.</em>
          </h2>
          <div className="mt-5 space-y-1.5 text-sm text-muted">
            <p>Your broker password is typed on your broker&rsquo;s page — never ours.</p>
            <p className="text-xs text-dim">SEBI mandates daily token expiry — reconnecting is one tap in the app.</p>
          </div>
          <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.16em] text-dim">
            Tokens AES-encrypted · SEBI-mandated daily expiry
          </p>
        </motion.div>

        <motion.div
          className="mt-16 text-center"
          initial={reduce ? false : { opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-8% 0px" }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          <h2 className="font-serif text-[clamp(1.75rem,1.2rem+2.4vw,2.9rem)] leading-tight text-ink">
            Ask Maven about <em className="italic text-emerald">your</em> portfolio.
          </h2>
          <MagneticCTA
            href="/login"
            className="mt-6 inline-flex min-h-[46px] items-center gap-2 rounded-xl bg-gradient-to-br from-emerald to-emerald-deep px-7 text-sm font-semibold text-bg shadow-[0_14px_36px_-12px_rgba(52,211,153,0.8)] transition-opacity duration-150 hover:opacity-90"
          >
            Continue with Google
          </MagneticCTA>
          <p className="mt-5 text-xs text-dim">Research tool. Not investment advice. Paper-traded results, not real money.</p>
        </motion.div>
      </section>
    </div>
  );
}
