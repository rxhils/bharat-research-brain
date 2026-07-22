import type { Metadata } from "next";
import { Explainer } from "@/components/explainer";
import { LandingAuthFlow } from "@/components/auth/landing-auth-flow";

export const metadata: Metadata = {
  // absolute: bypasses the layout's "%s | Maven" template so the front door
  // carries the exact brand title from the SEO plan.
  title: { absolute: "Maven — AI Research for Indian Markets | TryMaven" },
  description:
    "Index-like returns at roughly half the drawdown — Enhanced F+ survived covid at -13.88% while the market fell ~-38%. Risk management is the edge. Research tool, paper-traded, not advice.",
  alternates: {
    canonical: "https://www.trymaven.in/",
  },
};

// "How it works" is the landing page. The live paper portfolio lives at /portfolio.
export default function HomePage() {
  return (
    <>
      {/* Intro (unchanged) → Google gate for unauthenticated visitors. The
          "How It Works" explainer stays behind, fully intact. */}
      <LandingAuthFlow />
      <Explainer />
    </>
  );
}
