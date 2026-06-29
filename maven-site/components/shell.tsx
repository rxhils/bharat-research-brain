"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { MarketSnapshot } from "@/lib/types";
import { pct, signClass } from "@/lib/format";
import { MavenCtx, useMaven, type View } from "./ctx";
import { CountUp } from "./motion";
import { Logo, EmptyState } from "./ui";
import { MarketMode } from "./market";
import { ChatMode } from "./chat";

const NAV: { id: View; label: string }[] = [
  { id: "market", label: "Market" },
  { id: "chat", label: "Chat" },
  { id: "watchlist", label: "Watchlist" },
  { id: "themes", label: "Themes" },
  { id: "saved", label: "Saved" },
  { id: "settings", label: "Settings" },
];

const TITLES: Record<View, { kicker: string; title: string }> = {
  market: { kicker: "Market mode", title: "Today in the Indian market" },
  chat: { kicker: "Chat mode", title: "Ask Maven" },
  watchlist: { kicker: "Watchlist", title: "Your watchlist" },
  themes: { kicker: "Themes", title: "Themes to watch" },
  saved: { kicker: "Saved", title: "Saved views" },
  settings: { kicker: "Settings", title: "Settings" },
};

export function Maven() {
  const [view, setView] = useState<View>("market");
  const [subject, setSubject] = useState<string | null>(null);
  const [snap, setSnap] = useState<MarketSnapshot | null>(null);

  useEffect(() => {
    let on = true;
    fetch("/api/market").then((r) => r.json()).then((d) => { if (on) setSnap(d); }).catch(() => {});
    return () => { on = false; };
  }, []);

  const goChat = (s?: string) => { if (s) setSubject(s); setView("chat"); };

  return (
    <MavenCtx.Provider value={{ subject, setSubject, goChat }}>
      <div className="mx-auto flex min-h-screen max-w-[1440px]">
        <Sidebar view={view} setView={setView} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopStrip snap={snap} />
          <div className="flex min-w-0 flex-1">
            <main className="min-w-0 flex-1 px-4 py-5 sm:px-7">
              <Header view={view} setView={setView} />
              <div className="mt-5">
                {view === "market" && <MarketMode snap={snap} />}
                {view === "chat" && <ChatMode />}
                {view !== "market" && view !== "chat" && (
                  <EmptyState title={TITLES[view].title + " - coming soon"} sub="Phase 2 will populate this." />
                )}
              </div>
            </main>
            <ContextRail snap={snap} />
          </div>
        </div>
      </div>
    </MavenCtx.Provider>
  );
}

function Sidebar({ view, setView }: { view: View; setView: (v: View) => void }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-hairline px-3 py-5 md:flex">
      <div className="flex items-center gap-2 px-2">
        <Logo />
        <span className="font-serif text-lg text-ink">Maven</span>
      </div>
      <div className="mt-1 px-2 text-[10px] uppercase tracking-label text-dim">India market intelligence</div>
      <nav className="mt-6 flex flex-col gap-1">
        {NAV.map((n) => (
          <button
            key={n.id}
            onClick={() => setView(n.id)}
            className={"relative rounded-lg px-3 py-2 text-left text-sm transition-colors " + (view === n.id ? "text-ink" : "text-muted hover:text-ink")}
          >
            {view === n.id && (
              <motion.span layoutId="navsel" className="absolute inset-0 -z-10 rounded-lg bg-white/[0.06]" transition={{ type: "spring", stiffness: 400, damping: 32 }} />
            )}
            {n.label}
          </button>
        ))}
      </nav>
      <div className="mt-auto rounded-lg border border-hairline p-3 text-[11px] leading-relaxed text-dim">
        Educational market context. Not investment advice.
      </div>
    </aside>
  );
}

function TopStrip({ snap }: { snap: MarketSnapshot | null }) {
  return (
    <div className="sticky top-0 z-20 flex items-center gap-5 overflow-x-auto border-b border-hairline bg-bg/80 px-4 py-2.5 backdrop-blur sm:px-7">
      {!snap && Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-6 w-24 shrink-0 animate-pulse rounded bg-white/5" />)}
      {snap?.indices.map((q) => (
        <div key={q.symbol} className="flex shrink-0 items-baseline gap-2">
          <span className="text-[11px] text-muted">{q.label}</span>
          <span className="tnum text-sm text-ink">{q.price != null ? <CountUp to={q.price} decimals={2} duration={0.9} /> : "--"}</span>
          {q.changePct != null && <span className={"tnum text-[11px] " + signClass(q.changePct)}>{pct(q.changePct)}</span>}
        </div>
      ))}
      <div className="ml-auto shrink-0 pl-4">
        <span className={"rounded-md px-2 py-0.5 text-[10px] " + (snap?.live ? "bg-emerald/10 text-emerald" : "bg-amber/10 text-amber")}>
          {snap ? (snap.live ? "Live - Yahoo" : "Sample") : "..."}
        </span>
      </div>
    </div>
  );
}

function Header({ view, setView }: { view: View; setView: (v: View) => void }) {
  const isMode = view === "market" || view === "chat";
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div className="text-[10px] uppercase tracking-label text-dim">{TITLES[view].kicker}</div>
        <h1 className="mt-1 font-serif text-2xl text-ink">{TITLES[view].title}</h1>
      </div>
      {isMode && <ModeToggle view={view} setView={setView} />}
    </div>
  );
}

function ModeToggle({ view, setView }: { view: View; setView: (v: View) => void }) {
  const opts: View[] = ["market", "chat"];
  return (
    <div className="relative flex rounded-full border border-border bg-panel/70 p-1">
      {opts.map((o) => (
        <button
          key={o}
          onClick={() => setView(o)}
          className={"relative z-10 rounded-full px-5 py-1.5 text-sm capitalize transition-colors " + (view === o ? "text-bg" : "text-muted hover:text-ink")}
        >
          {view === o && <motion.span layoutId="modepill" className="absolute inset-0 -z-10 rounded-full bg-emerald" transition={{ type: "spring", stiffness: 380, damping: 30 }} />}
          {o}
        </button>
      ))}
    </div>
  );
}

function ContextRail({ snap }: { snap: MarketSnapshot | null }) {
  const { subject, goChat } = useMaven();
  const actions = ["What changed today?", "Explain simply", "Summarize the market"];
  return (
    <aside className="sticky top-[45px] hidden h-[calc(100vh-45px)] w-72 shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline px-4 py-5 lg:flex">
      <div>
        <div className="text-[10px] uppercase tracking-label text-dim">Context</div>
        <div className="mt-2 rounded-lg border border-hairline bg-panel/60 p-3">
          <div className="text-sm text-ink">{subject ?? "Whole market"}</div>
          <div className="mt-1 text-[11px] text-dim">Active subject - carried into Chat.</div>
        </div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-label text-dim">Quick actions</div>
        <div className="mt-2 flex flex-col gap-2">
          {actions.map((a) => (
            <button
              key={a}
              onClick={() => goChat(a)}
              className="rounded-lg border border-hairline px-3 py-2 text-left text-xs text-muted transition-colors hover:border-border hover:text-ink"
            >
              {a}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-auto text-[10px] leading-relaxed text-dim">
        {snap ? snap.source : "Loading data..."}
        <br />
        As of {snap && snap.asOf ? new Date(snap.asOf).toLocaleTimeString("en-IN") : "--"}
      </div>
    </aside>
  );
}