"use client";

// Agent explainer — the roster of every agent in the system, what each one does in
// plain English, and whether it is LIVE (part of the frozen-F+ decision that moves
// your money) or OFFLINE (built but not yet wired / not part of the live signal).
// Click any agent to expand. Live status overlays real agent_run_log rows from
// /api/agents when a nightly run has recorded heartbeats; until then the documented
// status is shown. Honest by design — no fake "busy" agents.

import { useEffect, useState } from "react";
import type { AgentBoard, AgentRun } from "@/lib/types";

type Doc = {
  name: string;
  one: string; // one-line summary
  long: string; // plain-English explanation
  cadence?: string; // when it runs (live agents)
  offlineReason?: string; // why it is offline
};

const LIVE: Doc[] = [
  {
    name: "Price Ingest",
    one: "Grabs the official closing price of every stock.",
    long: "After the market closes, this pulls the end-of-day price for all ~500 stocks. "
      + "Every other number — your portfolio value, the stops, the rankings — is built on "
      + "these prices. Free permitted source (yfinance EOD); no live broker feed required.",
    cadence: "Daily, after close",
  },
  {
    name: "Daily Mark",
    one: "Re-prices your holdings and applies the safety stop.",
    long: "Re-values your open positions at today's close, updates the equity curve and "
      + "drawdown, and automatically sells any holding that has fallen 15% below your entry "
      + "(cut-on-breakdown). This is the daily risk check.",
    cadence: "Daily",
  },
  {
    name: "Exposure / Regime",
    one: "Decides how much to keep in cash vs stocks.",
    long: "Checks whether the whole market (Nifty 500) is above or below its 200-day "
      + "average. Healthy → fully invested (100%). Weakening → 50%. Dangerous → 25%, the rest "
      + "in cash. This is what cut the drawdown through the COVID crash in the backtest.",
    cadence: "Weekly",
  },
  {
    name: "Quarterly Rebalance",
    one: "Rebuilds the 25-stock book every quarter.",
    long: "Every ~63 trading days it re-ranks the whole universe with the Enhanced F+ score, sells "
      + "names that dropped out, buys new leaders, and keeps existing winners (hold buffer). "
      + "Redeploys cash at the current exposure level.",
    cadence: "Quarterly",
  },
  {
    name: "Enhanced F+ Composite Scorer",
    one: "The actual brain that picks the stocks.",
    long: "Scores every stock on vol-adjusted momentum + quality + low-volatility (the Enhanced F+ "
      + "composite), capped at 4 per sector, and the top 25 become the book. This is the "
      + "exact logic that passed every backtest (commit 6ced078) — nothing else picks names.",
    cadence: "At each rebalance",
  },
];

const OFFLINE: Doc[] = [
  {
    name: "News",
    one: "Scans market news headlines per stock.",
    long: "Would read recent headlines for each holding and tag relevance. The NewsAPI key "
      + "is set, but the client is not yet wired into the live pipeline.",
    offlineReason: "NewsAPI client not wired",
  },
  {
    name: "Sentiment (FinBERT)",
    one: "Rates news positive / negative with a finance AI.",
    long: "Would run headlines through FinBERT (a finance language model) to score tone. "
      + "Needs the model + a GPU machine running; not provisioned on the cloud yet.",
    offlineReason: "FinBERT / GPU not running",
  },
  {
    name: "Fundamentals",
    one: "Reads revenue, profit and debt from financials.",
    long: "Would pull quarterly financials and trend them. The FMP key is valid, but the "
      + "client is not wired into the live decision.",
    offlineReason: "FMP client pending",
  },
  {
    name: "FII / DII Flows",
    one: "Tracks big foreign / domestic fund buying & selling.",
    long: "Would read end-of-day institutional flow data. Requires operator-downloaded "
      + "exchange CSVs (we never scrape the NSE site).",
    offlineReason: "needs operator CSV uploads",
  },
  {
    name: "Macro",
    one: "Watches USD/INR, crude, India VIX and rates.",
    long: "Tracks the big-picture backdrop. Some data exists, but macro is not part of the "
      + "live Enhanced F+ signal — only the market-regime check (in Exposure) is.",
    offlineReason: "not in the live signal",
  },
  {
    name: "Meta-Auditor",
    one: "Checks every claim has a real source.",
    long: "Would reject any agent claim with no evidence or stale data. Only runs when the "
      + "AI research agents above are online.",
    offlineReason: "runs only with the AI agents",
  },
];

