"use client";

// Trades page — every trade the frozen F+ engine has taken (open + closed), each with
// a day-to-day price sparkline (is the stock going up or down) and the plain-English
// entry thesis / exit trigger. All real data from paper_position + prices_eod_adjusted.
//
// Wave-2 redesign ("The Tape"): the page hero carries a count-up scoreboard plus an
// aggregate paper-P&L path that draws itself in (TapePath below); row sparklines get
// the same PathDraw treatment with a gradient area fill and a pulsing endpoint dot on
// open positions; the expanded panel gains a real full-width price chart (TradeChart)
// with a dashed entry line and entry/exit markers. Kit gap note: PathDraw can't take
// vector-effect / preserveAspectRatio="none", so TapePath and TradeChart build their
// own motion.path locally (same pathLength pattern, .brand-motion wrapped).

import { AnimatePresence, motion, useMotionTemplate, useMotionValue } from "framer-motion";
import { useEffect, useId, useState, type PointerEvent } from "react";
import type { Trade } from "@/lib/types";
import { EASE, EASE_SOFT, LayoutPill, PathDraw, Reveal, SectionEyebrow, useReducedMotionSafe } from "./motion";

const pc = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
const rs = (n: number) => "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
const sign = (n: number) => (n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted");

const EMERALD = "#34d399";
const ROSE = "#fb7185";

/* ------------------------------------------------------------------ */
/* The Tape — aggregate paper-P&L path for the hero scoreboard.        */
/* Points are computed server-side in app/trades/page.tsx from the     */
/* real trade series; this only draws them. Renders nothing when there */
/* is not enough data (honest omission, never a decorative fake line). */
/* ------------------------------------------------------------------ */
export function TapePath({
  pts,
  className = "",
  caption = "mean % move from entry · all trades",
}: {
  pts: number[];
  className?: string;
  caption?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  if (pts.length < 2) return null;
  const min = Math.min(...pts), max = Math.max(...pts);
  const rng = max - min || 1;
  // x mapped to 1..99, y to 6..36 (viewBox 0 0 100 40) so the stroke + endpoint
  // dot never clip against the glass panel's overflow-hidden.
  const X = (i: number) => 1 + (i / (pts.length - 1)) * 98;
  const Y = (v: number) => 36 - ((v - min) / rng) * 30;
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${X(i).toFixed(2)},${Y(p).toFixed(2)}`).join(" ");
  const areaD = `${d} L99,40 L1,40 Z`;
  const start = pts[0];
  const end = pts[pts.length - 1];
  const maxI = pts.indexOf(max);
  const lastY = Y(end);
  const topPct = (v: number) => `${(Y(v) / 40) * 100}%`;
  const fmt = (n: number) => `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
  return (
    <div className={`brand-motion ${className}`}>
      <div className="relative">
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="block h-24 w-full" aria-hidden>
          <defs>
            <linearGradient id={`tape-area-${uid}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={EMERALD} stopOpacity="0.2" />
              <stop offset="100%" stopColor={EMERALD} stopOpacity="0" />
            </linearGradient>
          </defs>
          <motion.path
            d={areaD}
            fill={`url(#tape-area-${uid})`}
            stroke="none"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-10% 0px" }}
            transition={{ duration: 0.8, delay: 0.9, ease: EASE_SOFT }}
          />
          <motion.path
            d={d}
            fill="none"
            stroke={EMERALD}
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            whileInView={{ pathLength: 1 }}
            viewport={{ once: true, margin: "-10% 0px" }}
            transition={{ duration: 1.4, delay: 0.2, ease: EASE }}
          />
        </svg>
        {/* gold-soft marker on the peak reading — the page's 2nd sanctioned gold use */}
        <motion.span
          aria-hidden
          className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gold-soft"
          style={{ left: `${X(maxI)}%`, top: topPct(max) }}
          initial={{ opacity: 0, scale: 0 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: "-10% 0px" }}
          transition={{ duration: 0.35, delay: 1.7, ease: EASE_SOFT }}
        />
        <span
          className="absolute -translate-x-1/2 translate-y-2 whitespace-nowrap font-mono text-[9px] tnum text-gold-soft"
          style={{ left: `${X(maxI)}%`, top: topPct(max) }}
        >
          peak {fmt(max)}
        </span>
        {/* latest endpoint dot */}
        <motion.span
          aria-hidden
          className="absolute h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald"
          style={{ left: "99%", top: `${(lastY / 40) * 100}%` }}
          initial={{ opacity: 0, scale: 0 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: "-10% 0px" }}
          transition={{ duration: 0.35, delay: 1.6, ease: EASE_SOFT }}
        />
        {/* start / latest values pinned at the path ends (tnum mono) */}
        <span className="absolute left-0 -translate-y-1/2 font-mono text-[10px] tnum text-dim" style={{ top: topPct(start) }}>
          {fmt(start)}
        </span>
        <span className="absolute right-0 -translate-y-[150%] font-mono text-[10px] tnum text-emerald" style={{ top: topPct(end) }}>
          {fmt(end)}
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-[0.12em] text-dim">
        <span>{caption}</span>
        <span>start {fmt(start)} → latest {fmt(end)}</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Row sparkline — PathDraw draw-in + gradient area fill + endpoint    */
/* dot; open positions get a pulsing ring (.brand-motion exempts it    */
/* from the OS reduced-motion damp — it is a live-position signal).    */
/* ------------------------------------------------------------------ */
function Sparkline({ pts, up, live }: { pts: number[]; up: boolean; live: boolean }) {
  if (pts.length < 2) return <span className="text-[10px] text-dim">no path</span>;
  const w = 150, h = 34, min = Math.min(...pts), max = Math.max(...pts);
  const rng = max - min || 1;
  const xy = pts.map((p, i) => ({
    x: 3 + (i / (pts.length - 1)) * (w - 6),
    y: h - ((p - min) / rng) * (h - 8) - 4,
  }));
  const d = xy.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const areaD = `${d} L${(w - 3).toFixed(1)},${h} L3,${h} Z`;
  const last = xy[xy.length - 1];
  const color = up ? EMERALD : ROSE;
  return (
    // decorative: the trend is stated by the adjacent signed % text
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="shrink-0">
      <PathDraw
        d={d}
        stroke={color}
        strokeWidth={1.5}
        duration={0.8}
        areaD={areaD}
        areaFill={up ? "rgba(52,211,153,0.14)" : "rgba(251,113,133,0.12)"}
        dot={{ cx: last.x, cy: last.y, r: 2.5, fill: color }}
      />
      {live && (
        <circle
          className="motion-safe:animate-ping"
          cx={last.x}
          cy={last.y}
          r={3}
          fill={color}
          opacity={0.5}
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
        />
      )}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* TradeChart — the full price path inside the expanded panel: drawn   */
/* line + gradient area (preserveAspectRatio="none" svg with           */
/* non-scaling strokes), dashed hairline at the entry price, gold-soft */
/* entry marker and emerald/rose exit-or-latest marker, min/max ₹      */
/* ticks. Mounts inside the accordion, so it animates on mount.        */
/* ------------------------------------------------------------------ */
function TradeChart({ t }: { t: Trade }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const pts = t.series.map((p) => p.close);
  if (pts.length < 2) return null;
  const min = Math.min(...pts, t.entryPrice);
  const max = Math.max(...pts, t.entryPrice);
  const rng = max - min || 1;
  // percent-space geometry: x 2..98, y 8..92 so the markers never clip.
  const X = (i: number) => 2 + (i / (pts.length - 1)) * 96;
  const Y = (v: number) => 92 - ((v - min) / rng) * 84;
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${X(i).toFixed(2)},${Y(p).toFixed(2)}`).join(" ");
  const areaD = `${d} L98,100 L2,100 Z`;
  const entryY = Y(t.entryPrice);
  const lastY = Y(pts[pts.length - 1]);
  const up = t.pnlPct >= 0;
  const color = up ? EMERALD : ROSE;
  const live = t.status === "open";
  return (
    <div className="brand-motion relative h-[140px] w-full" aria-hidden>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        <defs>
          <linearGradient id={`tc-area-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.18" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <motion.path
          d={areaD}
          fill={`url(#tc-area-${uid})`}
          stroke="none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.7, delay: 0.5, ease: EASE_SOFT }}
        />
        {/* dashed hairline at the entry price */}
        <line
          x1="0" x2="100" y1={entryY} y2={entryY}
          stroke="rgba(255,255,255,0.25)" strokeWidth={1}
          strokeDasharray="4 4" vectorEffect="non-scaling-stroke"
        />
        <motion.path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={1.75}
          vectorEffect="non-scaling-stroke"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.9, ease: EASE }}
        />
      </svg>
      {/* entry marker — muted dot (reference, not an accent); gold is reserved
          for the single Tape peak so the page keeps to gold-max-2 */}
      <span
        className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/60"
        style={{ left: "2%", top: `${Y(pts[0])}%` }}
      />
      {/* exit-or-latest marker */}
      <motion.span
        className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{ left: "98%", top: `${lastY}%`, backgroundColor: color }}
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.9, ease: EASE_SOFT }}
      />
      {live && (
        // decorative pulse — freezes under OS reduced-motion (motion-safe), not .brand-motion
        <span
          className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full motion-safe:animate-ping"
          style={{ left: "98%", top: `${lastY}%`, backgroundColor: color, opacity: 0.4 }}
        />
      )}
      {/* entry label pinned to the dashed line — flips BELOW the line when the
          entry sits near the top, so -translate-y-full never clips the container. */}
      <span
        className={`absolute right-1 font-mono text-[10px] uppercase tracking-wide text-muted ${
          entryY < 14 ? "pt-0.5" : "-translate-y-full pb-0.5"
        }`}
        style={{ top: `${entryY}%` }}
      >
        entry {rs(t.entryPrice)} · {t.entryDate}
      </span>
      {/* price hi / lo ticks — top corners (y-axis anchors) */}
      <span className="absolute left-1 top-0.5 font-mono text-[10px] tnum text-dim">H {rs(max)}</span>
      <span className="absolute right-1 top-0.5 font-mono text-[10px] tnum text-dim">L {rs(min)}</span>
      {/* first / last trading-day ticks — bottom corners (x-axis anchors) */}
      <span className="absolute bottom-0.5 left-1 font-mono text-[10px] tnum text-dim">{t.series[0].date}</span>
      <span className="absolute bottom-0.5 right-1 font-mono text-[10px] tnum text-dim">{t.series[t.series.length - 1].date}</span>
    </div>
  );
}

function Field({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-dim">{label}</div>
      <div className={`mt-0.5 font-mono text-sm tnum ${tone ?? "text-ink"}`}>{value}</div>
    </div>
  );
}

// Row button fades its background on hover, so keep transition-colors alongside
// the press scale (plain PRESS would override it). scale-[0.99] on a wide row.
const ROW_PRESS =
  "motion-safe:transition-[background-color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.99]";

function TradeRow({ t }: { t: Trade }) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotionSafe();
  const closes = t.series.map((p) => p.close);
  const up = t.trendPct >= 0;
  const value = t.shares * t.currentPrice;
  // Desktop-only pointer-tracked spotlight: a radial gradient that follows the
  // cursor across the row (transform/opacity-free, background-position only).
  // Off under coarse pointers and OS reduced-motion — decorative, not signal.
  const mx = useMotionValue(-200);
  const my = useMotionValue(-200);
  const spotlight = useMotionTemplate`radial-gradient(150px circle at ${mx}px ${my}px, rgba(52,211,153,0.08), transparent 72%)`;
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: fine)");
    setFine(mq.matches);
    const on = (e: MediaQueryListEvent) => setFine(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const showSpotlight = fine && !reduce;
  const onMove = (e: PointerEvent<HTMLButtonElement>) => {
    if (!showSpotlight) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set(e.clientX - r.left);
    my.set(e.clientY - r.top);
  };
  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-bg/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onPointerMove={onMove}
        aria-expanded={open}
        className={`group relative block w-full p-3 text-left hover:bg-panel/50 ${ROW_PRESS}`}
      >
        {showSpotlight && (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-0 z-0 rounded-xl opacity-0 group-hover:opacity-100 motion-safe:transition-opacity motion-safe:duration-200"
            style={{ background: spotlight }}
          />
        )}
        <div className="relative z-10 flex flex-wrap items-center gap-x-4 gap-y-2">
        {/* name */}
        <div className="min-w-[150px] flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-ink">{t.ticker}</span>
            <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
              t.status === "open" ? "bg-emerald/15 text-emerald" : "bg-white/5 text-muted"}`}>
              {t.status}
            </span>
          </div>
          <div className="truncate text-xs text-muted">{t.name} · {t.sector}</div>
          <div className="mt-0.5 font-mono text-[10px] tnum text-dim">
            opened {t.entryDate}{t.exitDate ? ` · closed ${t.exitDate}` : ""}
          </div>
        </div>
        {/* sparkline (day-to-day) */}
        <div className="flex items-center gap-2">
          <Sparkline pts={closes} up={up} live={t.status === "open"} />
          <span className={`font-mono text-xs tnum ${sign(t.trendPct)}`}>{pc(t.trendPct)}</span>
        </div>
        {/* entry -> current */}
        <div className="text-right font-mono text-xs tnum text-muted">
          <div>{rs(t.entryPrice)} → {rs(t.currentPrice)}</div>
          <div className="text-[10px] text-dim">{t.status === "open" ? "entry → latest" : "entry → exit"}</div>
        </div>
        {/* pnl */}
        <div className={`w-20 text-right font-mono text-sm font-semibold tnum ${sign(t.pnlPct)}`}>
          {pc(t.pnlPct)}
        </div>
        </div>
      </button>

      {/* Smooth height+opacity reveal instead of a snap. Clipped by the parent's
          overflow-hidden so the price-path detail slides open cleanly. */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="detail"
            initial={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            animate={reduce ? { opacity: 1 } : { height: "auto", opacity: 1 }}
            exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="space-y-3 border-t border-hairline px-3 pb-3 pt-3">
              {/* entry rationale */}
              <div className="rounded-lg border border-emerald/20 bg-emerald/[0.05] p-3">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-emerald">Entry thesis</div>
                <p className="mt-1 text-xs leading-relaxed text-muted">{t.whyEntry}</p>
              </div>
              {/* exit rationale */}
              {t.whyExit && (
                <div className="rounded-lg border border-rose/20 bg-rose/[0.05] p-3">
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-rose">Exit trigger</div>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{t.whyExit}</p>
                </div>
              )}
              {/* the actual price path — real EOD adjusted close, entry → exit/latest */}
              <TradeChart t={t} />
              {/* details */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="Entry" value={`${rs(t.entryPrice)}`} />
                <Field label="Entry date" value={t.entryDate} />
                <Field label={t.status === "open" ? "Latest" : "Exit"} value={rs(t.currentPrice)} tone={sign(t.pnlPct)} />
                <Field label={t.status === "open" ? "As of" : "Exit date"} value={t.exitDate ?? "—"} />
                <Field label="Shares" value={t.shares.toFixed(2)} />
                <Field label="Position value" value={rs(value)} />
                <Field label="Exposure at entry" value={`${(t.exposureAtEntry * 100).toFixed(0)}%`} />
                <Field label="P&L" value={pc(t.pnlPct)} tone={sign(t.pnlPct)} />
              </div>
              <p className="text-[11px] text-dim">
                Day-to-day path: {t.series.length} trading days, moved
                <span className={`ml-1 font-mono tnum ${sign(t.trendPct)}`}>{pc(t.trendPct)}</span> since entry
                (real EOD adjusted close).
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* EngineJumpNav — slim sticky nav under the hero: one mono pill per    */
/* engine section, the shared-layoutId pill gliding to the section in   */
/* view (IntersectionObserver scrollspy). Breaks the 60-row scroll.     */
/* ------------------------------------------------------------------ */
export function EngineJumpNav({ items }: { items: { id: string; label: string }[] }) {
  const pillId = useId();
  const [active, setActive] = useState(items[0]?.id ?? "");
  useEffect(() => {
    const els = items
      .map((it) => document.getElementById(it.id))
      .filter((el): el is HTMLElement => el !== null);
    if (els.length === 0) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-40% 0px -50% 0px", threshold: 0 },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [items]);
  if (items.length < 2) return null;
  return (
    <nav className="sticky top-2 z-20 flex flex-wrap gap-1 rounded-xl border border-hairline bg-bg/90 p-1">
      {items.map((it) => (
        <a
          key={it.id}
          href={`#${it.id}`}
          onClick={() => setActive(it.id)}
          aria-current={active === it.id ? "true" : undefined}
          className={`relative rounded-lg px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] motion-safe:transition-colors ${
            active === it.id ? "text-emerald" : "text-muted hover:text-ink"}`}
        >
          {active === it.id && (
            <LayoutPill layoutId={`engine-nav-${pillId}`} className="absolute inset-0 rounded-lg bg-emerald/15" />
          )}
          <span className="relative">{it.label}</span>
        </a>
      ))}
    </nav>
  );
}

