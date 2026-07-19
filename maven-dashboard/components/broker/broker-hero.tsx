"use client";

// Broker hero — "orbital custody". Six real broker marks orbit the Maven
// medallion on two slow counter-rotating rings; dashed beams flow strictly
// INWARD (the read-only promise as motion). Pointer parallax tilts the whole
// constellation a few degrees on desktop. Reduced motion renders everything
// static and visible.

import Image from "next/image";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { EASE, useReducedMotionSafe } from "../motion";

const C = 260; // constellation center (520×520 box)

type Node = {
  name: string;
  img: string;
  angle: number; // degrees, 0 = right, counter-clockwise
  r: number;
  live?: boolean;
};

const NODES: Node[] = [
  { name: "Zerodha", img: "/brokers/zerodha.png", angle: 4, r: 212, live: true },
  { name: "HDFC Sky", img: "/brokers/hdfcsky.png", angle: 204, r: 210, live: true },
  { name: "Groww", img: "/brokers/groww.png", angle: 156, r: 208 },
  { name: "Anand Rathi", img: "/brokers/anandrathi.png", angle: 117, r: 210 },
  { name: "Upstox", img: "/brokers/upstox.png", angle: 74, r: 212 },
  { name: "Angel One", img: "/brokers/angelone.png", angle: 33, r: 206 },
];

const pos = (n: Node) => ({
  x: C + n.r * Math.cos((n.angle * Math.PI) / 180),
  y: C - n.r * Math.sin((n.angle * Math.PI) / 180),
});

function MavenMark({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" role="img" aria-label="Maven">
      <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="89" cy="17" r="8" fill="#34d399" />
    </svg>
  );
}