function StatusDot({ live, run }: { live: boolean; run?: AgentRun }) {
  let color = live ? "bg-emerald" : "bg-dim";
  let pulse = "";
  if (run) {
    if (run.status === "running") { color = "bg-amber"; pulse = "animate-pulseDot"; }
    else if (run.status === "done") color = "bg-emerald";
    else if (run.status === "error") color = "bg-rose";
    else if (run.status === "offline") color = "bg-dim";
  }
  return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color} ${pulse}`} />;
}

function AgentCard({ doc, live, run }: { doc: Doc; live: boolean; run?: AgentRun }) {
  const [open, setOpen] = useState(false);
  const badge = live
    ? { text: run?.status ?? "live", cls: "bg-emerald/15 text-emerald" }
    : { text: "offline", cls: "bg-white/5 text-dim" };
  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      className="w-full rounded-xl border border-hairline bg-bg/40 p-3 text-left transition-colors hover:border-white/10 hover:bg-panel/60"
    >
      <div className="flex items-start gap-2.5">
        <StatusDot live={live} run={run} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink">{doc.name}</span>
            <span className={`rounded-md px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${badge.cls}`}>
              {badge.text}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted">{doc.one}</p>
          {open && (
            <div className="mt-2 border-t border-hairline pt-2">
              <p className="text-xs leading-relaxed text-muted">{doc.long}</p>
              {live && doc.cadence && (
                <p className="mt-1.5 text-[11px] text-dim">Runs: {doc.cadence}</p>
              )}
              {!live && doc.offlineReason && (
                <p className="mt-1.5 text-[11px] text-dim">Offline: {doc.offlineReason}</p>
              )}
              {run?.headlineOutput && (
                <p className="mt-1.5 font-mono text-[11px] text-emerald">{run.headlineOutput}</p>
              )}
            </div>
          )}
          {!open && <p className="mt-1 text-[10px] text-dim">click to explain</p>}
        </div>
      </div>
    </button>
  );
}

export function AgentExplainer() {
  const [board, setBoard] = useState<AgentBoard | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch("/api/agents", { cache: "no-store" });
        if (alive && r.ok) setBoard(await r.json());
      } catch { /* board stays null — documented status is shown */ }
    };
    load();
    const id = setInterval(load, 8000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const byName = new Map<string, AgentRun>();
  for (const a of board?.agents ?? []) byName.set(a.agentName.toLowerCase(), a);
  const runFor = (name: string) => byName.get(name.toLowerCase());

  const liveRecorded = (board?.agents ?? []).some((a) => a.status === "running" || a.status === "done");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-ink">The agents — what each one does</h2>
          <p className="mt-0.5 text-xs text-muted">
            Tap any agent for a plain-English explanation.
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-dim">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald" /> live</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-dim" /> offline</span>
        </div>
      </div>

      <div>
        <div className="mb-2 text-[11px] font-medium uppercase tracking-widest text-muted">
          Live — the Enhanced F+ engine (decides your money)
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {LIVE.map((d) => <AgentCard key={d.name} doc={d} live run={runFor(d.name)} />)}
        </div>
      </div>

      <div>
        <div className="mb-2 text-[11px] font-medium uppercase tracking-widest text-muted">
          Offline — research layer (built, not part of the live signal)
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {OFFLINE.map((d) => <AgentCard key={d.name} doc={d} live={false} run={runFor(d.name)} />)}
        </div>
      </div>

      <p className="text-[11px] text-dim">
        {liveRecorded
          ? `Live run ${board?.runId} — status from agent_run_log.`
          : "No nightly run has recorded heartbeats yet — statuses above are the documented "
            + "design. They light up live once the scheduled job runs."}
      </p>
    </div>
  );
}
