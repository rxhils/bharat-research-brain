"use client";
import { useEffect, useState } from "react";
import type { MarketSnapshot } from "@/lib/types";
import { pct, signClass } from "@/lib/format";
import { Stagger, StaggerItem } from "./motion";
import { Card, Label, Pill, Delta } from "./ui";
import { useMaven } from "./ctx";

const WATCH = [
  { sym: "ICICIBANK", name: "ICICI Bank", chg: 1.8 },
  { sym: "RELIANCE", name: "Reliance", chg: 0.6 },
  { sym: "INFY", name: "Infosys", chg: -0.4 },
  { sym: "SBIN", name: "State Bank of India", chg: 1.2 },
];

const EXPLAINERS = [
  { q: "What is the FAR route?", a: "Fully Accessible Route - lets foreign investors buy specified Indian government bonds without limits; it drove debt inflows after India joined global bond indices." },
  { q: "Why does lower crude help India?", a: "India imports most of its oil, so cheaper crude shrinks the import bill, supports the rupee and cools inflation." },
  { q: "Why does a bank rally matter?", a: "Financials are the heaviest weight in the Nifty, so when banks move they pull the whole index with them." },
];

function inrFlow(cr: number): string {
  return (cr >= 0 ? "+" : "-") + "₹" + Math.abs(cr).toLocaleString("en-IN") + " Cr";
}

export function MarketMode({ snap }: { snap: MarketSnapshot | null }) {
  const { setSubject, goChat } = useMaven();
  return (
    <Stagger className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <StaggerItem className="lg:col-span-2"><WhyMoved /></StaggerItem>
      <StaggerItem><Pulse snap={snap} /></StaggerItem>
      <StaggerItem>
        <Sectors snap={snap} onPick={(s) => { setSubject(s); goChat("Why is " + s + " moving today?"); }} />
      </StaggerItem>
      <StaggerItem><Themes snap={snap} onPick={(t) => { setSubject(t); goChat("Tell me about the " + t + " theme"); }} /></StaggerItem>
      <StaggerItem><Movers /></StaggerItem>
      <StaggerItem className="lg:col-span-2"><Explainers /></StaggerItem>
    </Stagger>
  );
}

