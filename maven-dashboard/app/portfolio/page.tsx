import type { Metadata } from "next";
import {
  getAccount, getEquityCurve, getExposure, getHoldings, getKeyStats, getLivePortfolios,
} from "@/lib/data";
import { Empty } from "@/components/client";
import { GlassPanel } from "@/components/glass-panel";
import { CountUp, SectionEyebrow } from "@/components/motion";
import { PortfolioRace } from "@/components/portfolio-race";
import { PortfolioTabs, type BookPanelData } from "@/components/portfolio-tabs";
import type { EquityPoint, ExposureState, Holding, KeyStats, PaperAccount } from "@/lib/types";

export const dynamic = "force-dynamic";

const title = "Three Live Paper Portfolios: Returns and Risk Metrics";
const description =
  "Track three live paper portfolios (Enhanced F+, Defensive, Concentrated) with equity curves vs Nifty 500 TRI, drawdown, Sharpe, exposure, and full holdings.";
const url = "https://www.trymaven.in/portfolio";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

// "Quant" is shown as its strategy name on the public site.
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

// One honest color identity per book (same on the race chart and the desk):
// emerald = Enhanced F+, slate = Defensive, gold = Concentrated. Benchmark
// stays dim slate inside the chart itself.
const BOOK_COLOR: Record<string, string> = { Defensive: "#94a3b8", Concentrated: "#c9a961" };
const colorOf = (n: string) => BOOK_COLOR[n] ?? "#34d399";

type Panel = {
  name: string; acct: PaperAccount; curve: EquityPoint[];
  exposure: ExposureState; stats: KeyStats; holdings: Holding[];
};

function HeroStat({ label, children, hint }: {
  label: string; children: React.ReactNode; hint?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-dim">{label}</div>
      <div className="mt-1 font-mono text-2xl tnum text-ink">{children}</div>
      {hint && <div className="mt-0.5 text-[11px] text-dim">{hint}</div>}
    </div>
  );
}

export default async function Portfolio() {
  const ports = await getLivePortfolios();
  const panels = await Promise.all(
    ports.map(async (p): Promise<Panel> => {
      const [acct, curve, exposure, stats, holdings] = await Promise.all([
        getAccount(p.id), getEquityCurve(p.id), getExposure(p.id), getKeyStats(p.id), getHoldings(p.id),
      ]);
      return { name: p.name, acct, curve, exposure, stats, holdings };
    }),
  );

  // Combined hero figures — pure arithmetic over the per-book stats already
  // loaded above (no new queries, no invented numbers). Blended alpha is the
  // capital-weighted mean of each book's alpha vs the Nifty 500 TRI.
  const combinedEquity = panels.reduce((s, p) => s + p.acct.currentEquity, 0);
  const combinedStart = panels.reduce((s, p) => s + p.acct.startingCapital, 0);
  const combinedReturnPct = combinedStart > 0 ? (combinedEquity / combinedStart - 1) * 100 : 0;
  const blendedAlphaPct = combinedStart > 0
    ? panels.reduce((s, p) => s + p.stats.alphaVsNifty500Pct * p.acct.startingCapital, 0) / combinedStart
    : 0;

  const raceBooks = panels
    .filter((p) => p.curve.length >= 2)
    .map((p) => ({ name: displayName(p.name), color: colorOf(p.name), curve: p.curve }));

  const books: BookPanelData[] = panels.map((p) => ({
    ...p, displayName: displayName(p.name), color: colorOf(p.name),
  }));

  return (
    <div className="space-y-8">
      {/* ---- hero band: the experiment, its combined figures, and The Race ---- */}
      <section className="relative">
        {/* light source behind the panel, never on it */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 left-1/2 h-72 w-[min(46rem,90vw)] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(52,211,153,0.09),transparent)]"
        />
        <GlassPanel as="div" glow="emerald" noise innerClassName="p-6 sm:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.15fr_auto] lg:items-end">
            <div>
              <SectionEyebrow>Paper portfolios · live</SectionEyebrow>
              <h1 className="mt-3 font-serif text-[clamp(2.25rem,1rem+4.5vw,4.25rem)] leading-[1.02] tracking-[-0.02em] text-ink">
                Three books.
                <br />
                One risk engine.
              </h1>
              <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-muted">
                Enhanced F+ trades vol-adjusted momentum; Defensive trades low-volatility with
                sooner, harder de-risking; Concentrated runs a top-10 high-conviction book. All
                three ₹10L paper, side by side.
              </p>
            </div>

            {panels.length > 0 && (
              // glass hairline band: the combined figures are the hero's most
              // important numbers, so they get the gradient p-px + inset top
              // highlight treatment (no backdrop-filter — stays in blur budget).
              <div className="rounded-2xl bg-gradient-to-b from-white/[0.14] via-white/[0.05] to-transparent p-px shadow-[0_0_34px_-14px_rgba(52,211,153,0.3)]">
                <div className="grid grid-cols-2 gap-x-8 gap-y-5 rounded-[calc(1rem-1px)] bg-white/[0.03] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.15)] sm:grid-cols-3 lg:grid-cols-1 lg:gap-y-6 lg:p-6">
                  <HeroStat label="Combined equity" hint={`across ${panels.length} paper books`}>
                    <CountUp to={combinedEquity} prefix="₹" decimals={0} />
                  </HeroStat>
                  <HeroStat label="Combined return">
                    <CountUp
                      to={combinedReturnPct}
                      prefix={combinedReturnPct >= 0 ? "+" : ""}
                      suffix="%"
                      decimals={2}
                    />
                  </HeroStat>
                  <HeroStat label="Blended alpha" hint="capital-weighted, vs Nifty 500 TRI">
                    <CountUp
                      to={blendedAlphaPct}
                      prefix={blendedAlphaPct >= 0 ? "+" : ""}
                      suffix="%"
                      decimals={2}
                    />
                  </HeroStat>
                </div>
              </div>
            )}
          </div>

          {raceBooks.length > 0 && (
            <div className="mt-10">
              <PortfolioRace books={raceBooks} />
              <p className="mt-2 text-[11px] text-dim">
                Normalized to % return since each book&apos;s inception · paper-traded · Nifty 500
                TRI benchmark.
              </p>
            </div>
          )}
        </GlassPanel>
      </section>

      {/* ---- book desk: one tab per book, full-width detail ---- */}
      {books.length > 0 ? (
        <section>
          <div className="mb-4">
            <SectionEyebrow>Book desk</SectionEyebrow>
            <h2 className="mt-2 font-serif text-[clamp(1.5rem,1rem+1.5vw,2.25rem)] tracking-[-0.01em] text-ink">
              Every book, in full.
            </h2>
          </div>
          <PortfolioTabs books={books} />
        </section>
      ) : (
        <Empty />
      )}

      <p className="px-1 pt-2 text-xs text-dim">
        Research tool. Not investment advice. Paper-traded results, not real money.
        {panels[0] && (
          <span> · Engine {panels[0].acct.engineVersion} · read-only broker sync</span>
        )}
      </p>
    </div>
  );
}
