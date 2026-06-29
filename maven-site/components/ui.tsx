"use client";
import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { useReducedMotionSafe } from "./motion";

export function Card({ children, className = "", onClick }: {
  children: ReactNode; className?: string; onClick?: () => void;
}) {
  const reduce = useReducedMotionSafe();
  return (
    <motion.div
      onClick={onClick}
      whileHover={reduce ? undefined : { y: -2 }}
      transition={{ type: "spring", stiffness: 320, damping: 26 }}
      className={"rounded-xl2 border border-border bg-panel/70 p-4 backdrop-blur-sm " + (onClick ? "cursor-pointer " : "") + className}
    >
      {children}
    </motion.div>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <div className="text-[10px] font-semibold uppercase tracking-label text-dim">{children}</div>;
}

export function Pill({ children, tone = "muted" }: {
  children: ReactNode; tone?: "emerald" | "rose" | "gold" | "muted";
}) {
  const map = {
    emerald: "bg-emerald/10 text-emerald",
    rose: "bg-rose/10 text-rose",
    gold: "bg-gold/10 text-gold-soft",
    muted: "bg-white/5 text-muted",
  } as const;
  return <span className={"rounded-md px-2 py-0.5 text-[11px] " + map[tone]}>{children}</span>;
}

export function Delta({ v, className = "" }: { v: number | null; className?: string }) {
  if (v == null) return <span className="text-dim">--</span>;
  const cls = v > 0 ? "text-emerald" : v < 0 ? "text-rose" : "text-muted";
  const arrow = v > 0 ? "▲" : v < 0 ? "▼" : "•";
  return <span className={"tnum " + cls + " " + className}>{arrow} {Math.abs(v).toFixed(2)}%</span>;
}

export function Spark({ data, up = true, w = 96, h = 28 }: {
  data?: number[]; up?: boolean; w?: number; h?: number;
}) {
  if (!data || data.length < 2) return <svg width={w} height={h} />;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const pts = data
    .map((d, i) => (i / (data.length - 1)) * w + "," + (h - ((d - min) / span) * (h - 4) - 2))
    .join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={up ? "#34d399" : "#fb7185"} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" opacity={0.9} />
    </svg>
  );
}

export function EmptyState({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="rounded-xl2 border border-dashed border-border p-10 text-center">
      <div className="text-sm text-muted">{title}</div>
      {sub && <div className="mt-1 text-xs text-dim">{sub}</div>}
    </div>
  );
}

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M3 18L9 6l3 6 3-9 6 15" stroke="#e9ebed" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="20" cy="6" r="2" fill="#34d399" />
    </svg>
  );
}