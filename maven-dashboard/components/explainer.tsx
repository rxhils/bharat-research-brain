"use client";

/**
 * "How it works" — the honest explainer, native to the Maven dashboard.
 *
 * Built with the dashboard's own tokens (bg/panel/border/emerald) + a muted
 * gold + an editorial serif for headlines. Framer Motion for scroll reveals,
 * count-ups, and the self-drawing drawdown proof. The hero "engine core" is a
 * CSS/SVG piece (no WebGL bundle in the research app). prefers-reduced-motion
 * is respected throughout.
 *
 * HONESTY CONTRACT: edge = risk (Enhanced F+ beats Nifty 500 +129.97% vs
 * +82.17% 2021-26 at lower drawdown 14.05% vs 18.59%; covid -13.88% vs market
 * ~-38%). Every figure is backtested, not a live track record; universe is
 * current constituents (survivorship → absolute returns optimistic). Broker is
 * read-only. No proprietary thresholds anywhere.
 */

import {
  motion,
  useInView,
  useReducedMotion,
  useScroll,
  animate,
  type Variants,
} from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Hydration-safe reduced-motion: returns false on the server AND the first client
 *  render (so the element tree is identical and hydration matches), then the real
 *  prefers-reduced-motion value after mount. Without this, reduced-motion users hit
 *  a hydration error wherever `reduce` changes which elements render (e.g. the
 *  ScrollProgress bar, which returns null when reduced). */
function useReducedMotionSafe(): boolean {
  const reduce = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? !!reduce : false;
}

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
      { file: "portfolios-balanced.png", cap: "Balanced" },
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
      "Watchlist is your personal tracking layer — the names you're studying before you commit. Save the stocks you care about, watch how they move, see where they overlap with MAVEN portfolios, and follow their signals without buying into a portfolio yet. Some may be future buys, some you already hold at your broker, some you just want to follow closely — MAVEN keeps the list alive with movement, overlap, and what changed today.",
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

const GRAD_GOLD: React.CSSProperties = {
  backgroundImage: "linear-gradient(180deg,#e3cb8f 0%,#c9a961 60%,#9c8348 100%)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};
const GRAD_EMERALD: React.CSSProperties = {
  backgroundImage: "linear-gradient(180deg,#6ee7b7 0%,#34d399 100%)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};

function Reveal({ children, delay = 0, y = 22, className = "" }: { children: ReactNode; delay?: number; y?: number; className?: string }) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px -12% 0px" }}
      transition={{ duration: 0.75, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

const stagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.1, delayChildren: 0.04 } } };
function RevealGroup({ children, className = "" }: { children: ReactNode; className?: string }) {
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
    show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
  };
  return <motion.div className={className} variants={v}>{children}</motion.div>;
}

