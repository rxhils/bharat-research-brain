import Link from "next/link";
import type { Metadata } from "next";

import { getAccount, getEquityCurve, getHoldings, getLivePortfolios } from "@/lib/data";
import { EquityChart, HoldingsTable } from "@/components/client";
import { GRAD_EMERALD, GRAD_GOLD } from "@/components/explainer";
import { GlassPanel } from "@/components/glass-panel";
import { ScrollProgress } from "@/components/scroll-progress";
import { CountUp, Reveal, SectionEyebrow } from "@/components/motion";
import { PipelineDiagram } from "@/components/portfolio-mode/pipeline-diagram";
import { StyleGrid, type StyleItem, type StyleTier } from "@/components/portfolio-mode/style-grid";
import type { EquityPoint, Holding, PaperAccount } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Portfolio Mode & Broker Connection Explained",
  description:
    "Understand how Maven's multi-style portfolio engine works, what live vs backtested vs illustrative numbers mean, and how read-only broker connection will work.",
  alternates: {
    canonical: "https://www.trymaven.in/portfolio-mode",
  },
  // page is hidden from nav + sitemap while it's rebuilt; keep crawlers out too
  robots: { index: false, follow: false },
  openGraph: {
    title: "Portfolio Mode & Broker Connection Explained",
    description:
      "Understand how Maven's multi-style portfolio engine works, what live vs backtested vs illustrative numbers mean, and how read-only broker connection will work.",
    url: "https://www.trymaven.in/portfolio-mode",
  },
  twitter: {
    title: "Portfolio Mode & Broker Connection Explained",
    description:
      "Understand how Maven's multi-style portfolio engine works, what live vs backtested vs illustrative numbers mean, and how read-only broker connection will work.",
  },
};

// "Quant" is shown as its strategy name on the public site (matches app/portfolio/page.tsx).
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

const STYLE_TIERS: StyleTier[] = [
  { tier: "Stable", items: [
    { name: "Core", oneLine: "The long-term base portfolio." },
    { name: "Quality", oneLine: "Strong businesses, chosen for durability." },
    { name: "Defensive", oneLine: "Built to fall less in bad markets." },
  ] },
  { tier: "Balanced", items: [
    { name: "Growth", oneLine: "Higher upside, higher volatility." },
    { name: "Momentum", oneLine: "Follows market leadership and price strength." },
    { name: "Income", oneLine: "Built to generate cash flow." },
  ] },
  { tier: "Bold", items: [
    { name: "Quant", oneLine: "Maven's signature rules-based model.", signature: true },
    { name: "Value", oneLine: "Looks for businesses priced below what they're worth." },
    { name: "Contrarian", oneLine: "Backs quality when sentiment gets too weak." },
  ] },
];

const BROKER_LIST = ["Zerodha", "Groww", "Upstox", "Angel One", "HDFC Sky", "Anand Rathi"];

// The five chassis facts every style shares — surfaced as a spec row.
const CHASSIS_SPECS = [
  "Quality gate",
  "Graded cash sleeve",
  "15% breakdown stop",
  "Quarterly rebalance",
  "Interest on idle cash",
];

function StatusTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full border border-dashed border-border px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-dim">
      {children}
    </span>
  );
}

