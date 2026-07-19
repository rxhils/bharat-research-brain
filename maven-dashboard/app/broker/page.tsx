import type { Metadata } from "next";

import { BrokerGrid } from "@/components/broker/broker-grid";
import { BrokerHero } from "@/components/broker/broker-hero";
import { BrokerJourney } from "@/components/broker/broker-journey";

export const metadata: Metadata = {
  title: "Broker — Maven",
  description:
    "Connect your broker read-only. Maven sees your holdings, never trades.",
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
