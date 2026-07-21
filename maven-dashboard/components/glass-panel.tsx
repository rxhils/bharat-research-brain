// GlassPanel — the house glass card, extracted from the chat-view / broker-grid
// pattern so every page shares one recipe: gradient p-px hairline wrapper
// (brighter top edge = overhead light), low-alpha white fill + backdrop blur
// with saturate (pure blur grays the backdrop out), inner top highlight, and
// an optional 2% noise overlay to kill banding on dark gradients.
//
// Server-component-safe: no hooks, no browser APIs — usable from RSC trees.
// Budget note: each panel is one backdrop-filter; cap ~6 per page.

import type { ElementType, ReactNode } from "react";

/** Hairline-gradient wrapper per glow tone (brighter top edge). */
const GLOW_WRAP: Record<"none" | "emerald" | "gold", string> = {
  none: "bg-gradient-to-b from-white/[0.12] via-white/[0.05] to-transparent",
  emerald:
    "bg-gradient-to-b from-emerald/35 via-white/[0.06] to-transparent shadow-[0_0_34px_-12px_rgba(52,211,153,0.35)]",
  gold:
    "bg-gradient-to-b from-gold/35 via-white/[0.06] to-transparent shadow-[0_0_34px_-12px_rgba(201,169,97,0.3)]",
};

export interface GlassPanelProps {
  children: ReactNode;
  /** Classes for the outer p-px wrapper (sizing, margin, radius overrides). */
  className?: string;
  /** Classes for the inner surface (padding, layout). */
  innerClassName?: string;
  /** Hairline tint + ambient shadow: none (neutral white) | emerald | gold. */
  glow?: "none" | "emerald" | "gold";
  /** Adds the 2% feTurbulence noise overlay (see .noise-overlay in globals.css). */
  noise?: boolean;
  /** Rendered element for the outer wrapper (e.g. "section", "article"). */
  as?: ElementType;
}

/** House glass card: gradient hairline wrapper + blurred/saturated glass surface. */
export function GlassPanel({
  children,
  className = "",
  innerClassName = "",
  glow = "none",
  noise = false,
  as: Tag = "div",
}: GlassPanelProps) {
  return (
    <Tag className={`relative rounded-2xl p-px ${GLOW_WRAP[glow]}${className ? ` ${className}` : ""}`}>
      <div
        className={`relative h-full overflow-hidden rounded-[inherit] bg-white/[0.05] backdrop-blur-[14px] backdrop-saturate-[1.7] shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]${innerClassName ? ` ${innerClassName}` : ""}`}
      >
        {noise && <div className="noise-overlay" aria-hidden />}
        {children}
      </div>
    </Tag>
  );
}