export default async function PortfolioModePage() {
  // Graceful when the DB is empty or unreachable: every fetch degrades to
  // "no live book" rather than a crash — the proof panel then says so honestly.
  const ports = await getLivePortfolios().catch(() => [] as { id: number; name: string }[]);
  const liveCount = ports.length;
  const example = ports[0] ?? null;

  let acct: PaperAccount | null = null;
  let curve: EquityPoint[] = [];
  let holdings: Holding[] = [];
  if (example) {
    try {
      [acct, curve, holdings] = await Promise.all([
        getAccount(example.id),
        getEquityCurve(example.id),
        getHoldings(example.id),
      ]);
    } catch {
      acct = null;
      curve = [];
      holdings = [];
    }
  }

  const returnPct = acct && acct.startingCapital > 0 ? (acct.currentEquity / acct.startingCapital - 1) * 100 : null;
  const inceptionLabel = acct
    ? new Date(acct.inceptionDate).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
    : null;
  const accent =
    example?.name === "Defensive" ? "#94a3b8" : example?.name === "Concentrated" ? "#c9a961" : "#34d399";
  // Truthful status per style, sourced only from real props / verbatim figures:
  // - Quant (Enhanced F+): the live paper book — dated from acct.inceptionDate
  //   (falls back to its backtested status if the DB is offline).
  // - Defensive: has verbatim backtested figures on /strategies + /backtest.
  // - everything else: not live, no per-style figures yet → Planned.
  const statusFor = (rawName: string): StyleItem["status"] => {
    if (rawName === "Quant") {
      return inceptionLabel
        ? { label: `Live paper — since ${inceptionLabel}`, tone: "live" }
        : { label: "Backtested 2021–26", tone: "backtested" };
    }
    if (rawName === "Defensive") return { label: "Backtested 2021–26", tone: "backtested" };
    return { label: "Planned", tone: "planned" };
  };
  const tiers: StyleTier[] = STYLE_TIERS.map((t) => ({
    ...t,
    items: t.items.map((s) => ({ ...s, status: statusFor(s.name), name: displayName(s.name) })),
  }));

  return (
    <div className="space-y-14 pb-12 pt-2">
      <ScrollProgress />

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <Reveal>
        <SectionEyebrow>How Maven works</SectionEyebrow>
        <h1 className="mt-3 max-w-3xl text-balance font-serif text-[clamp(2.25rem,1rem+4.5vw,5rem)] leading-[1.02] tracking-[-0.02em] text-ink">
          Portfolio Mode &amp; Broker connection, explained.
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-muted">
          How research turns into a portfolio, and what &ldquo;connecting your broker&rdquo; will
          mean once it&apos;s available.
        </p>
      </Reveal>

      {/* ── 01 · Live proof — elevated directly under the intro ────────── */}
      <Reveal delay={0.06}>
        <GlassPanel glow="emerald" noise>
          <div className="relative p-6 sm:p-7">
            {/* radial glow BEHIND the content — light source, not a coat of paint */}
            <div
              aria-hidden
              className="pointer-events-none absolute -top-28 left-1/2 h-64 w-[34rem] max-w-full -translate-x-1/2 rounded-full bg-emerald/10 blur-3xl"
            />
            <div className="relative">
              <SectionEyebrow number="01">Proof first</SectionEyebrow>
              <h3 className="mt-2 font-serif text-[clamp(1.35rem,1rem+1.2vw,1.6rem)] text-ink">
                See it running{example ? ` — ${displayName(example.name)}` : ""}
              </h3>
              {acct && returnPct != null ? (
                <>
                  <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
                    {liveCount === 1
                      ? "One live paper book is running today."
                      : `${liveCount} live paper books are running today.`}{" "}
                    Real prices, real decisions, no real money.
                  </p>
                  <div className="brand-motion mt-5 grid grid-cols-2 gap-x-4 gap-y-5 border-t border-hairline pt-5 sm:grid-cols-3">
                    <div>
                      <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">Book value</div>
                      <div className="mt-1 font-mono text-xl text-ink sm:text-2xl">
                        <CountUp to={acct.currentEquity} prefix="₹" decimals={0} />
                      </div>
                    </div>
                    <div>
                      <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">
                        Since {inceptionLabel ?? "inception"}
                      </div>
                      <div className="mt-1 font-mono text-xl text-ink sm:text-2xl">
                        <CountUp to={returnPct} prefix={returnPct >= 0 ? "+" : ""} suffix="%" decimals={1} />
                      </div>
                    </div>
                    <div>
                      <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">Live paper books</div>
                      <div className="mt-1 font-mono text-xl text-ink sm:text-2xl">
                        <CountUp to={liveCount} decimals={0} duration={0.9} />
                      </div>
                    </div>
                  </div>
                  <div className="mt-6 grid gap-6 lg:grid-cols-2">
                    <div>
                      <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-dim">
                        Equity curve — {displayName(example!.name)} vs Nifty 500 TRI
                      </div>
                      <EquityChart data={curve} seriesName={displayName(example!.name)} accent={accent} />
                    </div>
                    <div>
                      <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-dim">
                        Current holdings — live, real positions
                      </div>
                      <HoldingsTable rows={holdings} compact />
                    </div>
                  </div>
                  <Link
                    href="/portfolio"
                    className="group mt-5 inline-flex items-center gap-1.5 text-xs text-emerald focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60"
                  >
                    <span className="border-b border-emerald/0 pb-px transition-colors duration-300 group-hover:border-emerald/60">
                      See every live book in full
                    </span>
                    <span aria-hidden className="motion-safe:transition-transform motion-safe:duration-300 motion-safe:group-hover:translate-x-0.5">
                      &rarr;
                    </span>
                  </Link>
                </>
              ) : (
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
                  No live paper book is connected in this environment right now. When the research
                  database is online, this panel shows the live equity curve against the Nifty 500
                  TRI and the current holdings — real prices, real decisions, no real money. Nothing
                  is simulated to fill the gap.
                </p>
              )}
            </div>
          </div>
        </GlassPanel>
      </Reveal>

      {/* ── Chapter one · Portfolio Mode ───────────────────────────────── */}
      <Reveal>
        <h2
          className="font-serif text-[clamp(1.75rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.015em]"
          style={GRAD_EMERALD}
        >
          Portfolio Mode
        </h2>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">
          Turns market intelligence into portfolio action — holdings, weights, cash level,
          rebalance decisions, risk control — all driven by the same validated Enhanced F+
          engine. Each style is the same engine with a different tilt, not a separate product.
        </p>
      </Reveal>

      {/* ── 02 · One engine, many tilts ────────────────────────────────── */}
      <Reveal delay={0.05}>
        <GlassPanel noise>
          <div className="p-6 sm:p-7">
            <SectionEyebrow number="02">One engine, many tilts</SectionEyebrow>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              Every style runs the same risk-managed chassis: a quality gate, a graded cash sleeve
              that de-risks on a weekly check, a 15% cut-on-breakdown stop, a full rebalance every
              quarter, and interest earned on idle cash. What changes between styles is the tilt —
              which signal it ranks by, how hard it de-risks, and how many names it holds. Most
              strategies chase return. The Enhanced F+ engine chases survival first — and lets
              return follow.
            </p>
            <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-hairline pt-4">
              {CHASSIS_SPECS.map((s) => (
                <span
                  key={s}
                  className="tnum inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.1em] text-muted"
                >
                  <span aria-hidden className="h-1 w-1 rounded-full bg-emerald" />
                  {s}
                </span>
              ))}
            </div>
          </div>
        </GlassPanel>
      </Reveal>

      {/* ── 03 · The pipeline — signature moment ───────────────────────── */}
      <Reveal>
        <SectionEyebrow number="03">The pipeline</SectionEyebrow>
        <h3 className="mt-2 font-serif text-[clamp(1.35rem,1rem+1.2vw,1.6rem)] text-ink">
          How a portfolio gets built
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Four stages turn the whole market into a weighted portfolio — then two clocks and one
          hard rule keep it honest.
        </p>
      </Reveal>
      <PipelineDiagram />

      {/* ── 04 · Three kinds of numbers ────────────────────────────────── */}
      <Reveal>
        <SectionEyebrow number="04">Reading the numbers</SectionEyebrow>
        <h3 className="mt-2 font-serif text-[clamp(1.35rem,1rem+1.2vw,1.6rem)] text-ink">
          Three different kinds of numbers
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          You&apos;ll see performance figures in three places on Maven — they answer different
          questions, and it&apos;s worth knowing which is which.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {/* Backtested — neutral/slate accent; the historical simulation. */}
          <div className="rounded-xl2 bg-gradient-to-b from-white/[0.14] via-white/[0.05] to-transparent p-px">
            <div className="flex h-full flex-col rounded-[inherit] bg-white/[0.03] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
                Backtested
              </div>
              <div className="mt-1.5 font-mono text-lg tnum text-ink">2021–26</div>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                A historical simulation over 2021–26, shown on Strategies. Not a live track record.
              </p>
            </div>
          </div>
          {/* Live paper-trade — emerald accent; the real, forward-tracked book. */}
          <div className="rounded-xl2 bg-gradient-to-b from-emerald/30 via-white/[0.05] to-transparent p-px">
            <div className="flex h-full flex-col rounded-[inherit] bg-white/[0.03] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald">
                Live paper-trade
              </div>
              <div className="mt-1.5 font-mono text-lg tnum text-emerald">
                {inceptionLabel ? `since ${inceptionLabel}` : "forward-tracked"}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                Real, forward-tracked on real NSE prices, updated on a real schedule. No real money
                at risk. Shown on Portfolio.
              </p>
            </div>
          </div>
          {/* Illustrative — dashed dim; deliberately no anchor figure (no data). */}
          <div className="flex h-full flex-col rounded-xl2 border border-dashed border-border bg-white/[0.02] p-4">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-dim">
              Illustrative
            </div>
            <div className="mt-1.5 font-mono text-lg tnum text-dim">demo only</div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Demo figures used to preview a style before it has a real track record. Always
              marked illustrative wherever shown.
            </p>
          </div>
        </div>
      </Reveal>

      {/* ── 05 · The style lineup ──────────────────────────────────────── */}
      <Reveal>
        <SectionEyebrow number="05">The lineup</SectionEyebrow>
        <h3 className="mt-2 font-serif text-[clamp(1.35rem,1rem+1.2vw,1.6rem)] text-ink">
          Nine tilts, one engine
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Nine named tilts on the same engine, grouped by how much conviction they take —
          Stable, Balanced, Bold. Not every style is live yet; each earns its place by clearing
          the same validation bar the flagship engine did.
        </p>
      </Reveal>
      <div>
        <StyleGrid tiers={tiers} />
        <Reveal delay={0.1}>
          <Link
            href="/strategies"
            className="group mt-4 inline-flex items-center gap-1.5 text-xs text-emerald focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60"
          >
            <span className="border-b border-emerald/0 pb-px transition-colors duration-300 group-hover:border-emerald/60">
              See backtested figures for every strategy
            </span>
            <span aria-hidden className="motion-safe:transition-transform motion-safe:duration-300 motion-safe:group-hover:translate-x-0.5">
              &rarr;
            </span>
          </Link>
        </Reveal>
      </div>

      {/* ── Chapter two · Broker connection ────────────────────────────── */}
      <div aria-hidden className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <Reveal>
        <SectionEyebrow>Chapter two — the planned layer</SectionEyebrow>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h2
            className="font-serif text-[clamp(1.75rem,1rem+2.5vw,3rem)] leading-[1.05] tracking-[-0.015em]"
            style={GRAD_GOLD}
          >
            Broker connection
          </h2>
          <StatusTag>Not yet available</StatusTag>
        </div>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">
          Connects Maven to a real account — Zerodha, Groww, Upstox, Angel One, HDFC Sky, Anand
          Rathi — read-only, to sync and compare your holdings against the models. Execution is
          the last layer, and it stays human-approved.
        </p>
      </Reveal>

      <Reveal delay={0.05}>
        <GlassPanel glow="gold" noise>
          <div className="p-6 sm:p-7">
            <SectionEyebrow>Design principle</SectionEyebrow>
            <p className="mt-3 font-serif text-xl leading-snug text-ink sm:text-2xl">
              Read-only. No trading.
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              Maven never places, modifies, or cancels an order — not today, and not in any future
              version of this feature. Once available, connecting a broker will only ever show you
              where your real holdings differ from a model portfolio; what to do about that gap
              stays entirely your decision, made in your own broker&apos;s app.
            </p>
            <div className="mt-5 grid grid-cols-2 gap-2.5 border-t border-hairline pt-5 sm:grid-cols-3">
              {BROKER_LIST.map((b) => (
                <div
                  key={b}
                  className="flex items-center justify-between gap-2 rounded-lg border border-border bg-white/[0.03] px-3 py-2.5"
                >
                  <span className="text-sm text-ink">{b}</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-dim">Planned</span>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>
      </Reveal>

      {/* ── Disclaimer ─────────────────────────────────────────────────── */}
      <Reveal delay={0.05}>
        <p className="max-w-2xl border-t border-hairline pt-5 text-xs leading-relaxed text-dim">
          Research tool. Not investment advice. Paper-traded results, not real money. No
          order-placement code exists anywhere in Maven, today or planned. Not registered with
          SEBI.
        </p>
      </Reveal>
    </div>
  );
}
