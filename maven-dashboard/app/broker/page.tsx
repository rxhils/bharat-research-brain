import type { Metadata } from "next";

import { BrokerGrid } from "@/components/broker/broker-grid";
import { BrokerHero } from "@/components/broker/broker-hero";
import { BrokerJourney } from "@/components/broker/broker-journey";

export const metadata: Metadata = {
  title: "Connect a Broker — Read-Only, No Trading Access",
  description:
    "Connect Zerodha or HDFC Sky to Maven read-only — Groww, Upstox, and more brokers coming soon. Holdings sync with AES-encrypted tokens; Maven never trades.",
  alternates: { canonical: "https://www.trymaven.in/broker" },
  openGraph: {
    title: "Connect a Broker — Read-Only, No Trading Access",
    description:
      "Connect Zerodha or HDFC Sky to Maven read-only — Groww, Upstox, and more brokers coming soon. Holdings sync with AES-encrypted tokens; Maven never trades.",
    url: "https://www.trymaven.in/broker",
  },
  twitter: {
    title: "Connect a Broker — Read-Only, No Trading Access",
    description:
      "Connect Zerodha or HDFC Sky to Maven read-only — Groww, Upstox, and more brokers coming soon. Holdings sync with AES-encrypted tokens; Maven never trades.",
  },
};

export default function BrokerPage() {
  return (
    <div className="space-y-16 sm:space-y-24">
      <BrokerHero />
      <BrokerGrid />
      <BrokerJourney />
    </div>
  );
}