function Constellation({ reduce }: { reduce: boolean }) {
  // Pointer parallax: springs give the tilt real weight (motion values never
  // trigger re-renders; useSpring picks up velocity on interrupt).
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const sx = useSpring(px, { stiffness: 60, damping: 18 });
  const sy = useSpring(py, { stiffness: 60, damping: 18 });
  const rotateY = useTransform(sx, [-0.5, 0.5], [-5, 5]);
  const rotateX = useTransform(sy, [-0.5, 0.5], [5, -5]);

  return (
    <div
      className="relative mx-auto hidden lg:block"
      style={{ width: 520, height: 520, perspective: 1100 }}
      onMouseMove={(e) => {
        if (reduce) return;
        const b = e.currentTarget.getBoundingClientRect();
        px.set((e.clientX - b.left) / b.width - 0.5);
        py.set((e.clientY - b.top) / b.height - 0.5);
      }}
      onMouseLeave={() => {
        px.set(0);
        py.set(0);
      }}
      aria-hidden
    >
      {/* aurora + fine grid behind the system */}
      <div className="absolute inset-0 rounded-full" style={{ background: "radial-gradient(50% 50% at 50% 50%, rgba(52,211,153,0.14), rgba(52,211,153,0.04) 55%, transparent 75%)", filter: "blur(4px)" }} />
      <div className="absolute inset-6" style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "34px 34px", maskImage: "radial-gradient(circle, #000 30%, transparent 70%)", WebkitMaskImage: "radial-gradient(circle, #000 30%, transparent 70%)" }} />

      <motion.div className="absolute inset-0" style={reduce ? undefined : { rotateX, rotateY, transformStyle: "preserve-3d" }}>
        {/* two counter-rotating dashed orbits */}
        <motion.svg viewBox="0 0 520 520" className="absolute inset-0" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.2, ease: EASE }}>
          <motion.g style={{ originX: "50%", originY: "50%" }} animate={reduce ? undefined : { rotate: 360 }} transition={{ duration: 90, repeat: Infinity, ease: "linear" }}>
            <circle cx={C} cy={C} r={210} fill="none" stroke="rgba(52,211,153,0.16)" strokeWidth="1" strokeDasharray="2 9" />
          </motion.g>
          <motion.g style={{ originX: "50%", originY: "50%" }} animate={reduce ? undefined : { rotate: -360 }} transition={{ duration: 130, repeat: Infinity, ease: "linear" }}>
            <circle cx={C} cy={C} r={150} fill="none" stroke="rgba(201,169,97,0.13)" strokeWidth="1" strokeDasharray="2 11" />
          </motion.g>

          {/* inward-flowing beams: the dash pattern advances tile → center only */}
          {NODES.map((n, i) => {
            const p = pos(n);
            const dx = C - p.x;
            const dy = C - p.y;
            const len = Math.hypot(dx, dy);
            const x1 = p.x + (dx / len) * 36;
            const y1 = p.y + (dy / len) * 36;
            const x2 = C - (dx / len) * 68;
            const y2 = C - (dy / len) * 68;
            return (
              <motion.line
                key={n.name}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={n.live ? "rgba(52,211,153,0.55)" : "rgba(148,163,178,0.28)"}
                strokeWidth={n.live ? 1.6 : 1.1}
                strokeLinecap="round"
                strokeDasharray="3 11"
                initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                animate={reduce ? { opacity: 1 } : { pathLength: 1, opacity: 1, strokeDashoffset: [0, -56] }}
                transition={reduce ? undefined : {
                  pathLength: { duration: 0.9, delay: 0.55 + i * 0.1, ease: EASE },
                  opacity: { duration: 0.4, delay: 0.55 + i * 0.1 },
                  strokeDashoffset: { duration: 2.4, repeat: Infinity, ease: "linear", delay: 1.4 },
                }}
                style={n.live ? { filter: "drop-shadow(0 0 4px rgba(52,211,153,0.5))" } : undefined}
              />
            );
          })}
        </motion.svg>

        {/* broker tiles on the orbits */}
        {NODES.map((n, i) => {
          const p = pos(n);
          return (
            <motion.div
              key={n.name}
              className="absolute flex flex-col items-center gap-1.5"
              style={{ left: p.x, top: p.y, x: "-50%", y: "-50%" }}
              initial={reduce ? false : { opacity: 0, scale: 0.4 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 260, damping: 20, delay: reduce ? 0 : 0.35 + i * 0.09 }}
            >
              <span
                className={"relative grid h-14 w-14 place-items-center rounded-2xl bg-white shadow-[0_10px_30px_-12px_rgba(0,0,0,0.9)] " + (n.live ? "ring-2 ring-emerald/60" : "ring-1 ring-white/20 opacity-90")}
              >
                <Image src={n.img} alt={n.name} width={34} height={34} className="rounded-md object-contain" unoptimized />
                {n.live && (
                  <span className="brand-motion absolute -right-1 -top-1 flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full rounded-full bg-emerald opacity-70 animate-ping" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald ring-2 ring-bg" />
                  </span>
                )}
              </span>
              <span className="text-[9px] font-semibold uppercase tracking-[0.14em] text-dim">{n.name}</span>
            </motion.div>
          );
        })}

        {/* the medallion — data flows in, never out */}
        <motion.div
          className="brand-motion absolute flex flex-col items-center gap-2.5"
          style={{ left: C, top: C, x: "-50%", y: "-50%" }}
          initial={reduce ? false : { opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 22, delay: reduce ? 0 : 0.1 }}
        >
          <span className="relative grid place-items-center">
            <span className="absolute h-36 w-36 rounded-full bg-emerald/25 blur-2xl animate-gate-glow2" />
            <span className="absolute h-[7.5rem] w-[7.5rem] rounded-full animate-[gateSpin_11s_linear_infinite]" style={{ background: "conic-gradient(from 0deg, transparent 0deg, transparent 300deg, rgba(52,211,153,0.85) 340deg, transparent 360deg)", maskImage: "radial-gradient(circle, transparent 64%, #000 66%, #000 72%, transparent 74%)", WebkitMaskImage: "radial-gradient(circle, transparent 64%, #000 66%, #000 72%, transparent 74%)" }} />
            <span className="relative grid h-28 w-28 place-items-center rounded-full border border-emerald/30" style={{ background: "radial-gradient(circle at 50% 28%, #1a1f24, #0a0b0e)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.07), 0 24px 60px -20px rgba(0,0,0,0.95), 0 0 44px -14px rgba(52,211,153,0.4)" }}>
              <MavenMark size={52} />
            </span>
          </span>
          <span className="flex items-center gap-1.5 rounded-full border border-emerald/30 bg-bg/80 px-2.5 py-1 backdrop-blur">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2" strokeLinejoin="round"><path d="M12 3l7 3v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V6l7-3z" /><path d="M9 12l2 2 4-4" strokeLinecap="round" /></svg>
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-emerald">Read-only</span>
          </span>
        </motion.div>
      </motion.div>
    </div>
  );
}

