"use client";

// The dashboard's shared chrome (Nav + content rail + footer) — extracted from
// layout.tsx so /login can render as a genuine bare, full-screen page with
// nothing else in the DOM. Overlaying the sign-in gate on top of live page
// content (the old approach) is what let the chat page bleed through behind
// it; a route with no other content mounted can't bleed through anything.

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode } from "react";
import { Logo, Nav } from "./client";
import { EASE, useReducedMotionSafe } from "./motion";

// House focus ring (matches components/client.tsx NAV_FOCUS).
const FOOT_FOCUS = "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60";

// Slim nav echo in the footer — every page gets a second path to the core
// routes without scrolling back up. Mirrors the Nav's tab set + Backtest.
const FOOTER_LINKS: { href: string; label: string }[] = [
  { href: "/chat", label: "Chat" },
  { href: "/", label: "How it works" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/broker", label: "Broker" },
  { href: "/trades", label: "Trades" },
  { href: "/strategies", label: "Strategies" },
  { href: "/backtest", label: "Backtest" },
];

export function SiteChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduce = useReducedMotionSafe();
  if (pathname?.startsWith("/login")) return <>{children}</>;

  return (
    <div className="mx-auto max-w-6xl px-5 sm:px-8">
      <Nav />
      {/* Route-level content transition: the nav pill GLIDES between tabs, so
          the content below shouldn't hard-cut. Keyed by pathname → one gentle
          rise+fade per navigation, matched to the pill's spring timing.
          Skipped under reduced motion (decorative, not a signature moment). */}
      <motion.main
        key={pathname}
        className="pb-16"
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: EASE }}
      >
        {children}
      </motion.main>
      <footer className="mt-4 border-t border-hairline py-6 text-xs leading-relaxed text-dim">
        {/* brand mark + nav echo + socials */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className={`flex w-fit items-center gap-2 rounded-lg text-muted transition-colors duration-150 hover:text-ink motion-safe:transition-[color,transform] motion-safe:active:scale-[0.97] ${FOOT_FOCUS}`}>
            <Logo size={22} />
            <span className="text-[11px] tracking-[0.2em]">MAVEN</span>
          </Link>
          <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            {FOOTER_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded text-dim transition-colors duration-150 hover:text-muted motion-safe:transition-[color,transform] motion-safe:active:scale-[0.97] ${FOOT_FOCUS}`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          {/* press feedback per PRESS convention (components/motion.tsx); the
              composed transition list keeps the color fade alongside the scale */}
          <div className="flex shrink-0 items-center gap-3">
            <a href="https://instagram.com/try.maven" target="_blank" rel="noopener noreferrer" aria-label="Maven on Instagram"
              className={`grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors duration-150 hover:border-emerald/40 hover:text-emerald motion-safe:transition-[color,border-color,transform] motion-safe:active:scale-[0.97] ${FOOT_FOCUS}`}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" /></svg>
            </a>
            <a href="https://twitter.com/trymavenai" target="_blank" rel="noopener noreferrer" aria-label="Maven on X (Twitter)"
              className={`grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors duration-150 hover:border-emerald/40 hover:text-emerald motion-safe:transition-[color,border-color,transform] motion-safe:active:scale-[0.97] ${FOOT_FOCUS}`}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 2H22l-7.5 8.6L23.3 22H16.7l-5.2-6.8L5.5 22H2.4l8.1-9.2L1 2h6.8l4.7 6.2L18.9 2Zm-1.2 18.2h1.7L7.4 3.7H5.6l12.1 16.5Z" /></svg>
            </a>
          </div>
        </div>
        {/* the one regulatory line every page shares — do not remove */}
        <div className="mt-4 border-t border-hairline/60 pt-4">
          Research tool. Not investment advice. Paper-traded results, not real money.
          <br />
          Enhanced F+ engine commit 6ced078 (frozen). Built for personal research; not registered
          with SEBI.
        </div>
      </footer>
    </div>
  );
}
