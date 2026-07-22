import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found" };

// Branded 404 — renders inside SiteChrome, so the nav, route transition, and
// the footer disclaimer come for free. Grammar matches the site: mono figure,
// Fraunces serif headline with one italic emphasis word, single emerald link.
export default function NotFound() {
  return (
    <div className="flex min-h-[55vh] flex-col items-start justify-center py-16">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald">
        <span className="text-dim">404{" — "}</span>Not found
      </p>
      <h1 className="mt-3 max-w-2xl text-balance font-serif text-[clamp(2rem,1rem+3.5vw,3.5rem)] leading-[1.05] tracking-[-0.02em] text-ink">
        This page doesn&apos;t <em className="italic text-emerald">exist</em>.
      </h1>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-muted">
        The address may be mistyped, or the page has moved. Everything Maven
        publishes is reachable from the home page.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-lg border border-emerald/30 px-4 py-2 text-sm text-emerald transition-[color,border-color,box-shadow] duration-150 hover:border-emerald/50 hover:bg-emerald/10 hover:shadow-[0_0_20px_-6px_rgba(52,211,153,0.5)] motion-safe:transition-[color,border-color,box-shadow,transform] motion-safe:active:scale-[0.97] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald/60"
      >
        Back to how it works
      </Link>
    </div>
  );
}