function CountUp({ to, suffix = "", duration = 1.5 }: { to: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-15% 0px" });
  const reduce = useReducedMotionSafe();
  const [v, setV] = useState(reduce ? to : 0);
  useEffect(() => {
    if (!inView) return;
    if (reduce) { setV(to); return; }
    const c = animate(0, to, { duration, ease: [0.16, 1, 0.3, 1], onUpdate: setV });
    return () => c.stop();
  }, [inView, to, duration, reduce]);
  const sign = to < 0 ? "−" : to > 0 ? "+" : "";
  return <span ref={ref} className="tnum">{sign}{Math.abs(v).toFixed(0)}{suffix}</span>;
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
      <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-emerald motion-reduce:animate-none" />
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

// Live recreation of the "Portfolio Mode" Ask-AI screen (image 4).
function PortfolioAskScreen() {
  const rows = [
    { ic: "pie", t: "How did my portfolio do today?" },
    { ic: "updown", t: "Which holdings moved the most?" },
    { ic: "doc", t: "Any new filings on my holdings?" },
  ];
  return (
    <div
      className="absolute inset-0 flex flex-col px-3 pb-2 pt-7 text-left"
      style={{ backgroundColor: "#08090b", backgroundImage: "radial-gradient(85% 38% at 50% 0%, rgba(52,211,153,0.12), transparent 62%)" }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-1.5">
          <svg width="17" height="17" viewBox="0 0 100 100" fill="none" aria-hidden>
            <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="89" cy="17" r="8" fill="#34d399" />
          </svg>
          <div className="leading-none">
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-gold">Maven</div>
            <div className="mt-1 flex items-center gap-1 text-[6px] text-muted"><span className="h-1 w-1 rounded-full bg-emerald" />Indian markets · live</div>
          </div>
        </div>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden className="text-gold">
          <path d="M3 12a9 9 0 1 0 2.5-6.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M3 4v4h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M12 8v4.5l3 1.8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </div>

      <h4 className="mt-3 font-serif text-[17px] font-light leading-[1.06] text-ink">
        Good morning. What is your <span className="italic text-emerald">portfolio</span> telling you?
      </h4>
      <p className="mt-1.5 text-[7px] leading-relaxed text-muted">Grounded in your holdings, live prices &amp; filings.</p>

      <p className="mt-2 text-[8px] leading-relaxed text-ink">
        <span className="text-emerald">✦</span> Your portfolio is{" "}
        <span className="rounded bg-emerald/15 px-1 text-emerald">+1.2%</span> today —{" "}
        <span className="rounded bg-emerald/15 px-1 text-emerald">Financials lead</span>, with 2 new filings.
      </p>

      <div className="my-2 h-px bg-hairline" />

      <span className="inline-flex w-fit items-center gap-1 rounded-full border border-emerald/30 px-2 py-0.5 text-[8px]">
        <svg width="10" height="6" viewBox="0 0 16 10" aria-hidden><path d="M1 8 L5 4 L8 6 L15 1" stroke="#34d399" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
        <span className="text-muted">NIFTY</span> <span className="font-semibold text-ink">23,140</span> <span className="text-emerald">▲ 0.8%</span>
      </span>

      <div className="mt-2 divide-y divide-hairline">
        {rows.map((r) => (
          <div key={r.t} className="flex items-center justify-between py-[7px]">
            <div className="flex items-center gap-2"><RowIcon kind={r.ic} /><span className="font-serif text-[11px] text-ink">{r.t}</span></div>
            <span className="text-[10px] text-gold/80">›</span>
          </div>
        ))}
      </div>

      <div className="flex-1" />

      <div className="rounded-xl border border-gold/25 p-1.5">
        <p className="px-1 pb-1.5 pt-0.5 font-serif text-[9px] italic text-muted">Ask Maven…</p>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1 rounded-full border border-emerald/30 bg-emerald/5 px-1.5 py-[3px] text-[6px] font-bold tracking-wide text-emerald">
            <span className="h-1 w-1 rounded-full bg-emerald" />PORTFOLIO <span className="text-[5px]">▲</span>
          </span>
          <div className="flex items-center gap-1.5 text-muted">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" aria-hidden><path d="M21 11l-9 9a5 5 0 01-7-7l9-9a3.5 3.5 0 015 5l-9 9a2 2 0 01-3-3l8-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" aria-hidden><rect x="9" y="2" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="2" /><path d="M5 11a7 7 0 0014 0M12 18v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
            <span className="grid h-4 w-4 place-items-center rounded-full bg-emerald"><svg width="7" height="7" viewBox="0 0 24 24" fill="none" aria-hidden><path d="M12 19V5M5 12l7-7 7 7" stroke="#08090b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
          </div>
        </div>
      </div>

      <div className="mt-1.5 flex items-center justify-around border-t border-hairline pt-1.5">
        {[{ t: "Ask AI", a: true }, { t: "Portfolios", a: false }, { t: "Watchlist", a: false }, { t: "Broker", a: false }].map((tb) => (
          <div key={tb.t} className={`flex flex-col items-center gap-0.5 text-[6px] ${tb.a ? "text-emerald" : "text-dim"}`}>
            <TabIcon name={tb.t} active={tb.a} />{tb.t}
          </div>
        ))}
      </div>
    </div>
  );
}

// "Models, ranked." list screens (images 1-3), shown in the small gallery frames.
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

function PortfolioCard({ c }: { c: PCard }) {
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
      <div className="text-[5px] text-muted">α {c.alpha} vs NIFTY · {c.holdings} holdings</div>
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

function PortfoliosScreen({ variant }: { variant: string }) {
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
        {d.cards.map((c) => <PortfolioCard key={c.name} c={c} />)}
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

// Portfolio strategies — the plain-English engine behind each MAVEN book.
type Strat = { name: string; tag: string; oneLine: string; strategy: string; buys: string; signature?: boolean };
const STRATEGIES: Strat[] = [
  { name: "Defensive", tag: "Stable", oneLine: "Built to fall less in bad markets.",
    strategy: "Leans toward steadier businesses that tend to hold up better when markets turn weak or uncertain.",
    buys: "Prefers stocks with calmer, more resilient behaviour and lower downside than the aggressive books." },
  { name: "Growth", tag: "Aggressive", oneLine: "Higher upside, higher swings.",
    strategy: "Backs companies with real expansion potential — where revenue, earnings, or the market itself may still be compounding.",
    buys: "Looks for businesses that can outgrow the market, accepting bigger price swings to get there." },
  { name: "Momentum", tag: "Trend", oneLine: "Buy what is already strong.",
    strategy: "Follows market leadership — it aims to own the names already showing real price strength and staying power.",
    buys: "Ranks stocks by strength and favours the ones already moving well; the weaker names quietly fall out." },
  { name: "Income", tag: "Yield", oneLine: "Built to generate cash flow.",
    strategy: "Focuses on companies that can pay out more healthily and more dependably over time.",
    buys: "Seeks businesses where dividends and cash generation look sustainable — not just the highest headline yield." },
  { name: "Quant", tag: "Systematic", signature: true, oneLine: "The rules-based, signal-driven book.",
    strategy: "MAVEN's signature portfolio, powered by the enhanced F+ model — the most systematic book, run on defined signals, ranking logic, and disciplined selection rules.",
    buys: "Instead of instinct, it scores every stock through the enhanced F+ framework and holds the names that fit the model best." },
  { name: "Value", tag: "Mispriced", oneLine: "Buy good companies on sale.",
    strategy: "Looks for businesses priced below what their fundamentals seem to justify.",
    buys: "Hunts for stocks that look cheap against earnings, cash flow, or quality — while sidestepping the obvious value traps." },
  { name: "Constrained", tag: "Controlled", oneLine: "A rules book with strict limits.",
    strategy: "Follows a systematic approach, but inside tighter guardrails on weights, exposure, concentration, and risk.",
    buys: "Even a high-scoring stock can be left out if it would break a position limit or a risk rule." },
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
    { name: "Zerodha", sub: "Connect via Zerodha Kite", color: "#ef4444", connected: true, synced: "6 holdings synced", status: "Connected · Synced 2026-06-11 18:10" },
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
  if (layer.n === 2) return <PortfolioAskScreen />;
  if (layer.n === 3) return <WatchlistScreen />;
  if (layer.n === 4) return <BrokerConnectScreen />;
  return undefined;
}
function galleryMock(layer: (typeof LAYERS)[number], cap: string): ReactNode {
  if (layer.n === 2) return <PortfoliosScreen variant={cap} />;
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
  const w = small ? "w-[100px] sm:w-[150px]" : "w-[256px] sm:w-[272px]";
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

// CSS/SVG "engine core" — concentric rotating rings + emerald glow + bell-curve apex
function EngineCore() {
  return (
    <div className="relative grid aspect-square w-full max-w-[300px] place-items-center sm:max-w-[420px]">
      <div className="absolute inset-0 rounded-full" style={{ background: "radial-gradient(circle at 50% 45%,rgba(52,211,153,0.30),rgba(16,185,129,0.10) 42%,transparent 70%)" }} />
      <div className="absolute h-[78%] w-[78%] animate-spinSlow rounded-full border border-emerald/15 motion-reduce:animate-none" style={{ borderTopColor: "rgba(52,211,153,0.6)" }} />
      <div className="absolute h-[58%] w-[58%] animate-spinReverse rounded-full border border-emerald/10 motion-reduce:animate-none" style={{ borderBottomColor: "rgba(52,211,153,0.45)" }} />
      <div className="absolute h-[38%] w-[38%] animate-spinSlow rounded-full border border-dashed border-emerald/20 motion-reduce:animate-none" />
      {/* core: the Maven mark (white peaks + emerald check + dot) */}
      <div
        className="relative grid h-[37%] w-[37%] animate-floatY place-items-center rounded-[30%] border border-emerald/30 bg-[#0d0e11] motion-reduce:animate-none"
        style={{ boxShadow: "inset 0 0 44px rgba(52,211,153,0.22), 0 0 80px -6px rgba(52,211,153,0.5)" }}
      >
        <svg viewBox="0 0 100 100" className="h-[60%] w-[60%]" fill="none" role="img" aria-label="Maven">
          <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="8.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="9.5" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="89" cy="17" r="7.5" fill="#34d399" className="animate-pulseDot motion-reduce:animate-none" />
        </svg>
      </div>
    </div>
  );
}

// ───────────────────────────── drawdown proof ─────────────────────────────

const W = 740, H = 400, padL = 50, padR = 18, padT = 28, padB = 46, Y_MIN = -42;
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

function DrawdownChart() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-20% 0px" });
  const reduce = useReducedMotionSafe();
  const drawn = reduce ? true : inView;
  return (
    <div ref={ref} className="rounded-xl2 border border-border bg-panel/60 p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[0.6rem] font-semibold uppercase tracking-label text-dim">Peak-to-trough drawdown</p>
          <p className="mt-1 font-serif text-lg text-ink">The covid crash</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-2"><svg width="18" height="6"><line x1="0" y1="3" x2="18" y2="3" stroke="#5a616a" strokeWidth="2.4" strokeDasharray="4 3" /></svg>Market</span>
          <span className="flex items-center gap-2"><svg width="18" height="6"><line x1="0" y1="3" x2="18" y2="3" stroke="#34d399" strokeWidth="2.8" /></svg>Enhanced F+</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Drawdown comparison: market troughs at -38%, Enhanced F+ at -13.88%.">
        <defs>
          <linearGradient id="xdband" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d399" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#34d399" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0, -10, -20, -30, -40].map((g) => (
          <g key={g}>
            <line x1={padL} x2={W - padR} y1={ys(g)} y2={ys(g)} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
            <text x={padL - 8} y={ys(g) + 4} textAnchor="end" fill="#5a616a" fontSize="11">{g}%</text>
          </g>
        ))}
        <motion.path d={band} fill="url(#xdband)" initial={{ opacity: 0 }} animate={{ opacity: drawn ? 1 : 0 }} transition={{ duration: 1, delay: 1.3 }} />
        <motion.path d={smooth(mPts)} fill="none" stroke="#5a616a" strokeWidth={2} strokeDasharray="5 5" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: drawn ? 1 : 0 }} transition={{ duration: 1.6, ease: "easeInOut" }} />
        <motion.path d={smooth(fPts)} fill="none" stroke="#34d399" strokeWidth={3} strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: drawn ? 1 : 0 }} transition={{ duration: 1.6, ease: "easeInOut", delay: 0.35 }} />
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: drawn ? 1 : 0 }} transition={{ duration: 0.6, delay: 1.8 }}>
          <circle cx={xs(MONTHS[5])} cy={ys(MARKET[5])} r={4} fill="#0a0b0d" stroke="#5a616a" strokeWidth={2} />
          <circle cx={xs(MONTHS[5])} cy={ys(FPLUS[5])} r={4.5} fill="#0a0b0d" stroke="#34d399" strokeWidth={2.5} />
        </motion.g>
        <text x={padL} y={H - 14} fill="#5a616a" fontSize="11">Jan 2020</text>
        <text x={W - padR} y={H - 14} textAnchor="end" fill="#5a616a" fontSize="11">Dec 2020</text>
      </svg>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border bg-panel2/50 p-4">
          <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Market fell</p>
          <p className="mt-1 font-serif text-3xl text-muted">{drawn ? <CountUp to={-38} suffix="%" duration={1.6} /> : "0%"}</p>
        </div>
        <div className="rounded-xl border border-emerald/30 bg-emerald/[0.06] p-4">
          <p className="text-[0.56rem] font-semibold uppercase tracking-label text-dim">Enhanced F+ fell</p>
          <p className="mt-1 font-serif text-3xl text-emerald tnum">{drawn ? "−13.88%" : "0%"}</p>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────── sections ─────────────────────────────

