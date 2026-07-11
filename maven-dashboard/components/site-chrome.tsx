"use client";

// The dashboard's shared chrome (Nav + content rail + footer) — extracted from
// layout.tsx so /login can render as a genuine bare, full-screen page with
// nothing else in the DOM. Overlaying the sign-in gate on top of live page
// content (the old approach) is what let the chat page bleed through behind
// it; a route with no other content mounted can't bleed through anything.

import { usePathname } from "next/navigation";
import { type ReactNode } from "react";
import { Nav } from "./client";

export function SiteChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname?.startsWith("/login")) return <>{children}</>;

  return (
    <div className="mx-auto max-w-6xl px-5 sm:px-8">
      <Nav />
      <main className="pb-16">{children}</main>
      <footer className="mt-4 flex flex-col gap-4 border-t border-hairline py-6 text-xs leading-relaxed text-dim sm:flex-row sm:items-center sm:justify-between">
        <div>
          Research tool. Not investment advice. Paper-traded results, not real money.
          <br />
          Enhanced F+ engine commit 6ced078 (frozen). Built for personal research; not registered
          with SEBI.
        </div>
        {/* press feedback per PRESS convention (components/motion.tsx); the
            composed transition list keeps the color fade alongside the scale */}
        <div className="flex shrink-0 items-center gap-3">
          <a href="https://instagram.com/try.maven" target="_blank" rel="noopener noreferrer" aria-label="Maven on Instagram"
            className="grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors duration-150 hover:border-emerald/40 hover:text-emerald motion-safe:transition-[color,border-color,transform] motion-safe:active:scale-[0.97]">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" /></svg>
          </a>
          <a href="https://twitter.com/trymavenai" target="_blank" rel="noopener noreferrer" aria-label="Maven on X (Twitter)"
            className="grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors duration-150 hover:border-emerald/40 hover:text-emerald motion-safe:transition-[color,border-color,transform] motion-safe:active:scale-[0.97]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 2H22l-7.5 8.6L23.3 22H16.7l-5.2-6.8L5.5 22H2.4l8.1-9.2L1 2h6.8l4.7 6.2L18.9 2Zm-1.2 18.2h1.7L7.4 3.7H5.6l12.1 16.5Z" /></svg>
          </a>
        </div>
      </footer>
    </div>
  );
}
