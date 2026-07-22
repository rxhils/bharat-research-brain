import type { Metadata, Viewport } from "next";
import { type ReactNode } from "react";
import { Hanken_Grotesk, JetBrains_Mono, Fraunces } from "next/font/google";
import "./globals.css";
import "lenis/dist/lenis.css";
import { SiteChrome } from "@/components/site-chrome";
import { SmoothScroll } from "@/components/smooth-scroll";

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
  metadataBase: new URL("https://www.trymaven.in"),
  title: {
    default: "Maven — AI Research for Indian Markets | TryMaven",
    template: "%s | Maven",
  },
  description:
    "Maven (TryMaven) is an AI research workspace for Indian markets — NSE/BSE market context, portfolio styles, read-only broker sync, and paper-traded strategy research. Not investment advice.",
  keywords: [
    "Maven", "TryMaven", "try maven", "Maven India", "Indian stock market AI",
    "NSE research", "BSE research", "India market research", "portfolio research India",
  ],
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    url: "https://www.trymaven.in",
    siteName: "Maven",
    title: "Maven — AI Research for Indian Markets",
    description:
      "Ask better questions about NSE/BSE. Portfolio styles, read-only broker sync, paper-traded research. Not investment advice.",
    images: [{ url: "/og-default.png", width: 1200, height: 630, alt: "Maven — Beats the market. Half the fall." }],
  },
  twitter: {
    card: "summary_large_image",
    site: "@trymavenai",
    title: "Maven — AI Research for Indian Markets",
    description: "Ask better questions about NSE/BSE. Research, not investment advice.",
  },
  icons: { icon: "/icon.svg" },
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "Maven", statusBarStyle: "black-translucent" },
};

// Brand entity for Google: ties "Maven" / "TryMaven" to this domain so brand
// queries resolve here. Rendered once, site-wide.
const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://www.trymaven.in/#org",
      name: "Maven",
      alternateName: ["TryMaven", "Maven India"],
      url: "https://www.trymaven.in",
      logo: "https://www.trymaven.in/icon.svg",
      sameAs: ["https://twitter.com/trymavenai", "https://instagram.com/try.maven"],
    },
    {
      "@type": "WebSite",
      "@id": "https://www.trymaven.in/#site",
      name: "Maven — AI Research for Indian Markets",
      alternateName: "TryMaven",
      url: "https://www.trymaven.in",
      publisher: { "@id": "https://www.trymaven.in/#org" },
    },
  ],
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
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
        <SmoothScroll>
          <SiteChrome>{children}</SiteChrome>
        </SmoothScroll>
      </body>
    </html>
  );
}
