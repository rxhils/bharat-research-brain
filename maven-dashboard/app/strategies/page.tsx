"use client";

// Strategies overview — the live, fully-backtested portfolios (see the LIVE array)
// with their EXACT validated figures, and the rest shown as "coming soon — in
// validation" with NO numbers. Static content only; no DB. Numbers must match the
// validated figures verbatim — nothing invented, nothing rounded differently.

import { motion } from "framer-motion";
import { CountUp, EASE, useReducedMotionSafe } from "@/components/motion";
import { type ReactNode } from "react";

function Reveal({ children, y = 16, delay = 0 }: { children: ReactNode; y?: number; delay?: number }) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      initial={reduce ? { opacity: 1 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

type Stat = { label: string; value: number; prefix?: string; suffix?: string; decimals?: number; tone?: "emerald" | "amber"; note?: string };
type Live = { name: string; sub?: string; flagship?: boolean; oneLiner: string; stats: Stat[]; edge: string; forWho: string; period: string };

const LIVE: Live[] = [
  {
    name: "Quant", sub: "Enhanced F+", flagship: true,
    oneLiner: "Balanced growth with strong risk management.",
    stats: [
      { label: "Total return", value: 129.97, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 14.05, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 14, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Beat the Nifty 500 — +129.97% vs +82.17% — at a lower drawdown.",
    forWho: "Investors who want growth with crash protection.",
    period: "2021–26",
  },
  {
    name: "Defensive",
    oneLiner: "Safety-first. Smaller drops, smoother ride.",
    stats: [
      { label: "Total return", value: 84.61, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 17.63, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 9, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Lower drawdown than Quant in 7 of 8 test windows, with better COVID survival — it trades a little return for less risk.",
    forWho: "Cautious investors prioritising capital protection.",
    period: "2021–26",
  },
  {
    name: "Concentrated",
    oneLiner: "Enhanced F+, concentrated to the top 10.",
    stats: [
      { label: "Total return", value: 152.66, prefix: "+", suffix: "%", decimals: 2, tone: "emerald" },
      { label: "Max drawdown", value: 12.63, suffix: "%", decimals: 2, tone: "amber" },
      { label: "COVID drawdown", value: 21, prefix: "~", suffix: "%", decimals: 0, tone: "emerald", note: "vs market ~38%" },
    ],
    edge: "Highest return of the three — +152.66% vs the index's +82.17% — by holding only the top 10. Same crash brakes as Quant, but more single-name risk (a deeper ~21% COVID drawdown).",
    forWho: "Investors who want maximum conviction and upside, and can accept more concentration risk.",
    period: "2021–26",
  },
];

// Spelled-out count derived from LIVE so the subheadline can never drift from
// the number of cards actually rendered.
const COUNT_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"] as const;
const LIVE_COUNT_WORD = COUNT_WORDS[LIVE.length] ?? String(LIVE.length);

const SOON: { name: string; style: string }[] = [
  { name: "Growth", style: "Higher-upside names with faster compounding potential." },
  { name: "Core", style: "A steady, benchmark-aware long-term base." },
  { name: "Value", style: "Undervalued businesses priced below their fundamentals." },
  { name: "Income", style: "Dependable cash generation and sustainable payouts." },
  { name: "Momentum", style: "Market leaders already showing trend strength." },
  { name: "Quality", style: "Durable, financially strong businesses." },
  { name: "Constrained", style: "Rules-based selection inside tighter risk limits." },
];

function Crown() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#c9a961" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 8l4 3 5-7 5 7 4-3-2 11H5z" />
    </svg>
  );
}

function LiveCard({ p, delay }: { p: Live; delay: number }) {
  const reduce = useReducedMotionSafe();
  return (
    <Reveal y={18} delay={delay}>
      <motion.div
        whileHover={reduce ? undefined : { y: -6, scale: 1.012 }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
        className={`group relative h-full overflow-hidden rounded-xl2 border p-6 transition-colors duration-300 sm:p-7 ${p.flagship ? "border-emerald/40 bg-panel/60" : "border-border bg-panel/40 hover:border-emerald/30 hover:bg-panel/60"}`}
      >
        {/* Static radial glow — a single flagship card, not a looping breathe.
            An infinite pulse/glow on a status-ish element is slop; the depth
            reads on its own. */}
        {p.flagship && <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-60 blur-3xl" style={{ background: "radial-gradient(circle,rgba(52,211,153,0.2),transparent 70%)" }} />}
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {p.flagship && <Crown />}
            <div>
              <h3 className="font-serif text-2xl text-ink">{p.name}</h3>
              {p.sub && <p className="text-xs text-gold-soft">{p.sub}</p>}
            </div>
          </div>
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald/40 bg-emerald/10 px-2.5 py-0.5 text-[0.6rem] font-semibold uppercase tracking-label text-emerald">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald" />Live
          </span>
        </div>
        <p className="relative mt-3 text-sm italic text-emerald/90">{p.oneLiner}</p>
        <div className="relative mt-5 grid grid-cols-3 gap-3">
          {p.stats.map((s) => (
            <div key={s.label} className="rounded-lg border border-hairline bg-bg/40 px-3 py-2.5">
              <div className="text-[0.55rem] uppercase tracking-label text-dim">{s.label}</div>
              <div className={`mt-1 font-mono text-lg font-semibold ${s.tone === "amber" ? "text-amber" : "text-emerald"}`}>
                <CountUp to={s.value} prefix={s.prefix} suffix={s.suffix} decimals={s.decimals ?? 2} />
              </div>
              {s.note && <div className="mt-0.5 text-[0.55rem] text-dim">{s.note}</div>}
            </div>
          ))}
        </div>
        <p className="relative mt-4 text-sm leading-relaxed text-muted">{p.edge}</p>
        <div className="relative mt-4 border-t border-hairline pt-3">
          <p className="text-[0.55rem] font-semibold uppercase tracking-label text-dim">For</p>
          <p className="mt-1 text-sm text-ink/90">{p.forWho}</p>
        </div>
        <p className="relative mt-4 text-[0.6rem] text-dim">Backtested ({p.period}) — not a live track record.</p>
      </motion.div>
    </Reveal>
  );
}

function SoonCard({ name, style, delay }: { name: string; style: string; delay: number }) {
  // Deliberately static + dimmed: these are not clickable, so no hover-lift or
  // press (a lift would imply interactivity that isn't there). The muted palette
  // is the affordance difference from the live cards — quiet, not inert-looking.
  return (
    <Reveal y={14} delay={delay}>
      <div className="h-full rounded-xl2 border border-dashed border-hairline bg-panel/20 p-5 opacity-75">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-serif text-lg text-muted">{name}</h3>
          <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[0.55rem] font-medium uppercase tracking-label text-dim">Coming soon</span>
        </div>
        <p className="mt-2 text-[0.82rem] leading-relaxed text-dim">{style}</p>
        <p className="mt-3 text-[0.55rem] uppercase tracking-label text-dim/70">In validation</p>
      </div>
    </Reveal>
  );
}

export default function StrategiesPage() {
  return (
    <div className="pt-6">
      <header className="pb-2">
        <p className="text-[0.6rem] font-semibold uppercase tracking-label text-gold">AI Portfolios</p>
        <h1 className="mt-4 font-serif text-[clamp(2rem,5vw,3.2rem)] font-light leading-[1.02] tracking-[-0.02em] text-ink">Models, ranked.</h1>
        <p className="mt-4 max-w-2xl text-lg leading-relaxed text-muted">{LIVE_COUNT_WORD} {LIVE.length === 1 ? "strategy is" : "strategies are"} live and fully backtested. The rest are in validation — no numbers until they&apos;ve earned them.</p>
      </header>

      <section className="mt-10">
        <div className="flex items-center gap-3">
          <span className="text-[0.6rem] font-semibold uppercase tracking-label text-gold-soft">Live &amp; validated</span>
          <span className="h-px flex-1 bg-hairline" />
        </div>
        <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {LIVE.map((p, i) => <LiveCard key={p.name} p={p} delay={i * 0.06} />)}
        </div>
      </section>

      <section className="mt-14">
        <div className="flex items-center gap-3">
          <span className="text-[0.6rem] font-semibold uppercase tracking-label text-gold-soft">In validation</span>
          <span className="h-px flex-1 bg-hairline" />
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SOON.map((s, i) => <SoonCard key={s.name} name={s.name} style={s.style} delay={(i % 3) * 0.05} />)}
        </div>
      </section>

      <p className="mt-12 max-w-3xl text-xs leading-relaxed text-dim">
        Backtested results — not a live track record. Based on current index constituents, so absolute
        returns are optimistic. Past performance does not guarantee future results. For personal research
        and educational purposes only; not investment advice.
      </p>
    </div>
  );
}
