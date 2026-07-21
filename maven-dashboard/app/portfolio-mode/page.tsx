import Link from "next/link";
import { getAccount, getEquityCurve, getHoldings, getLivePortfolios } from "@/lib/data";
import { Card, EquityChart, HoldingsTable } from "@/components/client";
import { GRAD_EMERALD, GRAD_GOLD, Reveal } from "@/components/explainer";

export const dynamic = "force-dynamic";

// "Quant" is shown as its strategy name on the public site (matches app/portfolio/page.tsx).
const displayName = (n: string) => (n === "Quant" ? "Enhanced F+" : n);

const STYLE_TIERS: { tier: string; items: { name: string; oneLine: string; signature?: boolean }[] }[] = [
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

function StatusTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full border border-dashed border-gold/30 px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-gold-soft">
      {children}
    </span>
  );
}

export default async function PortfolioModePage() {
  const ports = await getLivePortfolios();
  const liveCount = ports.length;
  const example = ports[0] ?? null;
  const [acct, curve, holdings] = example
    ? await Promise.all([getAccount(example.id), getEquityCurve(example.id), getHoldings(example.id)])
    : [null, [], []];

  return (
    <div className="space-y-10 pb-10 pt-2">
      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <Reveal>
        <div className="text-[11px] uppercase tracking-wider text-dim">How Maven works</div>
        <h1 className="mt-2 font-serif text-3xl text-ink sm:text-4xl">
          Portfolio Mode &amp; Broker connection, explained.
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          How research turns into a portfolio, and what &ldquo;connecting your broker&rdquo; will
          mean once it&apos;s available.
        </p>
      </Reveal>

      {/* ── Portfolio Mode ─────────────────────────────────────────────── */}
      <Reveal delay={60}>
        <h2 className="font-serif text-2xl" style={GRAD_EMERALD}>Portfolio Mode</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Turns market intelligence into portfolio action — holdings, weights, cash level,
          rebalance decisions, risk control — all driven by the same validated Enhanced F+
          engine. Each style is the same engine with a different tilt, not a separate product.
        </p>
      </Reveal>

      <Reveal delay={100} className="rounded-xl2 border border-border bg-panel/40 p-5">
        <div className="text-[11px] uppercase tracking-wider text-dim">One engine, many tilts</div>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Every style runs the same risk-managed chassis: a quality gate, a graded cash sleeve
          that de-risks on a weekly check, a 15% cut-on-breakdown stop, a full rebalance every
          quarter, and interest earned on idle cash. What changes between styles is the tilt —
          which signal it ranks by, how hard it de-risks, and how many names it holds. Most
          strategies chase return. The Enhanced F+ engine chases survival first — and lets
          return follow.
        </p>
      </Reveal>

      <Reveal delay={140}>
        <h3 className="text-[13px] font-medium tracking-wide text-ink">
          Three different kinds of numbers
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          You&apos;ll see performance figures in three places on Maven — they answer different
          questions, and it&apos;s worth knowing which is which.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl2 border border-border bg-panel/40 p-4">
            <div className="text-[11px] uppercase tracking-wider text-emerald">Backtested</div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">
              A historical simulation over 2021–26, shown on Strategies. Not a live track
              record.
            </p>
          </div>
          <div className="rounded-xl2 border border-border bg-panel/40 p-4">
            <div className="text-[11px] uppercase tracking-wider text-emerald">Live paper-trade</div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">
              Real, forward-tracked on real NSE prices, updated on a real schedule. No real
              money at risk. Shown on Portfolio.
            </p>
          </div>
          <div className="rounded-xl2 border border-border bg-panel/40 p-4">
            <div className="text-[11px] uppercase tracking-wider text-gold-soft">Illustrative</div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">
              Demo figures used to preview a style before it has a real track record. Always
              marked illustrative wherever shown.
            </p>
          </div>
        </div>
      </Reveal>

      <Reveal delay={180}>
        <h3 className="text-[13px] font-medium tracking-wide text-ink">How a portfolio gets built</h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Each portfolio starts from a stock universe, applies its own strategy-specific
          filters, ranks the eligible names, and sets target weights — capped at four names per
          sector. It updates on two clocks: a full re-pick every quarter, and a weekly check in
          between that scales exposure down if the market&apos;s own trend breaks. Any single
          position is cut immediately if it falls 15% from entry, regardless of the calendar.
        </p>
      </Reveal>

      {example && acct && (
        <Reveal delay={220}>
          <h3 className="text-[13px] font-medium tracking-wide text-ink">
            See it running — {displayName(example.name)}
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            {liveCount === 1
              ? "One live paper book is running today."
              : `${liveCount} live paper books are running today.`}{" "}
            Real prices, real decisions, no real money.
          </p>
          <div className="mt-4 grid gap-5 lg:grid-cols-2">
            <Card title="Equity curve" sub={`${displayName(example.name)} vs Nifty 500 TRI`}>
              <EquityChart data={curve} seriesName={displayName(example.name)} accent={example.name === "Defensive" ? "#94a3b8" : example.name === "Concentrated" ? "#c9a961" : "#34d399"} />
            </Card>
            <Card title="Current holdings" sub="live, real positions">
              <HoldingsTable rows={holdings} />
            </Card>
          </div>
          <Link href="/portfolio" className="mt-3 inline-block text-xs text-emerald hover:underline">
            See every live book in full →
          </Link>
        </Reveal>
      )}

      <Reveal delay={260}>
        <h3 className="text-[13px] font-medium tracking-wide text-ink">The style lineup</h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Nine named tilts on the same engine, grouped by how much conviction they take —
          Stable, Balanced, Bold. Not every style is live yet; each earns its place by clearing
          the same validation bar the flagship engine did.
        </p>
        <div className="mt-4 space-y-4">
          {STYLE_TIERS.map((grp) => (
            <div key={grp.tier}>
              <div className="text-[11px] uppercase tracking-wider text-dim">{grp.tier}</div>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {grp.items.map((s) => (
                  <span
                    key={s.name}
                    title={s.oneLine}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      s.signature ? "border-emerald/30 text-emerald" : "border-hairline text-muted"
                    }`}
                  >
                    {s.name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <Link href="/strategies" className="mt-3 inline-block text-xs text-emerald hover:underline">
          See backtested figures for every strategy →
        </Link>
      </Reveal>

      {/* ── Broker connection ──────────────────────────────────────────── */}
      <Reveal delay={300}>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-serif text-2xl" style={GRAD_GOLD}>Broker connection</h2>
          <StatusTag>Not yet available</StatusTag>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Connects Maven to a real account — Zerodha, Groww, Upstox, Angel One, HDFC Sky, Anand
          Rathi — read-only, to sync and compare your holdings against the models. Execution is
          the last layer, and it stays human-approved.
        </p>
      </Reveal>

      <Reveal delay={340} className="rounded-xl2 border border-dashed border-gold/25 bg-panel/30 p-5">
        <div className="text-[11px] uppercase tracking-wider text-gold-soft">Design principle</div>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Read-only. No trading. Maven never places, modifies, or cancels an order — not today,
          and not in any future version of this feature. Once available, connecting a broker
          will only ever show you where your real holdings differ from a model portfolio; what
          to do about that gap stays entirely your decision, made in your own broker&apos;s app.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {BROKER_LIST.map((b) => (
            <span key={b} className="rounded-full border border-hairline px-3 py-1 text-xs text-dim">
              {b} <span className="text-[0.6rem] text-dim/70">(planned)</span>
            </span>
          ))}
        </div>
      </Reveal>

      <Reveal delay={380}>
        <p className="max-w-2xl text-xs leading-relaxed text-dim">
          Research tool. Not investment advice. Paper-traded results, not real money. No
          order-placement code exists anywhere in Maven, today or planned. Not registered with
          SEBI.
        </p>
      </Reveal>
    </div>
  );
}
