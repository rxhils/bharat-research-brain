import type { Metadata, Viewport } from "next";
import { type ReactNode } from "react";
import { Hanken_Grotesk, JetBrains_Mono, Fraunces } from "next/font/google";
import "./globals.css";
import { SiteChrome } from "@/components/site-chrome";

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
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "Maven", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // let the app paint under the iOS notch/home bar; safe-area vars in globals.css
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${serif.variable}`}>
      <body className="min-h-screen">
        <SiteChrome>{children}</SiteChrome>
      </body>
    </html>
  );
}
