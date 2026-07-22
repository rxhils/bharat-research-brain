import type { Metadata } from "next";
import { getABReadout, getEquityCurve } from "@/lib/data";
import { CountUp, SectionEyebrow } from "@/components/motion";
import { GlassPanel } from "@/components/glass-panel";
import { AgentPipeline, LIVE_COUNT, OFFLINE_COUNT } from "@/components/brain/pipeline";
import { BrainPerformance } from "@/components/brain/performance";

export const dynamic = "force-dynamic";

const title = "How the Research System Works: Agents & Evidence";
const description =
  "Explore the data sources, research agents, validation layers, evidence controls, update cadence, and system limitations behind Maven's research system.";
const url = "https://www.trymaven.in/brain";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

/** Hero stat cell — mono tnum figure over a caps label. Numeric figures animate
 *  via CountUp (the house numeric idiom); non-numeric ones render as-is. All
 *  figures are verbatim from the roster / agent copy — never invented. */
function HeroStat({ label, value, count }: {
  label: string; value?: string; count?: { to: number; prefix?: string };
}) {
  return (
    <div>
      <div className="font-mono text-2xl tnum text-ink">
        {count ? (
          <CountUp to={count.to} prefix={count.prefix ?? ""} decimals={0} className="font-mono" />
        ) : (
          value
        )}
      </div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-dim">{label}</div>
    </div>
  );
}

export default async function Brain() {
  const [curve, readout] = await Promise.all([getEquityCurve(), getABReadout()]);

  return (
    <div className="space-y-8">
      {/* ---- hero: what this page is, and the shape of the system in numbers ---- */}
      <section className="relative">
        {/* light source behind the panel, never on it (matches /portfolio) */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 left-1/2 h-72 w-[min(46rem,90vw)] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(52,211,153,0.09),transparent)]"
        />
        <GlassPanel as="div" glow="emerald" noise innerClassName="p-6 sm:p-10">
          <SectionEyebrow>The brain</SectionEyebrow>
          <h1 className="mt-3 font-serif text-[clamp(2.25rem,1rem+4.5vw,5rem)] leading-[1.02] tracking-[-0.02em] text-ink">
            Five agents decide.
            <br />
            Six more are waiting.
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-muted">
            The frozen Enhanced F+ engine picks a real 25-stock paper book from end-of-day prices —
            five live agents run the pipeline. Six research agents are built but offline, and do not
            touch the live decision. This is the whole system, in plain English.
          </p>

          <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-6 border-t border-hairline pt-6 sm:grid-cols-4">
            <HeroStat label="Live agents" count={{ to: LIVE_COUNT }} />
            <HeroStat label="Offline · research" count={{ to: OFFLINE_COUNT }} />
            <HeroStat label="Stock book" count={{ to: 25 }} />
            <HeroStat label="Stock universe" count={{ to: 500, prefix: "~" }} />
          </dl>
        </GlassPanel>
      </section>

      {/* ---- the live pipeline: five connected stages + recessed research band ---- */}
      <AgentPipeline />

      {/* ---- the honest live record: frozen F+ paper book vs the index ---- */}
      <BrainPerformance curve={curve} readout={readout} />

      <p className="px-1 pt-1 text-xs text-dim">
        Research tool. Not investment advice. Paper-traded results, not real money.
      </p>
    </div>
  );
}
