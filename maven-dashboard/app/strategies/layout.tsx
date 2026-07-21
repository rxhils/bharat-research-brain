import type { Metadata } from "next";
import { type ReactNode } from "react";

// page.tsx in this route is a Client Component ("use client"), and Next.js
// disallows exporting `metadata` from a Client Component. This layout is the
// standard Next.js way to attach route-segment metadata in that situation —
// it renders children unchanged and adds no visible markup of its own.

const title = "Indian Equity Research Models: Live & In Validation";
const description =
  "Compare Maven's three live, backtested Indian equity strategies by return, drawdown, and COVID performance, plus more strategy models still in validation.";
const url = "https://www.trymaven.in/strategies";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

export default function StrategiesLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
