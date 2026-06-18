import type { Metadata } from "next";
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
  title: "Maven — Bharat Brain F+",
  description: "Forward paper-trading dashboard for the F+ risk engine.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${serif.variable}`}>
      <body className="min-h-screen">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Nav />
          <main className="pb-16">{children}</main>
          <footer className="mt-4 border-t border-hairline py-6 text-xs leading-relaxed text-dim">
            Research tool. Not investment advice. Paper-traded results, not real money.
            <br />
            F+ engine commit 57e72d5 (frozen). Built for personal research; not registered
            with SEBI.
          </footer>
        </div>
      </body>
    </html>
  );
}
