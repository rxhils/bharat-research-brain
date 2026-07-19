"use client";

// Supported brokers — real marks on white tiles, glass cards, live shimmer.
// Live cards carry an emerald edge + pulsing status; coming-soon cards sit
// slightly dimmed with their logos in grayscale until hovered.

import Image from "next/image";
import type React from "react";
import { motion } from "framer-motion";
import { EASE, useReducedMotionSafe } from "../motion";

const GRAD_GOLD: React.CSSProperties = {
  background: "linear-gradient(180deg,#e3cb8f,#c9a961 60%,#9c8348)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};

type Broker = {
  name: string;
  img: string;
  desc: string;
  status: "live" | "soon";
};

const BROKERS: Broker[] = [
  { name: "HDFC Sky", img: "/brokers/hdfcsky.png", desc: "Connect via HDFC Sky", status: "live" },
  { name: "Zerodha", img: "/brokers/zerodha.png", desc: "Connect via Zerodha Kite", status: "live" },
  { name: "Groww", img: "/brokers/groww.png", desc: "Connect your Groww account", status: "soon" },
  { name: "Anand Rathi", img: "/brokers/anandrathi.png", desc: "Connect via Anand Rathi", status: "soon" },
  { name: "Upstox", img: "/brokers/upstox.png", desc: "Connect via Upstox API", status: "soon" },
  { name: "Angel One", img: "/brokers/angelone.png", desc: "Connect via Angel One", status: "soon" },
];

function BrokerCard({ b, i, reduce }: { b: Broker; i: number; reduce: boolean }) {
  const live = b.status === "live";
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.55, delay: reduce ? 0 : (i % 3) * 0.08, ease: EASE }}
      whileHover={reduce ? undefined : { y: -5 }}
      className={
        "group relative rounded-2xl p-px transition-shadow duration-300 " +
        (live
          ? "bg-gradient-to-b from-emerald/35 via-white/[0.07] to-transparent hover:shadow-[0_24px_60px_-24px_rgba(52,211,153,0.45)]"
          : "bg-gradient-to-b from-white/[0.1] via-white/[0.05] to-transparent hover:shadow-[0_24px_60px_-28px_rgba(0,0,0,0.9)]")
      }
    >
      {live && (
        <span aria-hidden className="brand-motion absolute inset-x-6 top-0 z-10 h-px animate-gate-shimmer opacity-80" style={{ background: "linear-gradient(90deg, transparent, rgba(52,211,153,0.7), transparent)", backgroundSize: "50% 100%", backgroundRepeat: "no-repeat" }} />
      )}
      <div className="relative flex h-full items-center gap-4 rounded-2xl bg-panel/60 p-5 backdrop-blur-md">
        <span className={"grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-white shadow-[0_8px_22px_-10px_rgba(0,0,0,0.8)] transition-transform duration-300 group-hover:scale-105 " + (live ? "ring-1 ring-emerald/40" : "")}>
          <Image
            src={b.img}
            alt={b.name}
            width={30}
            height={30}
            unoptimized
            className={"rounded object-contain transition-[filter,opacity] duration-300 " + (live ? "" : "opacity-80 grayscale group-hover:opacity-100 group-hover:grayscale-0")}
          />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[0.95rem] font-semibold text-ink">{b.name}</div>
          <div className="mt-0.5 truncate text-xs text-muted">{b.desc}</div>
        </div>
        {live ? (
          <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-emerald/30 bg-emerald/[0.08] px-2.5 py-1">
            <span className="brand-motion relative flex h-1.5 w-1.5">
              <span className="absolute h-full w-full rounded-full bg-emerald opacity-70 animate-ping" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-emerald" />
            </span>
            <span className="whitespace-nowrap text-[10px] font-semibold uppercase tracking-wide text-emerald">Live · in the app</span>
          </span>
        ) : (
          <span className="shrink-0 rounded-full border border-gold-soft/30 bg-gold-soft/[0.06] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-gold-soft/90">
            Coming soon
          </span>
        )}
      </div>
    </motion.div>
  );
}

export function BrokerGrid() {
  const reduce = useReducedMotionSafe();
  return (
    <section>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-8% 0px" }}
        transition={{ duration: 0.6, ease: EASE }}
      >
        <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-gold-soft">
          <span className="h-px w-9 bg-gold-soft/40" />
          Supported brokers
        </div>
        <h2 className="mt-3 font-serif text-3xl leading-tight text-ink sm:text-4xl">
          Yours is probably <em className="italic" style={GRAD_GOLD}>here.</em>
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
          Two live today, four on the way — every connection read-only, made on your broker&rsquo;s own login page.
        </p>
      </motion.div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {BROKERS.map((b, i) => (
          <BrokerCard key={b.name} b={b} i={i} reduce={reduce} />
        ))}
      </div>

      <p className="mt-6 text-center text-xs text-dim">
        Broker connections happen in the Maven app — the site never touches your brokerage.
      </p>
    </section>
  );
}
