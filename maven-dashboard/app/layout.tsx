import type { Metadata, Viewport } from "next";
import { type ReactNode } from "react";
import { Hanken_Grotesk, JetBrains_Mono, Fraunces } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/client";

const sans = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
// editorial serif, used only on the /how-it-works explainer headlines
const serif = Fraunces({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  style: ["normal", "italic"],
  weight: ["300", "400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Maven — Bharat Brain",
  description: "Forward paper-trading dashboard for the Enhanced F+ risk engine.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${serif.variable}`}>
      <body className="min-h-screen">
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
            <div className="flex shrink-0 items-center gap-3">
              <a href="https://instagram.com/try.maven" target="_blank" rel="noopener noreferrer" aria-label="Maven on Instagram"
                className="grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors hover:border-emerald/40 hover:text-emerald">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" /></svg>
              </a>
              <a href="https://twitter.com/trymavenai" target="_blank" rel="noopener noreferrer" aria-label="Maven on X (Twitter)"
                className="grid h-8 w-8 place-items-center rounded-full border border-hairline text-dim transition-colors hover:border-emerald/40 hover:text-emerald">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 2H22l-7.5 8.6L23.3 22H16.7l-5.2-6.8L5.5 22H2.4l8.1-9.2L1 2h6.8l4.7 6.2L18.9 2Zm-1.2 18.2h1.7L7.4 3.7H5.6l12.1 16.5Z" /></svg>
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
