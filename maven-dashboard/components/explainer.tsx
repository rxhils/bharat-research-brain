"use client";

/**
 * "How it works" — the honest explainer, native to the Maven dashboard.
 *
 * Built with the dashboard's own tokens (bg/panel/border/emerald) + a muted
 * gold + an editorial serif for headlines. Framer Motion for scroll reveals,
 * count-ups, and the page's single signature moment — "The Fall, Scrubbed", a
 * sticky scroll-scrubbed covid drawdown proof (no WebGL bundle in the research
 * app). The hero leads with the real product mock in a scroll-flattening tilt.
 * prefers-reduced-motion is respected throughout; scroll-scrubbed signatures
 * are motion-value-driven inside .brand-motion so they still play under the
 * OS flag (they are user-driven, not autonomous).
 *
 * HONESTY CONTRACT: edge = risk (Enhanced F+ beats Nifty 500 +129.97% vs
 * +82.17% 2021-26 at lower drawdown 14.05% vs 18.59%; covid -13.88% vs market
 * ~-38%). Every figure is backtested, not a live track record; universe is
 * current constituents (survivorship → absolute returns optimistic). Broker is
 * read-only. No proprietary thresholds anywhere.
 */

import {
  animate,
  motion,
  useInView,
  useMotionValue,
  useMotionValueEvent,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
  type Variants,
} from "framer-motion";
import { useEffect, useId, useRef, useState, type PointerEvent, type ReactNode, type RefObject } from "react";
import { CountUp, EASE, MagneticButton, useReducedMotionSafe, useScrollScrub } from "./motion";
import { GlassPanel } from "./glass-panel";
import { ScrollProgress } from "./scroll-progress";

// ───────────────────────────── content ─────────────────────────────

const LAYERS = [
  {
    n: 1,
    name: "Market Mode",
    nav: "Ask AI",
    oneLine: "What is the Indian market saying?",
    mental: "Market Mode = what's happening?",
    summary:
      "The market-intelligence layer. It reads trend, regime, sector leadership, breadth, filings and earnings — and flags rising risk or opportunity before any portfolio acts. Context, not execution.",
    screenshot: "market-mode.png",
    chips: null as string[] | null,
    chipLabel: "",
    note: "",
    illustrative: false,
    gallery: [] as { file: string; cap: string }[],
  },
  {
    n: 2,
    name: "Portfolio Mode",
    nav: "Portfolios",
    oneLine: "What should my portfolio do about it?",
    mental: "Portfolio Mode = what to do about it?",
    summary:
      "Turns market intelligence into portfolio action — holdings, weights, cash level, rebalance decisions, risk control — all driven by the same validated Enhanced F+ engine. Each style is the same engine with a different tilt, not a separate product.",
    screenshot: "portfolio-mode.png",
    chips: ["Core", "Quality", "Growth", "Momentum", "Income", "Quant", "Value", "Contrarian"],
    chipLabel: "Eight styles, one engine",
    note: "Every style runs the same engine. The proven edge is lower drawdown — not guaranteed alpha. Any α shown is illustrative.",
    illustrative: true,
    gallery: [
      { file: "portfolios-stable.png", cap: "Stable" },
      { file: "portfolios-bold.png", cap: "Bold" },
    ],
  },
  {
    n: 3,
    name: "Watchlist",
    nav: "Watchlist",
    oneLine: "Track what matters, personally.",
    mental: "Watchlist = your live layer between curiosity and conviction.",
    summary:
      "Watchlist is your personal tracking layer — the names you're studying before you commit. Save the stocks you care about, watch how they move, see where they overlap with MAVEN portfolios, and follow their signals without committing to a portfolio yet. Some may be future holdings, some you already hold at your broker, some you just want to follow closely — MAVEN keeps the list alive with movement, overlap, and what changed today.",
    screenshot: "watchlist.png",
    chips: ["Saved names", "Price moves", "Portfolio overlap", "Alerts", "Earnings", "Signals"],
    chipLabel: "Tracks",
    note: "Watchlist data is for tracking and research — it helps you follow names more closely before acting.",
    illustrative: false,
    gallery: [] as { file: string; cap: string }[],
  },
  {
    n: 4,
    name: "Broker",
    nav: "Broker",
    oneLine: "Where insight becomes action.",
    mental: "Broker = connect & sync (read-only).",
    summary:
      "Connects Maven to a real account — Zerodha, Groww, Upstox, Angel One, HDFC Sky, Anand Rathi — read-only, to sync and compare your holdings against the models. Execution is the last layer, and it stays human-approved.",
    screenshot: "broker-connect.png",
    chips: ["Zerodha", "Groww", "Upstox", "Angel One", "HDFC Sky", "Anand Rathi"],
    chipLabel: "Connects to",
    note: "Read-only. No trading. Maven never places, modifies, or cancels an order.",
    illustrative: false,
    gallery: [
      { file: "broker-list.png", cap: "Brokers" },
      { file: "broker-hdfc.png", cap: "Sign-in" },
    ],
  },
];

const PRINCIPLES = [
  { k: "regime", t: "Reads the regime", b: "It knows the difference between a healthy market and a falling one, and treats them differently. Context before conviction." },
  { k: "quality", t: "Holds quality, diversified", b: "Durable businesses, spread across names and sectors. Never the whole book on a single bet or a single story." },
  { k: "cash", t: "Moves to cash when it matters", b: "When risk rises, it raises cash. That single discipline is what halved the drawdown when the market broke." },
];

const TIMELINE = [
  { t: "Two market eras", b: "Tested across distinct regimes — including the covid crash — not a single lucky stretch." },
  { t: "Pre-registered targets", b: "Success criteria were written down before the test, so a good result couldn't be invented after the fact." },
  { t: "No look-ahead", b: "Decisions used only the data available on that day. No future knowledge leaked backwards." },
  { t: "Many tried, one passed", b: "A long list of approaches was built and rejected. Enhanced F+ is the one that survived the discipline." },
];

const REJECTED = [
  { n: "Pure momentum chase", w: "Great in trends, brutal in reversals. Drawdown failed the test." },
  { n: "Single-factor value", w: "Cheap stayed cheap too long. Didn't beat buy-and-hold risk-adjusted." },
  { n: "All-in conviction", w: "Concentrated bets spiked volatility past the pre-registered ceiling." },
  { n: "Always-invested", w: "No cash discipline meant it crashed with the market. Rejected." },
];

// ───────────────────────────── primitives ─────────────────────────────

export const GRAD_GOLD: React.CSSProperties = {
  backgroundImage: "linear-gradient(180deg,#e3cb8f 0%,#c9a961 60%,#9c8348 100%)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};
export const GRAD_EMERALD: React.CSSProperties = {
  backgroundImage: "linear-gradient(180deg,#6ee7b7 0%,#34d399 100%)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};

export function Reveal({ children, delay = 0, y = 22, className = "" }: { children: ReactNode; delay?: number; y?: number; className?: string }) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px -12% 0px" }}
      transition={{ duration: 0.75, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

function RevealGroup({ children, className = "" }: { children: ReactNode; className?: string }) {
  // Reduced-motion branch mirrors Reveal/Item: children still fade in, but with
  // no sequential delay — a stagger reads as motion even on opacity-only items.
  const reduce = useReducedMotionSafe();
  const stagger: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.1, delayChildren: reduce ? 0 : 0.04 } },
  };
  return (
    <motion.div className={className} variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-10% 0px" }}>
      {children}
    </motion.div>
  );
}
function Item({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotionSafe();
  const v: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
  };
  return <motion.div className={className} variants={v}>{children}</motion.div>;
}

/** Variants child that reveals with a top→bottom clip-path wipe; opacity-only
 *  under reduced motion. Use inside a staggered variants group. */
function ClipItem({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotionSafe();
  const v: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, clipPath: "inset(0 0 100% 0)" },
    show: { opacity: 1, clipPath: "inset(0 0 0% 0)", transition: { duration: 0.7, ease: EASE } },
  };
  return <motion.div className={className} variants={v}>{children}</motion.div>;
}

/** Decorative pointer tilt (±4° through springs) — mouse only, gated behind
 *  useReducedMotionSafe. Sits OUTSIDE any clip-path wrapper so the rotation
 *  never gets cut by an ancestor clip box. */
function TiltCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotionSafe();
  const ref = useRef<HTMLDivElement>(null);
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const srx = useSpring(rx, { stiffness: 260, damping: 20 });
  const sry = useSpring(ry, { stiffness: 260, damping: 20 });
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (reduce || e.pointerType !== "mouse" || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    ry.set(((e.clientX - r.left) / r.width - 0.5) * 8);
    rx.set(-((e.clientY - r.top) / r.height - 0.5) * 8);
  };
  const onLeave = () => {
    rx.set(0);
    ry.set(0);
  };
  return (
    <motion.div
      ref={ref}
      className={className}
      style={{ rotateX: srx, rotateY: sry, transformPerspective: 800, transformStyle: "preserve-3d" }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      {children}
    </motion.div>
  );
}

function Eyebrow({ index, children }: { index: string; children: string }) {
  return (
    <Reveal>
      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-gold/70">{index}</span>
        <span className="h-px w-8 bg-gold/30" />
        <span className="font-sans text-[0.7rem] font-semibold uppercase tracking-label text-gold">{children}</span>
      </div>
    </Reveal>
  );
}

function LivePill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald/30 bg-emerald/10 px-3 py-1 text-xs font-medium text-emerald">
      {/* static dot + glow — three LivePills share this page, so a looping pulse
          on each reads as slop; the glow alone carries "live" (see agents.tsx) */}
      <span className="h-1.5 w-1.5 rounded-full bg-emerald shadow-[0_0_6px_rgba(52,211,153,0.55)]" />
      {children}
    </span>
  );
}

function IllustrativeTag() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-gold/25 bg-gold/[0.07] px-2.5 py-0.5 text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-gold-soft">
      <svg width="9" height="9" viewBox="0 0 10 10" fill="none" aria-hidden>
        <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1.2" />
        <path d="M5 4.4V7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <circle cx="5" cy="3" r="0.7" fill="currentColor" />
      </svg>
      Illustrative
    </span>
  );
}