function PrincipleIcon({ k }: { k: string }) {
  const c = { width: 26, height: 26, viewBox: "0 0 28 28", fill: "none", strokeWidth: 1.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, stroke: "#34d399" };
  if (k === "regime") return <svg {...c} aria-hidden><path d="M3 16 L8 14 L11 17 L14 9 L17 13 L21 6 L25 11" /><path d="M3 22 H25" opacity="0.3" /></svg>;
  if (k === "quality") return <svg {...c} aria-hidden><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="17" y="4" width="7" height="7" rx="1.5" opacity="0.6" /><rect x="4" y="17" width="7" height="7" rx="1.5" opacity="0.6" /><rect x="17" y="17" width="7" height="7" rx="1.5" /></svg>;
  return <svg {...c} aria-hidden><path d="M14 3 L23 7 V13 C23 19 19 23 14 25 C9 23 5 19 5 13 V7 Z" /><path d="M11 13.5 L13 15.5 L17.5 11" /></svg>;
}

function Layer({ layer, flip }: { layer: (typeof LAYERS)[number]; flip: boolean }) {
  return (
    <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-14">
      <div className={flip ? "lg:order-2" : ""}>
        <div className="flex items-center gap-4">
          <span className="font-serif text-4xl font-light text-emerald/30 sm:text-5xl">0{layer.n}</span>
          <div>
            <p className="text-[0.6rem] font-semibold uppercase tracking-label text-dim">Layer {layer.n} · {layer.nav}</p>
            <h3 className="font-serif text-3xl tracking-tight text-ink">{layer.name}</h3>
          </div>
        </div>
        <p className="mt-5 font-serif text-2xl italic leading-snug" style={GRAD_EMERALD}>{layer.oneLine}</p>
        <p className="mt-4 max-w-xl leading-relaxed text-muted">{layer.summary}</p>
        <div className="mt-6 inline-flex items-center gap-2 rounded-xl border border-border bg-panel2/60 px-4 py-2.5">
          <span className="text-gold">◆</span>
          <span className="text-sm text-ink">{layer.mental}</span>
        </div>
        {layer.chips && (
          <div className="mt-6">
            <p className="mb-3 text-[0.55rem] font-semibold uppercase tracking-label text-dim">{layer.chipLabel}</p>
            <div className="flex flex-wrap gap-2">
              {layer.chips.map((c) => <span key={c} className="rounded-full border border-border bg-panel/60 px-3 py-1 text-xs text-muted">{c}</span>)}
            </div>
          </div>
        )}
        {layer.note && (
          <div className="mt-6 flex items-start gap-3 rounded-xl border border-gold/15 bg-gold/[0.04] p-4">
            {layer.illustrative ? <IllustrativeTag /> : <LivePill>Read-only</LivePill>}
            <p className="text-sm leading-relaxed text-muted">{layer.note}</p>
          </div>
        )}
      </div>
      <div className={flip ? "lg:order-1" : ""}>
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
      </div>
    </div>
  );
}

