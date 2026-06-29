import type { Metadata, Viewport } from "next";
import { type ReactNode } from "react";
import { Hanken_Grotesk, JetBrains_Mono, Fraunces } from "next/font/google";
import "./globals.css";

const sans = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
const serif = Fraunces({ subsets: ["latin"], variable: "--font-serif", display: "swap", weight: ["300", "400", "500", "600"] });

export const metadata: Metadata = {
  title: "Maven - India market intelligence",
  description: "An India-first AI market intelligence workspace. Educational, not investment advice.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={sans.variable + " " + mono.variable + " " + serif.variable}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}