// Live recreation of the Maven "Market Mode" app screen (image 4), rendered
// inside a device frame instead of a screenshot file.
function MarketModeScreen() {
  const rows = [
    { ic: "trend", t: "Why is Nifty up today?" },
    { ic: "bars", t: "Reliance Q4 — what changed" },
    { ic: "swap", t: "HDFC Bank vs Kotak" },
  ];
  return (
    <div
      className="absolute inset-0 flex flex-col px-3 pb-2 pt-7 text-left"
      style={{
        backgroundColor: "#08090b",
        backgroundImage: "radial-gradient(85% 38% at 50% 0%, rgba(52,211,153,0.12), transparent 62%)",
      }}
    >
      {/* header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-1.5">
          <svg width="17" height="17" viewBox="0 0 100 100" fill="none" aria-hidden>
            <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="89" cy="17" r="8" fill="#34d399" />
          </svg>
          <div className="leading-none">
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-gold">Maven</div>
            <div className="mt-1 flex items-center gap-1 text-[6px] text-muted">
              <span className="h-1 w-1 rounded-full bg-emerald" />Indian markets · live
            </div>
          </div>
        </div>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden className="text-gold">
          <path d="M3 12a9 9 0 1 0 2.5-6.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M3 4v4h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M12 8v4.5l3 1.8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </div>

      {/* headline */}
      <h4 className="mt-3 font-serif text-[17px] font-light leading-[1.06] text-ink">
        Good morning. What are the <span className="italic text-emerald">markets</span> telling you?
      </h4>
      <p className="mt-1.5 text-[7px] leading-relaxed text-muted">Grounded in NSE/BSE data, filings &amp; your portfolio.</p>

      {/* insight */}
      <p className="mt-2 text-[8px] leading-relaxed text-ink">
        <span className="text-emerald">✦</span> Banking is leading — HDFC Bank{" "}
        <span className="rounded bg-emerald/15 px-1 text-emerald">+2.4%</span>, and FIIs turned{" "}
        <span className="rounded bg-emerald/15 px-1 text-emerald">net buyers</span> today.
      </p>

      <div className="my-2 h-px bg-hairline" />

      {/* nifty pill */}
      <span className="inline-flex w-fit items-center gap-1 rounded-full border border-emerald/30 px-2 py-0.5 text-[8px]">
        <svg width="10" height="6" viewBox="0 0 16 10" aria-hidden>
          <path d="M1 8 L5 4 L8 6 L15 1" stroke="#34d399" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-muted">NIFTY</span> <span className="font-semibold text-ink">23,140</span>{" "}
        <span className="text-emerald">▲ 0.8%</span>
      </span>

      {/* suggestion rows */}
      <div className="mt-2 divide-y divide-hairline">
        {rows.map((r) => (
          <div key={r.t} className="flex items-center justify-between py-[7px]">
            <div className="flex items-center gap-2">
              <RowIcon kind={r.ic} />
              <span className="font-serif text-[11px] text-ink">{r.t}</span>
            </div>
            <span className="text-[10px] text-gold/80">›</span>
          </div>
        ))}
      </div>

      <div className="flex-1" />

      {/* ask bar */}
      <div className="rounded-xl border border-gold/25 p-1.5">
        <p className="px-1 pb-1.5 pt-0.5 font-serif text-[9px] italic text-muted">Ask Maven…</p>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1 rounded-full border border-emerald/30 bg-emerald/5 px-1.5 py-[3px] text-[6px] font-bold tracking-wide text-emerald">
            <span className="h-1 w-1 rounded-full bg-emerald" />MARKET <span className="text-[5px]">▲</span>
          </span>
          <div className="flex items-center gap-1.5 text-muted">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" aria-hidden><path d="M21 11l-9 9a5 5 0 01-7-7l9-9a3.5 3.5 0 015 5l-9 9a2 2 0 01-3-3l8-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" aria-hidden><rect x="9" y="2" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="2" /><path d="M5 11a7 7 0 0014 0M12 18v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
            <span className="grid h-4 w-4 place-items-center rounded-full bg-emerald">
              <svg width="7" height="7" viewBox="0 0 24 24" fill="none" aria-hidden><path d="M12 19V5M5 12l7-7 7 7" stroke="#08090b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </span>
          </div>
        </div>
      </div>

      {/* tab bar */}
      <div className="mt-1.5 flex items-center justify-around border-t border-hairline pt-1.5">
        {[
          { t: "Ask AI", a: true },
          { t: "Portfolios", a: false },
          { t: "Watchlist", a: false },
          { t: "Broker", a: false },
        ].map((tb) => (
          <div key={tb.t} className={`flex flex-col items-center gap-0.5 text-[6px] ${tb.a ? "text-emerald" : "text-dim"}`}>
            <TabIcon name={tb.t} active={tb.a} />
            {tb.t}
          </div>
        ))}
      </div>
    </div>
  );
}