export function BrokerHero() {
  const reduce = useReducedMotionSafe();
  const up = { hide: reduce ? { opacity: 1 } : { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } } };

  return (
    <section className="relative overflow-hidden pt-10 sm:pt-14">
      <div className="grid items-center gap-10 lg:grid-cols-[1.02fr_1fr]">
        <motion.div initial="hide" animate="show" variants={{ hide: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.09 } } }}>
          <motion.div variants={up} className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-gold-soft">
            <span className="font-mono text-dim">04</span>
            <span className="h-px w-9 bg-gold-soft/40" />
            Broker · Layer 4
          </motion.div>
          <motion.h1 variants={up} className="mt-4 font-serif text-[clamp(2.4rem,5vw,3.9rem)] leading-[1.04] text-ink">
            Connect your <em className="italic text-gold-soft">broker.</em>
          </motion.h1>
          <motion.div variants={up} className="mt-4 flex items-center gap-2 text-sm font-medium text-emerald">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"><path d="M12 3l7 3v5.5c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5V6l7-3z" /><path d="M9 12l2 2 4-4" strokeLinecap="round" /></svg>
            Securely linked. Read-only, no trading.
          </motion.div>
          <motion.p variants={up} className="mt-4 max-w-md text-[0.95rem] leading-relaxed text-muted">
            Once linked, Maven answers questions about your <span className="text-ink">actual holdings</span> —
            what you own, how it is allocated, where the concentration sits — grounded in your real
            portfolio, not a hypothetical one.
          </motion.p>
          <motion.div variants={up} className="mt-7 flex flex-wrap items-center gap-4">
            <a href="/login" className="inline-flex min-h-[46px] items-center gap-2 rounded-xl bg-gradient-to-br from-emerald to-emerald-deep px-6 text-sm font-semibold text-bg shadow-[0_14px_36px_-12px_rgba(52,211,153,0.8)] transition-[transform,opacity] duration-150 hover:opacity-90 motion-safe:hover:-translate-y-0.5 motion-safe:active:scale-[0.98]">
              Continue with Google
            </a>
            <span className="flex items-center gap-2 text-xs text-muted">
              <span className="brand-motion relative flex h-1.5 w-1.5"><span className="absolute h-full w-full rounded-full bg-emerald opacity-70 animate-ping" /><span className="relative h-1.5 w-1.5 rounded-full bg-emerald" /></span>
              Live now: Zerodha · HDFC Sky
            </span>
          </motion.div>
          <motion.p variants={up} className="mt-5 text-xs leading-relaxed text-dim">
            Read-only. Maven can see your holdings — never trade or move funds.
          </motion.p>
        </motion.div>

        <Constellation reduce={reduce} />

        {/* mobile: compact logo strip instead of the full constellation */}
        <div className="flex flex-wrap items-center justify-center gap-3 lg:hidden">
          {NODES.map((n) => (
            <span key={n.name} className={"grid h-12 w-12 place-items-center rounded-xl bg-white " + (n.live ? "ring-2 ring-emerald/60" : "ring-1 ring-white/15 opacity-85")}>
              <Image src={n.img} alt={n.name} width={28} height={28} className="rounded object-contain" unoptimized />
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