// Thin scroll-progress bar — a quiet "you are here" cue (Jakub: subtle polish).
function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const reduce = useReducedMotionSafe();
  if (reduce) return null;
  return (
    <motion.div
      aria-hidden
      className="fixed inset-x-0 top-0 z-[60] h-[2px] origin-left"
      style={{ scaleX: scrollYProgress, background: "linear-gradient(90deg,#34d399,#c9a961)" }}
    />
  );
}

export function Explainer() {
  const reduce = useReducedMotionSafe();
  return (
    <div className="relative overflow-x-clip">
      <ScrollProgress />
      {/* ── Hero ── */}
      <section className="relative grid min-h-[78vh] items-center gap-10 py-16 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="pointer-events-none absolute inset-0 -z-10" style={{ background: "radial-gradient(55% 50% at 30% 40%,rgba(52,211,153,0.10),transparent 70%)" }} />
        {!reduce && (
          <motion.div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10"
            animate={{ backgroundPosition: ["0% 0%", "100% 60%", "0% 0%"] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
            style={{
              backgroundImage:
                "radial-gradient(38% 46% at 28% 42%, rgba(52,211,153,0.12), transparent 60%), radial-gradient(34% 42% at 76% 62%, rgba(16,185,129,0.10), transparent 60%)",
              backgroundSize: "200% 200%",
            }}
          />
        )}
        <div>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="mb-6 flex items-center gap-3">
            <LivePill>Indian markets · live</LivePill>
            <span className="text-[0.7rem] font-semibold uppercase tracking-label text-gold">How it works</span>
          </motion.div>
          <h1 className="font-serif text-[clamp(2.5rem,6.5vw,4.6rem)] font-light leading-[0.98] tracking-[-0.02em] text-ink">
            <motion.span className="block" initial={reduce ? { opacity: 1 } : { opacity: 0, y: "0.4em" }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}>Beats the market.</motion.span>
            <motion.span className="block italic" style={GRAD_EMERALD} initial={reduce ? { opacity: 1 } : { opacity: 0, y: "0.4em" }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.32, ease: [0.22, 1, 0.36, 1] }}>Half the fall.</motion.span>
          </h1>
          <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.6 }} className="mt-7 max-w-lg text-lg leading-relaxed text-muted">
            An AI research engine for Indian equities — built on a strategy validated across two market eras, including covid.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 0.95 }} className="mt-10">
            <div className="flex flex-wrap items-baseline gap-x-7 gap-y-3">
              <span className="flex items-baseline gap-2.5"><span className="font-serif text-4xl text-emerald tnum">+129.97%</span><span className="text-sm text-dim">Enhanced F+ · 2021–26</span></span>
              <span className="text-dim">vs</span>
              <span className="flex items-baseline gap-2.5"><span className="font-serif text-4xl text-muted tnum">+82.17%</span><span className="text-sm text-dim">Nifty 500</span></span>
            </div>
            <p className="mt-3 text-xs text-dim">Full-period total return, 2021–2026 — at lower drawdown 14.05% vs 18.59% · Backtested, not a live track record</p>
          </motion.div>
        </div>
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.2, delay: 0.3 }} className="flex justify-center">
          <EngineCore />
        </motion.div>
      </section>

      {/* ── Core idea ── */}
      <section className="border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="01">The core idea</Eyebrow>
        <div className="mt-8 grid gap-12 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-14">
          <div>
            <Reveal>
              <h2 className="max-w-xl font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">
                The edge isn&apos;t picking winners. <span className="italic" style={GRAD_GOLD}>It&apos;s not losing.</span>
              </h2>
            </Reveal>
            <div className="mt-6 max-w-lg space-y-4 text-lg leading-relaxed text-muted">
              <Reveal><p>Most strategies chase return. The Enhanced F+ engine chases survival first — and lets return follow.</p></Reveal>
              <Reveal delay={0.05}><p>Across a full crash it participated on the way up and stepped aside on the way down. The result wasn&apos;t a bigger number. It was a smaller hole.</p></Reveal>
            </div>
          </div>
          <Reveal y={30}><DrawdownChart /></Reveal>
        </div>
        <RevealGroup className="mt-16 grid gap-4 md:grid-cols-3">
          {PRINCIPLES.map((p, i) => (
            <Item key={p.k}>
              <div className="group h-full rounded-xl2 border border-border bg-panel/60 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-emerald/30 hover:shadow-[0_22px_50px_-24px_rgba(52,211,153,0.45)]">
                <div className="flex items-center justify-between">
                  <span className="grid h-11 w-11 place-items-center rounded-xl border border-border bg-panel2"><PrincipleIcon k={p.k} /></span>
                  <span className="font-serif text-2xl text-border">0{i + 1}</span>
                </div>
                <h3 className="mt-5 font-serif text-2xl text-ink">{p.t}</h3>
                <p className="mt-3 text-[0.95rem] leading-relaxed text-muted">{p.b}</p>
              </div>
            </Item>
          ))}
        </RevealGroup>
        <Reveal><p className="mx-auto mt-14 max-w-2xl text-center font-serif text-xl italic leading-relaxed text-muted">“It participates when markets rise, and steps aside when they fall. That discipline — not stock-picking magic — is the edge.”</p></Reveal>
      </section>

      {/* ── Four layers ── */}
      <section className="border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="02">The four layers</Eyebrow>
        <Reveal><h2 className="mt-8 max-w-2xl font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">One engine, four ways in.</h2></Reveal>
        <Reveal delay={0.05}><p className="mt-4 max-w-xl text-lg leading-relaxed text-muted">From reading the market to connecting your account — each layer does one job, and hands off cleanly to the next.</p></Reveal>
        <div className="mt-16 flex flex-col gap-24 sm:gap-28">
          {LAYERS.map((l, i) => <Reveal key={l.name} y={28}><Layer layer={l} flip={i % 2 === 1} /></Reveal>)}
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
      <section className="border-t border-hairline py-20 sm:py-28">
        <p className="text-[0.6rem] font-semibold uppercase tracking-label text-gold">Portfolio strategies</p>
        <Reveal><h2 className="mt-6 max-w-2xl font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">Every portfolio has a different engine.</h2></Reveal>
        <Reveal delay={0.05}><p className="mt-4 max-w-2xl text-lg leading-relaxed text-muted">MAVEN portfolios aren&apos;t just different baskets. Each one runs a different strategy, goal, and stock-selection logic — some built to protect capital, some to ride trend strength, some to follow strict model rules.</p></Reveal>
        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {STRATEGIES.map((s, i) => (
            <Reveal key={s.name} y={20} delay={(i % 2) * 0.05}>
              <div className={`group relative h-full overflow-hidden rounded-xl2 border p-6 transition-all duration-300 hover:-translate-y-0.5 ${s.signature ? "border-emerald/40 bg-panel/60 sm:col-span-2" : "border-border bg-panel/40 hover:border-emerald/30 hover:bg-panel/60"}`}>
                {s.signature && <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.22),transparent 70%)" }} />}
                <div className="relative flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {s.signature && (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#c9a961" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 8l4 3 5-7 5 7 4-3-2 11H5z" /></svg>
                    )}
                    <h3 className="font-serif text-xl text-ink">{s.name}</h3>
                  </div>
                  <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[0.58rem] font-semibold uppercase tracking-label ${s.signature ? "border-emerald/40 text-emerald" : "border-border text-dim"}`}>{s.signature ? `Signature · ${s.tag}` : s.tag}</span>
                </div>
                <p className="relative mt-2 text-sm italic text-emerald/90">{s.oneLine}</p>
                <p className="relative mt-3 max-w-xl text-sm leading-relaxed text-muted">{s.strategy}</p>
                <div className="relative mt-4 border-t border-hairline pt-3">
                  <p className="text-[0.55rem] font-semibold uppercase tracking-label text-dim">How it buys</p>
                  <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted">{s.buys}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Validation ── */}
      <section className="border-t border-hairline py-20 sm:py-28">
        <Eyebrow index="03">Why trust it</Eyebrow>
        <Reveal><h2 className="mt-8 max-w-2xl font-serif text-[clamp(1.8rem,4vw,3rem)] font-light leading-[1.05] tracking-[-0.015em] text-ink">Validated honestly. <span className="italic" style={GRAD_GOLD}>Negatives documented.</span></h2></Reveal>
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
        <Reveal y={26}>
          <div className="relative mt-16 overflow-hidden rounded-xl2 border border-emerald/25 p-8 sm:p-10" style={{ background: "linear-gradient(135deg,rgba(52,211,153,0.08),rgba(17,19,22,0.5) 60%)" }}>
            <div className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.3),transparent 70%)" }} />
            <p className="text-[0.6rem] font-semibold uppercase tracking-label text-emerald">The honest claim</p>
            <p className="mt-4 max-w-3xl font-serif text-2xl leading-snug text-ink">Enhanced F+ beat the Nifty 500 (+129.97% vs +82.17%, 2021–26) at lower drawdown (14.05% vs 18.59%), and survived covid at −13.88% versus the market&apos;s ~−38%. Its edge is risk management — earned through rigorous testing, not marketing.</p>
            <p className="mt-3 text-xs text-dim">Backtested results — not a live track record. Universe is current index constituents, so absolute returns are optimistic; the return-vs-drawdown edge is the durable signal.</p>
          </div>
        </Reveal>
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
        <div className="flex justify-center"><Eyebrow index="04">Live &amp; forward</Eyebrow></div>
        <Reveal><div className="mt-8 flex justify-center"><LivePill>Forward paper-trade · running now</LivePill></div></Reveal>
        <Reveal><h2 className="mx-auto mt-7 max-w-3xl font-serif text-[clamp(1.9rem,4.4vw,3.2rem)] font-light leading-[1.04] tracking-[-0.015em] text-ink">Now running forward, live, on <span className="italic" style={GRAD_EMERALD}>real NSE prices.</span></h2></Reveal>
        <Reveal delay={0.05}><p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted">Real prices daily, decisions recorded at those prices, marked to market, and tracked against the Nifty 500 — an honest, ongoing, public test. No hindsight, no edits.</p></Reveal>
        <RevealGroup className="mx-auto mt-12 grid max-w-2xl gap-3 sm:grid-cols-2">
          {["Real NSE prices, every trading day", "Decisions stamped at the price they were made", "Marked to market, tracked vs Nifty 500", "Paper-traded — no real money at risk"].map((t) => (
            <Item key={t}>
              <div className="flex items-center gap-3 rounded-xl border border-border bg-panel2/40 p-4 text-left">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-emerald/15 text-emerald"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden><path d="M2 7.5L6 11L12 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
                <span className="text-sm text-ink">{t}</span>
              </div>
            </Item>
          ))}
        </RevealGroup>
        <Reveal><p className="mx-auto mt-16 max-w-md font-serif text-xl italic text-muted">Beats the market. Half the fall.</p></Reveal>
      </section>
    </div>
  );
}