function WhyMoved() {
  const [data, setData] = useState<{ available: boolean; reasons: { title: string; body: string }[] } | null>(null);
  useEffect(() => {
    let on = true;
    fetch("/api/market/explain").then((r) => r.json()).then((d) => { if (on) setData(d); }).catch(() => {});
    return () => { on = false; };
  }, []);
  const reasons = data?.reasons ?? [];
  const has = !!data?.available && reasons.length > 0;
  return (
    <Card>
      <div className="flex items-center justify-between">
        <Label>Why the market moved</Label>
        {has ? <Pill tone="emerald">AI - DeepSeek</Pill> : <Pill tone="gold">AI - add key</Pill>}
      </div>
      {has ? (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {reasons.map((r, i) => (
            <div key={i} className="rounded-lg border border-hairline bg-panel2/50 p-3">
              <div className="text-xs font-medium text-ink">{r.title}</div>
              <div className="mt-1 text-xs leading-relaxed text-muted">{r.body}</div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            A DeepSeek-written, source-cited explanation of today move appears here once DEEPSEEK_API_KEY is set
            (server-side). No reasons are shown yet, to avoid guessing.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {["Rates & liquidity", "Global cues", "Flows"].map((t) => (
              <div key={t} className="rounded-lg border border-hairline bg-panel2/50 p-3">
                <div className="text-xs text-ink">{t}</div>
                <div className="mt-2 h-2 w-2/3 rounded bg-white/5" />
                <div className="mt-1 h-2 w-1/2 rounded bg-white/5" />
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

function Stat({ k, v, tone }: { k: string; v: string; tone: "emerald" | "rose" }) {
  return (
    <div className="rounded-lg border border-hairline bg-panel2/50 p-3">
      <div className="text-[11px] text-dim">{k}</div>
      <div className={"mt-1 tnum text-base " + (tone === "emerald" ? "text-emerald" : "text-rose")}>{v}</div>
    </div>
  );
}

function Pulse({ snap }: { snap: MarketSnapshot | null }) {
  const p = snap?.pulse;
  return (
    <Card>
      <Label>Today pulse</Label>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Stat k="FII (net)" v={p ? inrFlow(p.flows.fiiCr) : "--"} tone={p && p.flows.fiiCr >= 0 ? "emerald" : "rose"} />
        <Stat k="DII (net)" v={p ? inrFlow(p.flows.diiCr) : "--"} tone={p && p.flows.diiCr >= 0 ? "emerald" : "rose"} />
        <Stat k="Advances" v={p ? String(p.breadthAdv) : "--"} tone="emerald" />
        <Stat k="Declines" v={p ? String(p.breadthDec) : "--"} tone="rose" />
      </div>
      <div className="mt-3 text-[11px] text-dim">Flows: {p?.flows.asOf ?? "--"} (EOD). Breadth: leading names.</div>
    </Card>
  );
}

function Sectors({ snap, onPick }: { snap: MarketSnapshot | null; onPick: (s: string) => void }) {
  const s = snap?.sectors ?? [];
  return (
    <Card>
      <Label>Sector moves</Label>
      <div className="mt-3 flex flex-col gap-2">
        {s.length === 0 && <div className="text-xs text-dim">Loading sectors...</div>}
        {s.map((x) => (
          <button key={x.name} onClick={() => onPick(x.name)} className="group flex items-center gap-3">
            <span className="w-16 text-left text-xs text-muted group-hover:text-ink">{x.name}</span>
            <span className="relative h-1.5 flex-1 rounded bg-white/5">
              <span
                className={"absolute top-0 h-1.5 rounded " + (x.changePct >= 0 ? "bg-emerald" : "bg-rose")}
                style={{
                  width: Math.min(50, Math.abs(x.changePct) * 25) + "%",
                  left: x.changePct >= 0 ? "50%" : "auto",
                  right: x.changePct < 0 ? "50%" : "auto",
                }}
              />
              <span className="absolute left-1/2 top-[-3px] h-3 w-px bg-white/15" />
            </span>
            <span className={"w-14 text-right tnum text-xs " + signClass(x.changePct)}>{pct(x.changePct)}</span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function Themes({ snap, onPick }: { snap: MarketSnapshot | null; onPick: (t: string) => void }) {
  const themes = snap?.pulse.themes ?? ["Banks", "Energy", "Defence", "Railways", "IT"];
  return (
    <Card>
      <Label>Themes to watch</Label>
      <div className="mt-3 flex flex-wrap gap-2">
        {themes.map((t) => (
          <button key={t} onClick={() => onPick(t)} className="rounded-full border border-hairline px-3 py-1.5 text-xs text-muted transition-colors hover:border-emerald/40 hover:text-ink">
            {t}
          </button>
        ))}
      </div>
    </Card>
  );
}

function Movers() {
  return (
    <Card>
      <Label>Watchlist movers</Label>
      <div className="mt-3 flex flex-col gap-2.5">
        {WATCH.map((w) => (
          <div key={w.sym} className="flex items-center justify-between">
            <div>
              <div className="text-sm text-ink">{w.name}</div>
              <div className="text-[11px] text-dim">{w.sym}</div>
            </div>
            <Delta v={w.chg} />
          </div>
        ))}
      </div>
      <div className="mt-2 text-[11px] text-dim">Sample watchlist - live prices in Phase 3.</div>
    </Card>
  );
}

function Explainers() {
  return (
    <Card>
      <Label>Explainers</Label>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {EXPLAINERS.map((e) => (
          <div key={e.q} className="rounded-lg border border-hairline bg-panel2/50 p-3">
            <div className="text-sm text-ink">{e.q}</div>
            <div className="mt-1.5 text-xs leading-relaxed text-muted">{e.a}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}