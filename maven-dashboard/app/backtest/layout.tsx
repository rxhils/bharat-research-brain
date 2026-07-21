import type { Metadata } from "next";
import type { ReactNode } from "react";

// page.tsx in this route is a Client Component ("use client" — it uses Recharts
// + framer-motion hooks), and Next.js disallows exporting `metadata` from a
// Client Component. This sibling layout is the Server Component that carries
// the route's metadata; it renders {children} unchanged and does nothing else.

const title = "Enhanced F+ Backtest: Bull Run vs COVID Stress";
const description =
  "Enhanced F+ walk-forward and capital backtests vs the Nifty 500 TRI across the 2021–2026 bull run and 2017–2020 COVID stress era, plus methodology and caveats.";
const url = "https://www.trymaven.in/backtest";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

export default function BacktestLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