function RowIcon({ kind }: { kind: string }) {
  const c = { width: 11, height: 11, viewBox: "0 0 24 24", fill: "none", stroke: "#c9a961", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (kind === "trend") return <svg {...c} aria-hidden><path d="M3 17l6-6 4 4 8-8" /><path d="M21 7v4h-4" /></svg>;
  if (kind === "bars") return <svg {...c} aria-hidden><path d="M5 21V10M12 21V4M19 21v-7" /></svg>;
  if (kind === "pie") return <svg {...c} aria-hidden><path d="M12 3a9 9 0 1 0 9 9h-9z" /><path d="M12 3v9" /></svg>;
  if (kind === "updown") return <svg {...c} aria-hidden><path d="M7 5v14M7 5L4 8M7 5l3 3M17 19V5M17 19l-3-3M17 19l3-3" /></svg>;
  if (kind === "doc") return <svg {...c} aria-hidden><path d="M6 2h8l4 4v16H6zM14 2v4h4M9 13h6M9 17h4" /></svg>;
  return <svg {...c} aria-hidden><path d="M7 4L4 7l3 3M4 7h13M17 20l3-3-3-3M20 17H7" /></svg>;
}

function TabIcon({ name, active }: { name: string; active: boolean }) {
  const col = active ? "#34d399" : "#5a616a";
  const c = { width: 13, height: 13, viewBox: "0 0 24 24", fill: "none", stroke: col, strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "Ask AI") return <svg {...c} aria-hidden><path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" /></svg>;
  if (name === "Portfolios") return <svg {...c} aria-hidden><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>;
  if (name === "Watchlist") return <svg {...c} aria-hidden><path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 18.7l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" /></svg>;
  return <svg {...c} aria-hidden><path d="M9 15l6-6M10 6l1-1a4 4 0 016 6l-1 1M14 18l-1 1a4 4 0 01-6-6l1-1" /></svg>;
}

// "Models, ranked." list screens (images 1-3): the Balanced variant is layer 2's
// full-size mock (visually distinct from layer 1's Ask screen); Stable/Bold sit
// in the small gallery frames.
type PCard = { letter: string; color: string; name: string; crown?: boolean; ret: string; alpha: string; holdings: number; risk: "High" | "Medium" };
const PF_DATA: Record<string, { section: string; sub: string; featured?: boolean; cards: PCard[] }> = {
  Stable: {
    section: "Stable", sub: "Lower drawdown, steadier", featured: true,
    cards: [
      { letter: "C", color: "#7aa2ff", name: "Core", crown: true, ret: "+14.6%", alpha: "+1.1%", holdings: 42, risk: "High" },
      { letter: "Q", color: "#c084fc", name: "Quality", ret: "+13.2%", alpha: "−0.3%", holdings: 25, risk: "High" },
    ],
  },
  Balanced: {
    section: "Balanced", sub: "Broad coverage, medium risk",
    cards: [
      { letter: "G", color: "#34d399", name: "Growth", crown: true, ret: "+23.5%", alpha: "+10.0%", holdings: 24, risk: "Medium" },
      { letter: "M", color: "#fb923c", name: "Momentum", ret: "+20.8%", alpha: "+7.3%", holdings: 18, risk: "Medium" },
      { letter: "I", color: "#c9a961", name: "Income", ret: "+15.3%", alpha: "+1.8%", holdings: 26, risk: "High" },
    ],
  },
  Bold: {
    section: "Bold", sub: "Higher turnover, higher risk/reward",
    cards: [
      { letter: "Q", color: "#34d399", name: "Quant", crown: true, ret: "+31.7%", alpha: "+18.2%", holdings: 12, risk: "Medium" },
      { letter: "V", color: "#facc15", name: "Value", ret: "+24.5%", alpha: "+11.0%", holdings: 16, risk: "Medium" },
      { letter: "C", color: "#fb7185", name: "Contrarian", ret: "+20.2%", alpha: "+6.7%", holdings: 14, risk: "Medium" },
    ],
  },
};

function Risk({ level }: { level: string }) {
  const on = level === "High";
  return <span className={`shrink-0 rounded-full px-1 py-[0.5px] text-[5px] font-semibold ${on ? "bg-emerald/15 text-emerald" : "border border-border text-muted"}`}>{level}</span>;
}

function PortfolioCard({ c, small = false }: { c: PCard; small?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-panel/50 p-1">
      <div className="flex items-center gap-1">
        <span className="grid h-3.5 w-3.5 place-items-center rounded text-[6px] font-bold" style={{ color: c.color, background: "rgba(255,255,255,0.05)" }}>{c.letter}</span>
        <span className="text-[7px] font-bold text-ink">{c.name}</span>
        {c.crown && <span className="text-[6px] text-gold">♛</span>}
      </div>
      <div className="mt-0.5 flex items-center justify-between">
        <span className="text-[11px] font-bold text-emerald">{c.ret}</span>
        <Risk level={c.risk} />
      </div>
      {/* Illustrative α/holdings line — dropped in the small gallery frames where
          5px type turns to noise; kept in the full-size mock. */}
      {!small && <div className="text-[5px] text-muted">α {c.alpha} vs NIFTY · {c.holdings} holdings</div>}
    </div>
  );
}

function FeaturedQuant() {
  return (
    <div className="relative grid place-items-center rounded-xl border border-emerald/20 py-2.5" style={{ backgroundImage: "radial-gradient(60% 60% at 50% 42%, rgba(52,211,153,0.20), transparent 70%)" }}>
      <span className="absolute right-1.5 top-1.5 rounded-full bg-emerald px-1 py-[1px] text-[5px] font-bold text-black">↗ +31.7%</span>
      <div className="grid h-8 w-8 place-items-center rounded-lg border border-emerald/30 bg-[#0d0e11]" style={{ boxShadow: "0 0 22px -4px rgba(52,211,153,0.55)" }}>
        <svg viewBox="0 0 80 60" className="h-5 w-5" fill="none" aria-hidden>
          <path d="M6 50 C26 50 30 14 40 14 C50 14 54 50 74 50" stroke="#e9ebed" strokeWidth="3" strokeLinecap="round" opacity="0.85" />
          <circle cx="40" cy="14" r="4" fill="#6ee7b7" />
        </svg>
      </div>
      <div className="mt-1 text-[5px] font-semibold uppercase tracking-wide text-emerald">● Featured</div>
      <div className="font-serif text-[12px] text-ink">Quant</div>
      <div className="text-[5px] text-muted">by Maven · Bold</div>
    </div>
  );
}

function PortfoliosScreen({ variant, small = false }: { variant: string; small?: boolean }) {
  const d = PF_DATA[variant];
  return (
    <div className="absolute inset-0 flex flex-col gap-1.5 overflow-hidden px-2 pb-4 pt-6" style={{ backgroundColor: "#08090b" }}>
      <div>
        <div className="flex items-center justify-between">
          <span className="text-[6px] font-bold uppercase tracking-[0.2em] text-gold">AI Portfolios</span>
          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" aria-hidden className="text-gold"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2.5" /><path d="M21 21l-4-4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
        </div>
        <h4 className="font-serif text-[14px] leading-tight text-ink">Models, ranked.</h4>
        <div className="mt-0.5 flex items-center gap-1 text-[5px] text-muted"><span className="h-[3px] w-[3px] rounded-full bg-emerald" />NSE/BSE · live</div>
      </div>
      {d.featured && <FeaturedQuant />}
      <div>
        <h5 className="font-serif text-[11px] text-ink">{d.section}</h5>
        <p className="text-[5px] text-muted">{d.sub}</p>
      </div>
      <div className="flex flex-col gap-1">
        {d.cards.map((c) => <PortfolioCard key={c.name} c={c} small={small} />)}
      </div>
    </div>
  );
}

// Live recreation of the "Watchlist" personal-tracking screen (image 2).
type Watch = { sym: string; name: string; price: string; chg: string };
const WATCH: Watch[] = [
  { sym: "LTTS", name: "L&T Technology Services Ltd.", price: "₹3,351", chg: "+1.82%" },
  { sym: "ANANTRAJ", name: "Anant Raj Ltd.", price: "₹535", chg: "+4.19%" },
];

// Portfolio strategies — the plain-English engine behind each MAVEN book, by tier.
type Strat = { name: string; tag: string; oneLine: string; how: string; looks: string; bestFor: string; signature?: boolean };
const STRAT_TIERS: { tier: string; items: Strat[] }[] = [
  { tier: "Stable", items: [
    { name: "Core", tag: "Foundation", oneLine: "Your long-term base portfolio.",
      how: "The foundation basket — broad market exposure through a steadier, benchmark-aware approach rather than one extreme style bet.",
      looks: "Starts from a broad universe and aims for balance, durability, and cleaner overall exposure.",
      bestFor: "A main long-term portfolio to build around." },
    { name: "Quality", tag: "Durable", oneLine: "Strong businesses, chosen for durability.",
      how: "Favours companies with healthier business strength, better returns on capital, and cleaner balance sheets.",
      looks: "Stronger fundamentals and steadier quality signals over weak businesses that only look cheap or exciting.",
      bestFor: "Steadier compounding through stronger companies." },
    { name: "Defensive", tag: "Defensive", oneLine: "Built to fall less in bad markets.",
      how: "Designed to hold up better when markets are weak, uncertain, or volatile — resilience over excitement.",
      looks: "Steadier businesses, lower downside risk, and more stable behaviour through rougher periods.",
      bestFor: "A calmer profile and smaller drawdowns." },
  ] },
  { tier: "Balanced", items: [
    { name: "Growth", tag: "Aggressive", oneLine: "Higher upside, higher volatility.",
      how: "Backs companies with real expansion potential — where revenue, earnings, or opportunity may still be compounding faster than the market.",
      looks: "Leans into faster growers and accepts more volatility in exchange for stronger upside.",
      bestFor: "More return potential, if you can handle bigger swings." },
    { name: "Momentum", tag: "Trend", oneLine: "Buy what is already strong.",
      how: "Follows market leadership — it aims to own names already showing real price strength and trend persistence.",
      looks: "Ranks stocks by strength and favours the ones already moving well; fading trends fall out.",
      bestFor: "Trend-following over turnaround investing." },
    { name: "Income", tag: "Yield", oneLine: "Built to generate cash flow.",
      how: "Focuses on businesses that may offer healthier, more dependable payouts and better cash generation.",
      looks: "Sustainable dividend and cash-return profiles rather than simply chasing the highest yield.",
      bestFor: "Steadier cash flow and a more income-oriented style." },
  ] },
  { tier: "Bold", items: [
    { name: "Quant", tag: "Signature Model", signature: true, oneLine: "MAVEN's signature rules-based model.",
      how: "Powered by the enhanced F+ model — the most systematic book in MAVEN, built on defined signals, ranking logic, and disciplined selection rules.",
      looks: "Instead of picking by feel, it scores names through the enhanced F+ framework and selects the stocks that fit the model best.",
      bestFor: "MAVEN's strongest model-driven strategy." },
    { name: "Value", tag: "Mispriced", oneLine: "Buy undervalued stocks.",
      how: "Looks for companies priced below what their business fundamentals seem to justify.",
      looks: "Stocks that look cheap against earnings, cash flow, or quality — while avoiding the obvious traps.",
      bestFor: "Buying mispriced businesses over chasing hot trends." },
    { name: "Contrarian", tag: "Re-rating", oneLine: "Back quality when sentiment gets too weak.",
      how: "Looks for situations where the market may be overreacting, but the underlying business still has enough quality to justify attention.",
      looks: "Names where sentiment or price has weakened, but the business still supports a possible recovery or re-rating.",
      bestFor: "Selective recovery opportunities rather than pure momentum." },
  ] },
];

function WatchlistScreen() {
  return (
    <div className="absolute inset-0 flex flex-col gap-2 overflow-hidden px-2.5 pb-4 pt-6" style={{ backgroundColor: "#08090b" }}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[7px] font-bold uppercase tracking-[0.2em] text-gold">Watchlist</div>
          <h4 className="mt-0.5 font-serif text-[15px] leading-none text-ink">Names you track.</h4>
          <div className="mt-1 text-[5px] text-muted">Signals that matter — saved to this device.</div>
        </div>
        <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full border border-gold/40 text-[8px] leading-none text-gold-soft">+</span>
      </div>

      <div className="flex items-baseline justify-between">
        <span className="text-[10px] font-bold text-ink">2 tracked</span>
        <span className="text-[5px] text-muted">2 up · 0 down today</span>
      </div>

      <div className="flex flex-col gap-1.5">
        {WATCH.map((w) => (
          <div key={w.sym} className="rounded-lg border border-border bg-panel/50 p-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-bold text-ink">{w.sym}</span>
              <span className="text-[8px] font-semibold text-ink">{w.price}</span>
            </div>
            <div className="mt-0.5 flex items-center justify-between gap-1">
              <span className="truncate text-[5px] text-muted">{w.name}</span>
              <span className="shrink-0 text-[6px] font-semibold text-emerald">{w.chg}</span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-[5px] leading-relaxed text-dim">Last close from NSE/BSE end-of-day data — live prices resume when the market opens. Overlap shows smart-money portfolios that hold the name.</p>

      <div className="mt-auto flex items-center justify-around border-t border-hairline pt-1.5">
        {[{ t: "Ask AI", a: false }, { t: "Portfolios", a: false }, { t: "Watchlist", a: true }, { t: "Broker", a: false }].map((tb) => (
          <div key={tb.t} className={`flex flex-col items-center gap-0.5 text-[6px] ${tb.a ? "text-emerald" : "text-dim"}`}>
            <TabIcon name={tb.t} active={tb.a} />{tb.t}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Broker screens (images 4 / 3 / 5) ──
function MiniMark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" aria-hidden>
      <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="89" cy="17" r="8" fill="#34d399" />
    </svg>
  );
}
function BrokerHeader() {
  return (
    <div>
      <h4 className="font-serif text-[17px] font-light leading-none text-ink">Connect your broker</h4>
      <p className="mt-1 text-[6px] text-muted">Securely linked. Read-only, no trading.</p>
    </div>
  );
}
function BrokerTabBar() {
  return (
    <div className="flex items-center justify-around border-t border-hairline pt-1.5">
      {[{ t: "Ask AI", a: false }, { t: "Portfolios", a: false }, { t: "Watchlist", a: false }, { t: "Broker", a: true }].map((tb) => (
        <div key={tb.t} className={`flex flex-col items-center gap-0.5 text-[6px] ${tb.a ? "text-emerald" : "text-dim"}`}><TabIcon name={tb.t} active={tb.a} />{tb.t}</div>
      ))}
    </div>
  );
}
type Brk = { name: string; sub: string; color: string; connected?: boolean; synced?: string; status?: string };
function BrokerRow({ b }: { b: Brk }) {
  return (
    <div className="rounded-md border border-border bg-panel/50 p-1.5">
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[10px] font-bold text-white" style={{ backgroundColor: b.color }}>{b.name[0]}</span>
        <div className="min-w-0 flex-1">
          <div className="text-[9px] font-bold text-ink">{b.name}</div>
          <div className="truncate text-[6px] text-muted">{b.sub}</div>
          {b.synced && <div className="text-[5.5px] text-muted">{b.synced}</div>}
        </div>
        {b.connected
          ? <span className="shrink-0 rounded border border-border px-2 py-0.5 text-[7px] font-bold text-ink">Disconnect</span>
          : <span className="shrink-0 rounded bg-emerald px-3 py-1 text-[7px] font-bold text-black">Connect</span>}
      </div>
      {b.status && <div className="mt-1.5 border-t border-hairline pt-1 text-[5.5px] text-muted"><span className="text-emerald">●</span> {b.status}</div>}
    </div>
  );
}

function BrokerConnectScreen() {
  return (
    <div className="absolute inset-0 flex flex-col gap-2 overflow-hidden px-3 pb-4 pt-7" style={{ backgroundColor: "#08090b" }}>
      <BrokerHeader />
      <div className="text-[6px] font-bold uppercase tracking-[0.2em] text-dim">Account</div>
      <div className="rounded-xl border border-border bg-panel/60 p-2.5">
        <div className="flex items-center gap-2">
          <MiniMark size={22} />
          <div className="min-w-0">
            <div className="font-serif text-[12px] leading-none text-ink">Make Maven yours</div>
            <div className="mt-1 text-[6.5px] leading-snug text-muted">Brokers &amp; preferences — private to you.</div>
          </div>
        </div>
        <div className="mt-2.5 rounded-md bg-emerald py-1.5 text-center text-[10px] font-bold text-black">Log in / Sign up</div>
        <div className="mt-1.5 flex items-center justify-center gap-1.5 rounded-md bg-white py-1.5 text-[10px] font-bold text-[#1f1f1f]"><span style={{ color: "#4285F4" }}>G</span> Continue with Google</div>
        <p className="mt-2 text-center text-[6px] text-dim">No account needed — Market Mode works without one.</p>
      </div>
      <div className="text-[6px] font-bold uppercase tracking-[0.2em] text-dim">Appearance</div>
      <div className="flex rounded-md border border-border bg-panel/50 p-0.5 text-[8px]">
        <div className="flex-1 rounded bg-panel2 py-1 text-center font-semibold text-ink">System</div>
        <div className="flex-1 py-1 text-center text-muted">Light</div>
        <div className="flex-1 py-1 text-center text-muted">Dark</div>
      </div>
      <div className="text-[6px] font-bold uppercase tracking-[0.2em] text-dim">Brokers</div>
      <BrokerRow b={{ name: "Zerodha", sub: "Connect via Zerodha Kite", color: "#ef4444", connected: true }} />
      <BrokerRow b={{ name: "Groww", sub: "Connect your Groww account", color: "#00b386" }} />
      <div className="mt-auto"><BrokerTabBar /></div>
    </div>
  );
}

function BrokerListScreen() {
  const brokers: Brk[] = [
    { name: "Zerodha", sub: "Connect via Zerodha Kite", color: "#ef4444", connected: true },
    { name: "Groww", sub: "Connect your Groww account", color: "#00b386" },
    { name: "Upstox", sub: "Connect via Upstox API", color: "#7c3aed" },
    { name: "Angel One", sub: "Connect via Angel One SmartAPI", color: "#2563eb" },
    { name: "HDFC Sky", sub: "Connect via HDFC Sky", color: "#0ea5e9" },
    { name: "Anand Rathi", sub: "Connect via Anand Rathi", color: "#a16207" },
  ];
  return (
    <div className="absolute inset-0 flex flex-col gap-1.5 overflow-hidden px-2.5 pb-4 pt-6" style={{ backgroundColor: "#08090b" }}>
      <BrokerHeader />
      <div className="text-[5px] font-bold uppercase tracking-[0.2em] text-dim">Brokers</div>
      <div className="flex flex-col gap-1">{brokers.map((b) => <BrokerRow key={b.name} b={b} />)}</div>
      <div className="mt-auto"><BrokerTabBar /></div>
    </div>
  );
}

function HdfcLoginScreen() {
  return (
    <div className="absolute inset-0 flex flex-col bg-white text-left">
      <div className="flex items-center justify-between bg-[#efefef] px-2 pb-1.5 pt-6">
        <span className="grid h-4 w-4 place-items-center rounded-full bg-white text-[7px] text-gray-600">✕</span>
        <span className="text-[7px] font-medium text-gray-800">developer.hdfcsky.com</span>
        <span className="grid h-4 w-4 place-items-center rounded-full bg-white text-[7px] text-gray-600">▭</span>
      </div>
      <div className="flex-1 px-3 pt-4" style={{ backgroundImage: "linear-gradient(180deg,#eef2f8,#ffffff 40%)" }}>
        <div className="flex items-center gap-1">
          <span className="grid h-5 w-5 place-items-center rounded-full text-[8px] font-bold text-white" style={{ backgroundImage: "linear-gradient(135deg,#2f7de1,#0a2a6b)" }}>S</span>
          <span className="text-[7px] font-extrabold leading-[1.05] text-[#0a2a6b]">HDFC<br />SKY</span>
        </div>
        <h4 className="mt-4 text-[19px] font-extrabold leading-[1.05] text-[#0f1b33]">Login To<br />maven</h4>
        <p className="mt-1.5 text-[5.5px] text-gray-500">Please enter Client ID / Mobile Number / Email ID to get started</p>
        <div className="mt-3 rounded-md border border-gray-300 bg-white px-2 py-2 text-[6px] text-gray-400">Enter Client ID / Mobile Number / Email ID</div>
        <div className="mt-2 rounded-md py-2 text-center text-[8px] font-bold text-white" style={{ backgroundColor: "#0a66ff" }}>Get Started</div>
      </div>
    </div>
  );
}

// pick the right live screen for a given layer / gallery slot
function mainMock(layer: (typeof LAYERS)[number]): ReactNode {
  if (layer.n === 1) return <MarketModeScreen />;
  if (layer.n === 2) return <PortfoliosScreen variant="Balanced" />;
  if (layer.n === 3) return <WatchlistScreen />;
  if (layer.n === 4) return <BrokerConnectScreen />;
  return undefined;
}
function galleryMock(layer: (typeof LAYERS)[number], cap: string): ReactNode {
  if (layer.n === 2) return <PortfoliosScreen variant={cap} small />;
  if (layer.n === 4) {
    if (cap === "Brokers") return <BrokerListScreen />;
    if (cap === "Sign-in") return <HdfcLoginScreen />;
  }
  return undefined;
}

// device-framed phone mockup with graceful placeholder
function Device({ src, label, small = false, mock }: { src: string; label: string; small?: boolean; mock?: ReactNode }) {
  const [imgOk, setImgOk] = useState(false);
  // Responsive widths — comfortable on phones, full size from sm up.
  const w = small ? "w-[140px] sm:w-[170px]" : "w-[256px] sm:w-[272px]";
  return (
    <div className="relative animate-floatY motion-reduce:animate-none">
      <div className="pointer-events-none absolute -inset-8 -z-10 rounded-[3rem] opacity-70 blur-2xl" style={{ background: "radial-gradient(50% 45% at 50% 40%,rgba(52,211,153,0.20),transparent 70%)" }} />
      <div className={`relative mx-auto ${w} rounded-[2.4rem] border border-border bg-panel2 p-2.5`} style={{ boxShadow: "0 24px 60px -30px rgba(0,0,0,0.8)" }}>
        <div className="relative aspect-[390/844] overflow-hidden rounded-[1.9rem] bg-bg ring-1 ring-black/60">
          {/* Base layer — rendered server-side so it shows instantly on every device
              (this is what fixes blank/broken frames on iOS & Android). */}
          {mock ? (
            mock
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-3 px-4 text-center" style={{ background: "radial-gradient(60% 50% at 50% 30%,rgba(52,211,153,0.12),transparent 70%)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
                <rect x="3" y="3" width="18" height="18" rx="3" stroke="#34d399" strokeWidth="1.5" />
                <circle cx="8.5" cy="8.5" r="1.6" stroke="#34d399" strokeWidth="1.5" />
                <path d="M21 15l-5-5L5 21" stroke="#34d399" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-[0.55rem] font-semibold uppercase tracking-label text-gold/80">Screenshot slot</p>
              <p className="font-serif text-sm text-ink">{label}</p>
              {!small && <code className="rounded bg-panel px-2 py-1 text-[0.6rem] text-dim">/screenshots/{src}</code>}
            </div>
          )}
          {/* Real screenshot overlay — fades in only once it actually loads; a missing
              or 404 file stays invisible so the base layer shows through. No onError
              broken-image flash, which is what iOS was choking on. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/screenshots/${src}`}
            alt={label}
            loading="lazy"
            onLoad={() => setImgOk(true)}
            className={`absolute inset-0 z-10 h-full w-full object-cover object-top transition-opacity duration-300 ${imgOk ? "opacity-100" : "opacity-0"}`}
          />
          {/* notch */}
          <div className="absolute left-1/2 top-2 z-30 h-4 w-20 -translate-x-1/2 rounded-full bg-black/85" />
        </div>
      </div>
    </div>
  );
}

// Hero product visual — the real Market Mode device mock in a scroll-flattening
// 3D tilt (Linear pattern): starts leaned back, settles flat as you scroll.
// Motion-value-driven inside .brand-motion, so it plays under OS reduced-motion.
function HeroDeviceTilt({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useScrollScrub(ref, ["start start", "end start"]);
  // settle completes within the first ~16% of the device's scroll-out so the
  // flatten beat plays while the phone is still mostly on screen
  const rotateX = useTransform(progress, [0, 0.16], [18, 0]);
  const rotateY = useTransform(progress, [0, 0.16], [-6, 0]);
  const scale = useTransform(progress, [0, 0.16], [0.94, 1]);
  return (
    <div ref={ref} className="brand-motion relative flex justify-center" style={{ perspective: 1200 }}>
      {/* one radial emerald glow BEHIND the phone (light-source, never on it) + 2% noise to kill banding */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-[-12%] -z-10"
        style={{ background: "radial-gradient(50% 45% at 50% 48%, rgba(52,211,153,0.18), transparent 70%)" }}
      >
        <div className="noise-overlay" />
      </div>
      <motion.div style={{ rotateX, rotateY, scale, transformStyle: "preserve-3d" }}>
        {children}
      </motion.div>
    </div>
  );
}

// ─────────────── signature moment — "The Fall, Scrubbed" ───────────────
// Sticky 240vh scroll-scrubbed covid drawdown proof, staged in CSS 3D: three
// stacked SVG planes (grid → market → Enhanced F+) straighten from a 22°
// lean as the market line carves down to −38% and Enhanced F+ traces its
// shallower −13.88% path. One MotionValue per line drives BOTH the path draw
// and its counter, so they can never desync. Story completes by p=0.8 — the
// last 20% is settle/hold (annotation chips landed, one light sweep, done).
// Axis labels are HTML (fixed px) so they stay readable at 375px.

const W = 740, H = 400, padL = 16, padR = 18, padT = 28, padB = 20, Y_MIN = -42;
const MONTHS = [0, 0.08, 0.16, 0.22, 0.28, 0.34, 0.4, 0.5, 0.62, 0.78, 0.9, 1];
const MARKET = [0, -2, -5, -14, -28, -38, -33, -24, -16, -9, -4, -1];
const FPLUS = [0, -1, -2, -5, -10, -14, -12, -8, -5, -3, -1, 0];
const xs = (m: number) => padL + m * (W - padL - padR);
const ys = (d: number) => padT + (-d / -Y_MIN) * (H - padT - padB);
type P = readonly [number, number];
function smooth(pts: P[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2;
    d += ` C ${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]},${p2[1]}`;
  }
  return d;
}
const fPts: P[] = MONTHS.map((m, i) => [xs(m), ys(FPLUS[i])]);
const mPts: P[] = MONTHS.map((m, i) => [xs(m), ys(MARKET[i])]);
const lastM = mPts[mPts.length - 1];
const band = smooth(fPts) + ` L ${lastM[0]},${lastM[1]}` + smooth([...mPts].reverse()).replace(/^M[^C]*/, "") + " Z";
// Trough coordinates as % of the chart box — annotation chips are HTML,
// positioned against the same viewBox math the SVG planes use.
const TROUGH_X_PCT = (xs(MONTHS[5]) / W) * 100;
const M_TROUGH_Y_PCT = (ys(MARKET[5]) / H) * 100;
const F_TROUGH_Y_PCT = (ys(FPLUS[5]) / H) * 100;

function DrawdownScrub() {
  const wrapRef = useRef<HTMLDivElement>(null);
  // Raw motion values through a stiffened house spring — user-driven scrub, so
  // it is NEVER gated by useReducedMotionSafe (signature plays under OS flag).
  const spring = useScrollScrub(wrapRef, ["start start", "end end"], { stiffness: 120, damping: 24, restDelta: 0.001 });

  // Hydration flag — before it flips, the back plane shows full-strength static
  // tracks + trough labels and the tiles read the real drawdown figures, so the
  // signature proof reads for crawlers / JS-off. On mount, JS dims the fallback
  // and resets the counters to 0 so the scrub counts up as designed.
  const [mounted, setMounted] = useState(false);
  // ≤640px: the .dd-stage CSS vars collapse plane depth; JS only softens the lean.
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    setNarrow(mq.matches);
    const on = (e: MediaQueryListEvent) => setNarrow(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  // ── One MotionValue per line is the single source of truth: the SAME value
  // drives the path draw AND its counter, so desync is structurally impossible.
  const marketProg = useTransform(spring, [0.05, 0.45], [0, 1], { clamp: true });
  const fplusProg = useTransform(spring, [0.35, 0.65], [0, 1], { clamp: true });
  const bandOpacity = useTransform(spring, [0.62, 0.78], [0, 1]);
  const marketDotOpacity = useTransform(spring, [0.45, 0.52], [0, 1]);
  // Plane straightens across the first beat; the card shadow deepens with it.
  const rotateX = useTransform(spring, [0, 0.45], [narrow ? 12 : 22, 0]);
  const rotateY = useTransform(spring, [0, 0.45], [narrow ? -3 : -6, 0]);
  const yDrift = useTransform(spring, [0, 0.45], [narrow ? 8 : 14, 0]);
  const cardShadow = useTransform(spring, [0, 0.45], [
    "0 10px 30px -24px rgba(0,0,0,0)",
    "0 42px 90px -40px rgba(0,0,0,0.75)",
  ]);

  // Number-Ticker pattern: write digits straight to the DOM (no re-render/frame).
  const marketNumRef = useRef<HTMLSpanElement>(null);
  const fplusNumRef = useRef<HTMLSpanElement>(null);
  useMotionValueEvent(marketProg, "change", (v) => {
    if (marketNumRef.current) marketNumRef.current.textContent = v === 0 ? "0%" : `−${(v * 38).toFixed(0)}%`;
  });
  useMotionValueEvent(fplusProg, "change", (v) => {
    if (fplusNumRef.current) fplusNumRef.current.textContent = v === 0 ? "0%" : `−${(v * 13.88).toFixed(2)}%`;
  });

  // JS present: dim the static fallback and reset the SSR'd figures to 0 so the
  // scrub counts up from zero. With JS off, tiles keep their real values.
  useEffect(() => {
    setMounted(true);
    if (marketNumRef.current) marketNumRef.current.textContent = "0%";
    if (fplusNumRef.current) fplusNumRef.current.textContent = "0%";
  }, []);

  // Beat thresholds — chips spring in, the F+ dot lands, and one light sweep
  // fires once past p=0.8. After that, nothing moves: settle/hold to exit.
  const [marketChip, setMarketChip] = useState(false);
  const [fplusChip, setFplusChip] = useState(false);
  const [landed, setLanded] = useState(false);
  const sweptRef = useRef(false);
  const [swept, setSwept] = useState(false);
  useMotionValueEvent(spring, "change", (v) => {
    setMarketChip(v > 0.45);
    setFplusChip(v > 0.65);
    setLanded(v > 0.76);
    if (v > 0.8 && !sweptRef.current) {
      sweptRef.current = true;
      setSwept(true);
    }
  });
  return (
    <div ref={wrapRef} className="relative h-[240vh] [@media(max-width:640px)]:h-[180vh]">
      {/* h-svh (with h-screen fallback) tracks mobile dynamic toolbars; on short
          viewports (landscape phones, small laptops) top-align and let the pinned
          frame scroll internally instead of clipping the card */}
      <div className="brand-motion sticky top-0 flex h-screen h-svh items-center [@media(max-height:640px)]:items-start [@media(max-height:640px)]:overflow-y-auto [@media(max-height:640px)]:py-3">
        <motion.div className="relative w-full rounded-xl2 border border-border bg-panel/60 p-5 sm:p-6" style={{ boxShadow: cardShadow }}>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-[0.6rem] font-semibold uppercase tracking-label text-dim">Peak-to-trough drawdown</p>
              <p className="mt-1 font-serif text-lg text-ink">The covid crash</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted">
              <span className="flex items-center gap-2"><svg width="18" height="6" aria-hidden><line x1="0" y1="3" x2="18" y2="3" stroke="#5a616a" strokeWidth="2.4" strokeDasharray="4 3" /></svg>Market</span>
              <span className="flex items-center gap-2"><svg width="18" height="6" aria-hidden><line x1="0" y1="3" x2="18" y2="3" stroke="#34d399" strokeWidth="2.8" /></svg>Enhanced F+</span>
            </div>
          </div>
          {/* 3D stage: perspective wrapper → preserve-3d plane carrying the
              scroll-driven straighten → three stacked SVG planes (same viewBox,
              absolutely positioned). Per-element translateZ does NOT work inside
              one SVG, hence the split. Depths live in .dd-stage CSS vars
              (globals.css) so ≤640px collapses to 0/20/40 without JS. */}
          <div style={{ perspective: 1200 }}>
            <motion.div className="dd-stage relative" style={{ rotateX, rotateY, y: yDrift, transformStyle: "preserve-3d" }}>
              <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
                {/* Back plane — gridlines + static faint tracks (server-rendered:
                    the proof reads even with JS off) + HTML axis labels. */}
                <div className="pointer-events-none absolute inset-0" style={{ transform: "translateZ(var(--dd-z-back)) scale(var(--dd-s-back))" }}>
                  <svg viewBox={`0 0 ${W} ${H}`} className="block h-full w-full" aria-hidden>
                    {[0, -10, -20, -30, -40].map((g) => (
                      <line key={g} x1={padL} x2={W - padR} y1={ys(g)} y2={ys(g)} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
                    ))}
                    {/* Full-strength before hydration so the proof is drawn with
                        JS off; dims to ghost tracks once the scrubbed planes take over. */}
                    <path d={smooth(mPts)} fill="none" stroke={mounted ? "rgba(90,97,106,0.30)" : "rgba(90,97,106,0.9)"} strokeWidth={mounted ? 1.5 : 2} strokeDasharray="5 5" strokeLinecap="round" />
                    <path d={smooth(fPts)} fill="none" stroke={mounted ? "rgba(52,211,153,0.22)" : "rgba(52,211,153,0.85)"} strokeWidth={mounted ? 1.5 : 3} strokeLinecap="round" />
                  </svg>
                  {/* HTML axis labels — fixed px so they stay readable at 375px. */}
                  {[0, -10, -20, -30, -40].map((g) => (
                    <span
                      key={g}
                      aria-hidden
                      className="tnum absolute left-1 font-mono text-[10px] leading-none text-dim"
                      style={{ top: `calc(${((ys(g) / H) * 100).toFixed(2)}% - 13px)` }}
                    >
                      {g}%
                    </span>
                  ))}
                  {/* Server-rendered trough labels — the two figures the scrub proves,
                      readable with JS off / pre-hydration; the scroll-driven chips on
                      the front plane replace them once mounted. */}
                  <span
                    aria-hidden={mounted}
                    className={`absolute whitespace-nowrap rounded-full border border-border bg-panel2/90 px-2.5 py-1 font-mono text-[10px] leading-none text-muted transition-opacity duration-500 ${mounted ? "opacity-0" : "opacity-100"}`}
                    style={{ left: `calc(${TROUGH_X_PCT.toFixed(2)}% + 12px)`, top: `calc(${M_TROUGH_Y_PCT.toFixed(2)}% - 28px)` }}
                  >
                    Market −38%
                  </span>
                  <span
                    aria-hidden={mounted}
                    className={`absolute whitespace-nowrap rounded-full border border-emerald/40 bg-emerald/10 px-2.5 py-1 font-mono text-[10px] leading-none text-emerald transition-opacity duration-500 ${mounted ? "opacity-0" : "opacity-100"}`}
                    style={{ left: `calc(${TROUGH_X_PCT.toFixed(2)}% - 12px)`, top: `calc(${F_TROUGH_Y_PCT.toFixed(2)}% - 34px)` }}
                  >
                    Enhanced F+ −13.88%
                  </span>
                </div>
                {/* Mid plane — gap band, market path, market trough dot. */}
                <div className="pointer-events-none absolute inset-0" style={{ transform: "translateZ(var(--dd-z-mid))" }}>
                  <svg viewBox={`0 0 ${W} ${H}`} className="block h-full w-full" role="img" aria-label="Drawdown comparison, scrubbed by scroll: market troughs at -38%, Enhanced F+ at -13.88%.">
                    <defs>
                      <linearGradient id="ddband" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#34d399" stopOpacity="0.16" />
                        <stop offset="100%" stopColor="#34d399" stopOpacity="0.02" />
                      </linearGradient>
                    </defs>
                    {/* Gap band fills late — the "half the fall" area. */}
                    <motion.path d={band} fill="url(#ddband)" style={{ opacity: bandOpacity }} />
                    {/* marketProg drives BOTH this draw and the market counter. */}
                    <motion.path d={smooth(mPts)} fill="none" stroke="#5a616a" strokeWidth={2} strokeDasharray="5 5" strokeLinecap="round" style={{ pathLength: marketProg }} />
                    <motion.circle cx={xs(MONTHS[5])} cy={ys(MARKET[5])} r={4} fill="#0a0b0d" stroke="#5a616a" strokeWidth={2} style={{ opacity: marketDotOpacity }} />
                  </svg>
                </div>
                {/* Front plane — Enhanced F+ path + landing dot; the drop-shadow
                    is the depth/glow cue. fplusProg also drives the F+ counter. */}
                <div className="pointer-events-none absolute inset-0" style={{ transform: "translateZ(var(--dd-z-front))", filter: "drop-shadow(0 6px 16px rgba(52,211,153,0.35))" }}>
                  <svg viewBox={`0 0 ${W} ${H}`} className="block h-full w-full" aria-hidden>
                    <motion.path d={smooth(fPts)} fill="none" stroke="#34d399" strokeWidth={3} strokeLinecap="round" style={{ pathLength: fplusProg }} />
                    {/* The emerald F+ marker LANDS with a spring — payoff beat. */}
                    <motion.circle
                      cx={xs(MONTHS[5])} cy={ys(FPLUS[5])} r={4.5} fill="#0a0b0d" stroke="#34d399" strokeWidth={2.5}
                      style={{ transformBox: "fill-box", transformOrigin: "center" }}
                      initial={{ opacity: 0, scale: 0.3 }}
                      animate={landed ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.3 }}
                      transition={{ opacity: { duration: 0.2 }, scale: { type: "spring", stiffness: 520, damping: 13 } }}
                    />
                  </svg>
                </div>
                {/* Annotation chips — HTML on the closest plane, each on its own
                    spring so the planes settle at different rates. */}
                <div className="pointer-events-none absolute inset-0" style={{ transform: "translateZ(var(--dd-z-chip))" }}>
                  <motion.div
                    className="absolute whitespace-nowrap rounded-full border border-border bg-panel2/90 px-2.5 py-1 font-mono text-[10px] leading-none text-muted"
                    style={{ left: `calc(${TROUGH_X_PCT.toFixed(2)}% + 12px)`, top: `calc(${M_TROUGH_Y_PCT.toFixed(2)}% - 28px)` }}
                    initial={{ opacity: 0, y: 8, scale: 0.9 }}
                    animate={marketChip ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 8, scale: 0.9 }}
                    transition={{ type: "spring", stiffness: 380, damping: 24 }}
                  >
                    Market −38%
                  </motion.div>
                  <motion.div
                    className="absolute whitespace-nowrap rounded-full border border-emerald/40 bg-emerald/10 px-2.5 py-1 font-mono text-[10px] leading-none text-emerald"
                    style={{ left: `calc(${TROUGH_X_PCT.toFixed(2)}% - 12px)`, top: `calc(${F_TROUGH_Y_PCT.toFixed(2)}% - 34px)` }}
                    initial={{ opacity: 0, y: 8, scale: 0.9 }}
                    animate={fplusChip ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 8, scale: 0.9 }}
                    transition={{ type: "spring", stiffness: 300, damping: 18 }}
                  >
                    Enhanced F+ −13.88%
                  </motion.div>
                </div>
              </div>
            </motion.div>
          </div>
          <div className="mt-1.5 flex items-center justify-between font-mono text-[10px] text-dim">
            <span>Jan 2020</span>
            <span>Dec 2020</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-border bg-panel2/50 p-4">
              <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Market fell</p>
              <p className="mt-1 font-mono text-2xl text-muted sm:text-3xl"><span ref={marketNumRef} className="tnum">−38%</span></p>
            </div>
            <div className="rounded-xl border border-emerald/30 bg-emerald/[0.06] p-4">
              <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Enhanced F+ fell</p>
              <p className="mt-1 font-mono text-2xl text-emerald sm:text-3xl"><span ref={fplusNumRef} className="tnum">−13.88%</span></p>
            </div>
          </div>
          {/* One-shot light sweep — fired once past p=0.8 (motion-value event,
              inside .brand-motion so it plays under the OS reduced-motion flag).
              After it passes, nothing moves: settle/hold to exit. */}
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl2">
            <motion.div
              className="absolute inset-y-0 left-0 w-1/3"
              style={{ background: "linear-gradient(105deg, transparent, rgba(52,211,153,0.07), rgba(233,235,237,0.06), transparent)" }}
              initial={{ x: "-130%", opacity: 0 }}
              animate={swept ? { x: "340%", opacity: [0, 1, 0] } : { x: "-130%", opacity: 0 }}
              transition={{ duration: 1.2, ease: "easeInOut" }}
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}

// ───────────────────────────── sections ─────────────────────────────

/** Enters with a soft mask-image gradient wipe (left→right) instead of a
 *  fade-up. animate()-driven signature reveal, so it plays under the OS
 *  reduced-motion flag (numbers panel is a signature moment, not decoration). */
function MaskWipe({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const t = useMotionValue(0);
  useEffect(() => {
    if (!inView) return;
    const c = animate(t, 1, { duration: 1.1, ease: EASE });
    return () => c.stop();
  }, [inView, t]);
  const maskPos = useTransform(t, (v) => `${(1 - v) * 100}% 0%`);
  const mask = "linear-gradient(100deg, #000 45%, transparent 65%)";
  return (
    <motion.div
      ref={ref}
      className={className}
      style={{
        WebkitMaskImage: mask,
        maskImage: mask,
        WebkitMaskSize: "300% 100%",
        maskSize: "300% 100%",
        WebkitMaskRepeat: "no-repeat",
        maskRepeat: "no-repeat",
        WebkitMaskPosition: maskPos,
        maskPosition: maskPos,
      }}
    >
      {children}
    </motion.div>
  );
}

/** Thin sticky progress rail spanning the Validation section (hidden <lg):
 *  scaleY tracks section progress from the top; one dot per validation beat
 *  lights as the reader passes it. Scroll-driven, no loops. */
function ValidationRail({ target }: { target: RefObject<HTMLElement> }) {
  const { scrollYProgress } = useScroll({ target, offset: ["start 0.75", "end 0.75"] });
  return (
    <div aria-hidden className="pointer-events-none absolute -left-5 top-0 hidden h-full lg:block xl:-left-9">
      <div className="sticky top-[22vh] h-[56vh]">
        <div className="relative mx-auto h-full w-px bg-border/60">
          <motion.div className="absolute left-0 top-0 h-full w-px origin-top bg-emerald/70" style={{ scaleY: scrollYProgress }} />
          {TIMELINE.map((tl, i) => (
            <RailDot
              key={tl.t}
              progress={scrollYProgress}
              at={i === 0 ? 0.04 : i / (TIMELINE.length - 1)}
              top={`${(i / (TIMELINE.length - 1)) * 100}%`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function RailDot({ progress, at, top }: { progress: MotionValue<number>; at: number; top: string }) {
  const active = useTransform(progress, [Math.max(0, at - 0.04), at], [0, 1]);
  const scale = useTransform(active, [0, 1], [0.6, 1]);
  const opacity = useTransform(active, [0, 1], [0.3, 1]);
  return (
    <motion.span
      className="absolute left-1/2 h-2 w-2 rounded-full bg-emerald"
      style={{ top, scale, opacity, x: "-50%", marginTop: -4 }}
    />
  );
}

/** Two converging gold→emerald beams that draw with approach scroll, framing
 *  the closing checklist. Static faint tracks stay for JS-off / pre-scroll. */
function ConvergeBeams() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.9", "start 0.4"] });
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const gradId = `converge-${uid}`;
  const L = "M0 4 C170 4 225 52 300 52";
  const R = "M600 4 C430 4 375 52 300 52";
  return (
    <div ref={ref} aria-hidden className="pointer-events-none mx-auto mt-10 w-full max-w-2xl px-6">
      <svg viewBox="0 0 600 56" fill="none" className="block w-full overflow-visible">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#c9a961" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
        <path d={L} stroke={`url(#${gradId})`} strokeOpacity="0.10" strokeWidth="1.5" strokeLinecap="round" />
        <path d={R} stroke={`url(#${gradId})`} strokeOpacity="0.10" strokeWidth="1.5" strokeLinecap="round" />
        <motion.path d={L} stroke={`url(#${gradId})`} strokeOpacity="0.55" strokeWidth="1.5" strokeLinecap="round" style={{ pathLength: scrollYProgress }} />
        <motion.path d={R} stroke={`url(#${gradId})`} strokeOpacity="0.55" strokeWidth="1.5" strokeLinecap="round" style={{ pathLength: scrollYProgress }} />
      </svg>
    </div>
  );
}

/** One-shot light sweep across a relative parent, fired once on inView.
 *  JS-driven inside .brand-motion so it plays under the OS flag. No loops. */
function SweepOnce() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  return (
    <div ref={ref} aria-hidden className="brand-motion pointer-events-none absolute inset-0 overflow-hidden rounded-xl">
      <motion.div
        className="absolute inset-y-0 left-0 w-1/3"
        style={{ background: "linear-gradient(105deg, transparent, rgba(52,211,153,0.07), rgba(233,235,237,0.06), transparent)" }}
        initial={{ x: "-130%", opacity: 0 }}
        animate={inView ? { x: "340%", opacity: [0, 1, 0] } : { x: "-130%", opacity: 0 }}
        transition={{ duration: 1.2, ease: "easeInOut", delay: 0.25 }}
      />
    </div>
  );
}

function PrincipleIcon({ k }: { k: string }) {
  const c = { width: 26, height: 26, viewBox: "0 0 28 28", fill: "none", strokeWidth: 1.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, stroke: "#34d399" };
  if (k === "regime") return <svg {...c} aria-hidden><path d="M3 16 L8 14 L11 17 L14 9 L17 13 L21 6 L25 11" /><path d="M3 22 H25" opacity="0.3" /></svg>;
  if (k === "quality") return <svg {...c} aria-hidden><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="17" y="4" width="7" height="7" rx="1.5" opacity="0.6" /><rect x="4" y="17" width="7" height="7" rx="1.5" opacity="0.6" /><rect x="17" y="17" width="7" height="7" rx="1.5" /></svg>;
  return <svg {...c} aria-hidden><path d="M14 3 L23 7 V13 C23 19 19 23 14 25 C9 23 5 19 5 13 V7 Z" /><path d="M11 13.5 L13 15.5 L17.5 11" /></svg>;
}

function Layer({ layer, flip }: { layer: (typeof LAYERS)[number]; flip: boolean }) {
  const rowRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotionSafe();
  // Per-row parallax: device and text columns ride different y ranges
  // (locomotive speed-multipliers in framer form). Decorative → zeroed under
  // reduced motion. Outer divs carry the parallax MotionValue; inner divs
  // carry the entrance cascade, so y never fights itself.
  const { scrollYProgress: rowP } = useScroll({ target: rowRef, offset: ["start 0.85", "start 0.35"] });
  const textY = useTransform(rowP, [0, 1], reduce ? [0, 0] : [12, -12]);
  const deviceY = useTransform(rowP, [0, 1], reduce ? [0, 0] : [30, -30]);
  const cascade: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: reduce ? 0 : 0.05 } },
  };
  const item: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, y: 18 },
    show: { opacity: 1, y: 0, transition: { duration: 0.65, ease: EASE } },
  };
  return (
    <div ref={rowRef} className="grid items-center gap-10 lg:grid-cols-2 lg:gap-14">
      <motion.div style={{ y: textY }} className={flip ? "lg:order-2" : ""}>
        <motion.div variants={cascade} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.25 }}>
          <motion.div variants={item} className="flex items-center gap-4">
            <span className="font-serif text-4xl font-light text-emerald/30 sm:text-5xl">0{layer.n}</span>
            <div>
              <p className="text-[0.6rem] font-semibold uppercase tracking-label text-dim">Layer {layer.n} · {layer.nav}</p>
              <h3 className="font-serif text-3xl tracking-tight text-ink">{layer.name}</h3>
            </div>
          </motion.div>
          <motion.p variants={item} className="mt-5 font-serif text-2xl italic leading-snug" style={GRAD_EMERALD}>{layer.oneLine}</motion.p>
          <motion.p variants={item} className="mt-4 max-w-xl leading-relaxed text-muted">{layer.summary}</motion.p>
          <motion.div variants={item} className="mt-6">
            <div className="inline-flex items-center gap-2 rounded-xl border border-border bg-panel2/60 px-4 py-2.5">
              <span className="text-gold">◆</span>
              <span className="text-sm text-ink">{layer.mental}</span>
            </div>
          </motion.div>
          {layer.chips && (
            <motion.div variants={item} className="mt-6">
              <p className="mb-3 text-[0.55rem] font-semibold uppercase tracking-label text-dim">{layer.chipLabel}</p>
              <div className="flex flex-wrap gap-2">
                {layer.chips.map((c) => <span key={c} className="rounded-full border border-border bg-panel/60 px-3 py-1 text-xs text-muted">{c}</span>)}
              </div>
            </motion.div>
          )}
          {layer.note && (
            <motion.div variants={item} className="mt-6 flex items-start gap-3 rounded-xl border border-gold/15 bg-gold/[0.04] p-4">
              {layer.illustrative ? <IllustrativeTag /> : <LivePill>Read-only</LivePill>}
              <p className="text-sm leading-relaxed text-muted">{layer.note}</p>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
      <motion.div style={{ y: deviceY }} className={flip ? "lg:order-1" : ""}>
        <motion.div
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.75, ease: EASE }}
        >
          {layer.gallery.length > 0 ? (
            <div className="flex flex-col items-center gap-6">
              <Device src={layer.screenshot} label={layer.name} mock={mainMock(layer)} />
              <div className="flex flex-wrap justify-center gap-3">
                {layer.gallery.map((g) => (
                  <div key={g.file} className="flex flex-col items-center gap-2">
                    <Device src={g.file} label={g.cap} small mock={galleryMock(layer, g.cap)} />
                    <span className="text-[0.6rem] text-dim">{g.cap}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Device src={layer.screenshot} label={layer.name} mock={mainMock(layer)} />
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}

export function Explainer() {
  const reduce = useReducedMotionSafe();
  // Hero headline: clip-path reveals (left→right wipe per line) staggered via
  // variants; opacity-only under reduced motion.
  const heroStagger: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.06, delayChildren: reduce ? 0 : 0.15 } },
  };
  const heroLine: Variants = reduce
    ? { hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 0.6, ease: EASE } } }
    : { hidden: { clipPath: "inset(0 100% 0 0)" }, show: { clipPath: "inset(0 0% 0 0)", transition: { duration: 0.9, ease: EASE } } };
  // Validation section ref — anchors the sticky side-rail's scroll progress.
  const validationRef = useRef<HTMLElement>(null);
  return (
    <div className="relative overflow-x-clip">
      <ScrollProgress />
      {/* ── Hero ── */}
      <section className="relative grid min-h-[78svh] items-center gap-10 py-16 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="pointer-events-none absolute inset-0 -z-10" style={{ background: "radial-gradient(55% 50% at 30% 40%,rgba(52,211,153,0.10),transparent 70%)" }} />
        <div>
          <motion.div initial={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="mb-6 flex items-center gap-3">
            <LivePill>Indian markets · live</LivePill>
            <span className="text-[0.7rem] font-semibold uppercase tracking-label text-gold">How it works</span>
          </motion.div>
          <motion.h1
            className="font-serif text-[clamp(2.5rem,1rem+6vw,5.5rem)] font-light leading-[0.98] tracking-[-0.025em] text-ink"
            variants={heroStagger}
            initial="hidden"
            animate="show"
          >
            <motion.span className="block" variants={heroLine}>Beats the market.</motion.span>
            <motion.span className="block italic" style={GRAD_EMERALD} variants={heroLine}>Half the fall.</motion.span>
          </motion.h1>
          <motion.p initial={reduce ? { opacity: 0 } : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.3 }} className="mt-7 max-w-lg text-lg leading-relaxed text-muted">
            An AI research engine for Indian equities — built on a strategy validated across two market eras, including covid.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 0.5 }} className="mt-10">
            <GlassPanel className="max-w-xl" innerClassName="p-5 sm:p-6">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-3 sm:gap-x-7">
                <span className="flex items-baseline gap-2.5"><CountUp to={129.97} prefix="+" suffix="%" decimals={2} className="font-serif text-4xl text-emerald" /><span className="text-sm text-dim">Enhanced F+ · 2021–26</span></span>
                <span className="text-dim">vs</span>
                <span className="flex items-baseline gap-2.5"><CountUp to={82.17} prefix="+" suffix="%" decimals={2} className="font-serif text-4xl text-muted" /><span className="text-sm text-dim">Nifty 500</span></span>
              </div>
              <p className="mt-3 text-xs text-dim">Full-period total return, 2021–2026 — at lower drawdown 14.05% vs 18.59% · Backtested, not a live track record</p>
            </GlassPanel>
            <motion.div initial={reduce ? { opacity: 0 } : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.65, ease: EASE }}>
              <MagneticButton
                type="button"
                onClick={() => document.getElementById("strategies")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" })}
                className="group mt-8 inline-flex items-center gap-3 rounded-full border border-border bg-panel/50 py-2.5 pl-5 pr-2.5 text-sm text-muted transition-[border-color,background-color,color] duration-300 hover:border-emerald/40 hover:bg-panel/70 hover:text-ink"
              >
                <span>See how every model works</span>
                <span className="grid h-7 w-7 place-items-center rounded-full bg-emerald/10 text-emerald transition-colors duration-300 group-hover:bg-emerald/20">
                  {/* Chevron nudges down only on hover — no infinite loop, on-system
                      with the page's "decorative loops freeze" stance. */}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="transition-transform duration-300 motion-safe:group-hover:translate-y-0.5"><path d="M6 9l6 6 6-6" /></svg>
                </span>
              </MagneticButton>
            </motion.div>
          </motion.div>
        </div>
        {/* Right column: the real product, not abstract rings — Market Mode mock
            in a scroll-flattening tilt with one radial glow behind it. */}
        <motion.div initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.2, delay: 0.3 }}>
          <HeroDeviceTilt>
            <Device src="market-mode.png" label="Market Mode" mock={<MarketModeScreen />} />
          </HeroDeviceTilt>
        </motion.div>
      </section>

      {/* ── Core idea ── */}
      <section className="border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="01">The core idea</Eyebrow>
        <div className="mt-8">
          <Reveal>
            <h2 className="max-w-xl text-balance font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">
              The edge isn&apos;t picking winners. <span className="italic" style={GRAD_GOLD}>It&apos;s not losing.</span>
            </h2>
          </Reveal>
          <div className="mt-6 max-w-lg space-y-4 text-lg leading-relaxed text-muted">
            <Reveal><p>Most strategies chase return. The Enhanced F+ engine chases survival first — and lets return follow.</p></Reveal>
            <Reveal delay={0.05}><p>Across a full crash it participated on the way up and stepped aside on the way down. The result wasn&apos;t a bigger number. It was a smaller hole.</p></Reveal>
          </div>
        </div>
        {/* The signature: full-width sticky scroll-scrub proof (no Reveal wrapper —
            a transformed ancestor would break position: sticky). */}
        <div className="mt-10">
          <DrawdownScrub />
        </div>
        {/* Principles: clip-path reveal cascade (0.07s stagger) + a decorative
            pointer tilt (mouse-only, reduced-motion gated). Tilt wraps the clip
            wrapper so the settled clip box never cuts the rotated corners. */}
        <motion.div
          className="mt-16 grid gap-4 md:grid-cols-3"
          variants={{ hidden: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.07 } } }}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.4 }}
        >
          {PRINCIPLES.map((p, i) => (
            <TiltCard key={p.k} className="h-full">
              <ClipItem className="h-full">
                <div className="group h-full rounded-xl2 bg-gradient-to-b from-white/[0.14] to-white/[0.03] p-px transition-transform duration-300 motion-safe:hover:-translate-y-1">
                  <div className="h-full rounded-[inherit] bg-panel p-6 transition-shadow duration-300 group-hover:shadow-[0_22px_50px_-24px_rgba(52,211,153,0.45)]">
                    <div className="flex items-center justify-between">
                      <span className="grid h-11 w-11 place-items-center rounded-xl border border-border bg-panel2"><PrincipleIcon k={p.k} /></span>
                      <span className="font-serif text-2xl text-border">0{i + 1}</span>
                    </div>
                    <h3 className="mt-5 font-serif text-2xl text-ink">{p.t}</h3>
                    <p className="mt-3 text-[0.95rem] leading-relaxed text-muted">{p.b}</p>
                  </div>
                </div>
              </ClipItem>
            </TiltCard>
          ))}
        </motion.div>
        <Reveal><p className="mx-auto mt-14 max-w-2xl text-center font-serif text-xl italic leading-relaxed text-muted">“It participates when markets rise, and steps aside when they fall. That discipline — not stock-picking magic — is the edge.”</p></Reveal>
      </section>

      {/* ── Four layers ── */}
      <section className="border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="02">The four layers</Eyebrow>
        <Reveal><h2 className="mt-8 max-w-2xl text-balance font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">One engine, four ways in.</h2></Reveal>
        <Reveal delay={0.05}><p className="mt-4 max-w-xl text-lg leading-relaxed text-muted">From reading the market to connecting your account — each layer does one job, and hands off cleanly to the next.</p></Reveal>
        <div className="mt-16 flex flex-col gap-10 sm:gap-12">
          {LAYERS.map((l, i) => (
            // Layer handles its own entrance cascade + parallax — no Reveal
            // wrapper (a transformed ancestor would also fight the row's
            // per-column y MotionValues). The inter-layer connector was removed:
            // as a 72px stub it read as an accidental divider, not a pipeline.
            <Layer key={l.name} layer={l} flip={i % 2 === 1} />
          ))}
        </div>
        <Reveal>
          <div className="mt-20 rounded-xl2 border border-border bg-panel/40 p-8 sm:p-10">
            <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:justify-center sm:gap-3">
              {[["Market Mode", "reads the market"], ["Portfolio Mode", "decides"], ["Broker", "connects"]].map(([a, b], i) => (
                <div key={a} className="flex items-center gap-3">
                  <div className="flex flex-col sm:items-start"><span className="font-serif text-xl text-ink">{a}</span><span className="text-sm text-dim">{b}</span></div>
                  {i < 2 && <span className="text-2xl text-emerald/50">→</span>}
                </div>
              ))}
            </div>
            <p className="mt-7 text-center font-serif text-2xl italic text-muted">Insight, then action.</p>
          </div>
        </Reveal>
      </section>

      {/* ── Portfolio strategies ── */}
      <section id="strategies" className="scroll-mt-24 border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="03">Portfolio strategies</Eyebrow>
        <Reveal><h2 className="mt-6 max-w-2xl text-balance font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">Every model has a different engine.</h2></Reveal>
        <Reveal delay={0.05}><p className="mt-4 max-w-2xl text-lg leading-relaxed text-muted">MAVEN portfolios aren&apos;t just different baskets of stocks. Each one follows a distinct strategy, risk profile, and selection logic — some built for steadier performance, some for stronger upside, some for tighter model discipline.</p></Reveal>
        <Reveal delay={0.1}>
          <p className="mt-6 max-w-3xl rounded-xl2 border border-border bg-panel/40 p-5 text-sm leading-relaxed text-muted">
            Each portfolio is designed to solve a different job. <span className="text-ink">Defensive</span> aims to hold up better in weaker markets, <span className="text-ink">Growth</span> looks for faster compounding, <span className="text-ink">Momentum</span> follows strength, <span className="text-ink">Income</span> focuses on cash generation, <span className="text-ink">Value</span> looks for mispricing, and <span className="text-ink">Quant</span> uses MAVEN&apos;s enhanced F+ engine to rank and select stocks systematically.
          </p>
        </Reveal>

        <div className="mt-16 flex flex-col gap-14">
          {STRAT_TIERS.map((grp) => (
            <div key={grp.tier}>
              <Reveal>
                <div className="flex items-center gap-3">
                  <span className="text-[0.6rem] font-semibold uppercase tracking-label text-gold-soft">{grp.tier}</span>
                  <span className="h-px flex-1 bg-hairline" />
                </div>
              </Reveal>
              <div className="mt-5 grid gap-5 lg:grid-cols-3">
                {grp.items.map((s, i) => (
                  <Reveal key={s.name} y={16} delay={i * 0.05}>
                    <div className={`group relative flex h-full flex-col overflow-hidden rounded-xl2 border p-6 transition-[transform,border-color,background-color] duration-300 motion-safe:hover:-translate-y-1 ${s.signature ? "border-beam border-emerald/40 bg-panel/60" : "border-border bg-panel/40 hover:border-emerald/30 hover:bg-panel/60"}`}>
                      {s.signature && <div className="pointer-events-none absolute -right-14 -top-14 h-44 w-44 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.22),transparent 70%)" }} />}
                      {/* Differentiator glyph — a mono monogram anchor (mirrors the
                          app's portfolio letter marks) so the eye can scan the grid. */}
                      <div className="relative flex items-start justify-between gap-3">
                        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg border font-mono text-base tnum ${s.signature ? "border-emerald/40 bg-emerald/10 text-emerald" : "border-border bg-panel2/70 text-muted"}`} aria-hidden>{s.name[0]}</span>
                        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[0.55rem] font-semibold uppercase tracking-label ${s.signature ? "border-emerald/40 text-emerald" : "border-border text-dim"}`}>{s.tag}</span>
                      </div>
                      <div className="relative mt-3 flex items-center gap-2">
                        {s.signature && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#c9a961" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 8l4 3 5-7 5 7 4-3-2 11H5z" /></svg>}
                        <h3 className="font-serif text-xl text-ink">{s.name}</h3>
                      </div>
                      <p className="relative mt-2 text-sm italic text-emerald/90">{s.oneLine}</p>
                      <div className="relative mt-4 border-t border-hairline pt-3">
                        <p className="text-[0.5rem] font-semibold uppercase tracking-label text-dim">Best for</p>
                        <p className="mt-1 text-[0.84rem] leading-relaxed text-ink/90">{s.bestFor}</p>
                      </div>
                      {/* How it works + What it looks for collapse behind a native
                          disclosure — every word stays verbatim in the DOM (crawler-
                          readable), scannable by default, expandable on tap/click. */}
                      <details className="group/disc relative mt-4 border-t border-hairline pt-3">
                        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[0.5rem] font-semibold uppercase tracking-label text-dim transition-colors hover:text-muted [&::-webkit-details-marker]:hidden">
                          <span>How it works · What it looks for</span>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="shrink-0 transition-transform duration-300 group-open/disc:rotate-180"><path d="M6 9l6 6 6-6" /></svg>
                        </summary>
                        <div className="mt-3 space-y-3">
                          <div>
                            <p className="text-[0.5rem] font-semibold uppercase tracking-label text-dim">How it works</p>
                            <p className="mt-1 text-[0.84rem] leading-relaxed text-muted">{s.how}</p>
                          </div>
                          <div>
                            <p className="text-[0.5rem] font-semibold uppercase tracking-label text-dim">What it looks for</p>
                            <p className="mt-1 text-[0.84rem] leading-relaxed text-muted">{s.looks}</p>
                          </div>
                        </div>
                      </details>
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* selection + overlap explainers */}
        <div className="mt-16 grid gap-5 sm:grid-cols-2">
          <Reveal y={16}>
            <div className="h-full rounded-xl2 border border-border bg-panel/40 p-6">
              <h4 className="font-serif text-lg text-ink">How selection works</h4>
              <p className="mt-3 text-sm leading-relaxed text-muted">Each portfolio starts with a stock universe, applies strategy-specific filters, ranks the eligible names, sets target weights, and updates through rebalances when the strategy changes. That&apos;s why the portfolios can look different even inside the same product.</p>
            </div>
          </Reveal>
          <Reveal y={16} delay={0.05}>
            <div className="h-full rounded-xl2 border border-border bg-panel/40 p-6">
              <h4 className="font-serif text-lg text-ink">Why portfolios can overlap</h4>
              <p className="mt-3 text-sm leading-relaxed text-muted">A stock can fit more than one strategy at once. One company might be strong enough for Quality, growing fast enough for Growth, and trending well enough for Momentum. Overlap is normal when several strategies independently like the same business.</p>
            </div>
          </Reveal>
        </div>
        <Reveal y={16} delay={0.1}>
          <div className="relative mt-5 overflow-hidden rounded-xl2 border border-emerald/30 bg-panel/50 p-6 sm:p-8">
            <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.2),transparent 70%)" }} />
            <div className="relative flex items-center gap-2">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#c9a961" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 8l4 3 5-7 5 7 4-3-2 11H5z" /></svg>
              <h4 className="font-serif text-lg text-ink">Why Quant stands out</h4>
            </div>
            <p className="relative mt-3 max-w-2xl text-sm leading-relaxed text-muted">Quant is MAVEN&apos;s signature engine. It uses the enhanced F+ framework to rank, score, and select stocks systematically — making it the most disciplined and model-led portfolio in the stack.</p>
          </div>
        </Reveal>
      </section>

      {/* ── Validation ── */}
      <section ref={validationRef} className="relative border-t border-hairline py-20 sm:py-28">
        <ValidationRail target={validationRef} />
        <Eyebrow index="04">Why trust it</Eyebrow>
        <Reveal><h2 className="mt-8 max-w-2xl text-balance font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">Validated honestly. <span className="italic" style={GRAD_GOLD}>Negatives documented.</span></h2></Reveal>
        <RevealGroup className="mt-14 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {TIMELINE.map((t, i) => (
            <Item key={t.t}>
              <div className="flex items-center gap-3">
                <span className="grid h-8 w-8 place-items-center rounded-full border border-emerald/40 bg-emerald/10 font-mono text-xs text-emerald">{i + 1}</span>
                <span className="h-px flex-1 bg-border" />
              </div>
              <h3 className="mt-4 font-serif text-xl text-ink">{t.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{t.b}</p>
            </Item>
          ))}
        </RevealGroup>
        {/* Honest-claim panel: mask-image gradient wipe entrance; the drawdown
            pair ticks in as CountUp (animate()-driven → plays under OS flag).
            Figures verbatim from the backtest — no new claims. */}
        <MaskWipe>
          <GlassPanel glow="emerald" noise className="mt-16 rounded-xl2" innerClassName="p-8 sm:p-10">
            <div className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.3),transparent 70%)" }} />
            <p className="text-[0.6rem] font-semibold uppercase tracking-label text-emerald">The honest claim</p>
            <p className="mt-4 max-w-3xl font-serif text-2xl leading-snug text-ink">Enhanced F+ beat the Nifty 500 (+129.97% vs +82.17%, 2021–26) at lower drawdown (<CountUp to={14.05} suffix="%" decimals={2} className="text-emerald" /> vs <CountUp to={18.59} suffix="%" decimals={2} />), and survived covid at −13.88% versus the market&apos;s ~−38%. Its edge is risk management — earned through rigorous testing, not marketing.</p>
            <p className="mt-3 text-xs text-dim">Backtested results — not a live track record. Universe is current index constituents, so absolute returns are optimistic; the return-vs-drawdown edge is the durable signal.</p>
          </GlassPanel>
        </MaskWipe>
        <Reveal><p className="mt-16 font-serif text-xl text-muted">We tried plenty that didn&apos;t work — and kept the receipts.</p></Reveal>
        <RevealGroup className="mt-6 grid gap-4 sm:grid-cols-2">
          {REJECTED.map((r) => (
            <Item key={r.n}>
              <div className="flex items-start gap-4 rounded-xl2 border border-border bg-panel2/40 p-5">
                <span className="mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-border text-dim">
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
                </span>
                <div><p className="font-semibold text-ink">{r.n}</p><p className="mt-1 text-sm leading-relaxed text-dim">{r.w}</p></div>
              </div>
            </Item>
          ))}
        </RevealGroup>
      </section>

      {/* ── Live & forward ── */}
      <section className="border-t border-hairline py-20 text-center sm:py-28">
        <div className="flex justify-center"><Eyebrow index="05">Live &amp; forward</Eyebrow></div>
        <Reveal><div className="mt-8 flex justify-center"><LivePill>Forward paper-trade · running now</LivePill></div></Reveal>
        <Reveal><h2 className="mx-auto mt-7 max-w-3xl text-balance font-serif text-[clamp(1.9rem,4.4vw,3.2rem)] font-light leading-[1.04] tracking-[-0.015em] text-ink">Now running forward, live, on <span className="italic" style={GRAD_EMERALD}>real NSE prices.</span></h2></Reveal>
        <Reveal delay={0.05}><p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted">Real prices daily, decisions recorded at those prices, marked to market, and tracked against the Nifty 500 — an honest, ongoing, public test. No hindsight, no edits.</p></Reveal>
        {/* Converging beams frame the checklist; a one-shot sweep crosses it. */}
        <ConvergeBeams />
        <RevealGroup className="relative mx-auto mt-3 grid max-w-2xl gap-3 sm:grid-cols-2">
          {["Real NSE prices, every trading day", "Decisions stamped at the price they were made", "Marked to market, tracked vs Nifty 500", "Paper-traded — no real money at risk"].map((t) => (
            <Item key={t}>
              <div className="flex items-center gap-3 rounded-xl border border-border bg-panel2/40 p-4 text-left">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-emerald/15 text-emerald"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden><path d="M2 7.5L6 11L12 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
                <span className="tnum text-sm text-ink">{t}</span>
              </div>
            </Item>
          ))}
          <SweepOnce />
        </RevealGroup>
        {/* Closing line settles in on a gentle scale spring. */}
        <motion.p
          className="mx-auto mt-16 max-w-md font-serif text-xl italic text-muted"
          initial={{ opacity: 0, scale: 0.96 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ scale: { type: "spring", stiffness: 180, damping: 16 }, opacity: { duration: 0.5, ease: EASE } }}
        >
          Beats the market. Half the fall.
        </motion.p>
      </section>
    </div>
  );
}