export function TradesView({ trades, engineLabel = "Enhanced F+" }: { trades: Trade[]; engineLabel?: string }) {
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  // unique per instance: two engine sections render side by side and layoutId is
  // global, so a shared id would animate the pill across sections.
  const pillId = useId();
  if (!trades.length) {
    return (
      <div className="rounded-xl border border-hairline bg-bg/40 p-6 text-center text-sm text-muted">
        No trades yet — the paper account has not been incepted, or DATABASE_URL is not set.
      </div>
    );
  }
  const openN = trades.filter((t) => t.status === "open").length;
  const closedN = trades.length - openN;
  const closed = trades.filter((t) => t.status === "closed");
  const closedAvg = closed.length ? closed.reduce((s, t) => s + t.pnlPct, 0) / closed.length : null;
  const shown = trades.filter((t) => filter === "all" || t.status === filter);
  const tab = (key: "all" | "open" | "closed", label: string) => (
    <button
      type="button"
      onClick={() => setFilter(key)}
      aria-pressed={filter === key}
      className={`relative rounded-lg px-3 py-1 text-xs motion-safe:transition-[color,transform] motion-safe:duration-150 motion-safe:active:scale-[0.97] ${
        filter === key ? "text-emerald" : "text-muted hover:text-ink"}`}
    >
      {filter === key && (
        <LayoutPill layoutId={`trades-filter-${pillId}`} className="absolute inset-0 rounded-lg bg-emerald/15" />
      )}
      <span className="relative">{label}</span>
    </button>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <SectionEyebrow>{engineLabel}</SectionEyebrow>
          <p className="mt-1 text-xs text-muted">Tap a trade for the price path and the entry/exit logic.</p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {/* right-aligned mini-stat block — the per-engine scoreboard echo (plan step 8) */}
          <div className="text-right font-mono text-[11px] tnum text-dim">
            <span className="text-ink">{trades.length}</span> trades ·{" "}
            <span className="text-emerald">{openN} open</span> · {closedN} closed
            {closedAvg !== null && (
              <> · avg <span className={sign(closedAvg)}>{pc(closedAvg)}</span></>
            )}
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-hairline bg-panel/50 p-1">
            {tab("all", "All")}
            {tab("open", "Open")}
            {tab("closed", "Closed")}
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {shown.map((t, i) => <Reveal key={t.id} y={10} delay={Math.min(i, 8) * 0.035}><TradeRow t={t} /></Reveal>)}
      </div>
    </div>
  );
}
