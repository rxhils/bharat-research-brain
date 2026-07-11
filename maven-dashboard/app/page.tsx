import type { Metadata } from "next";
import { Explainer } from "@/components/explainer";
import { LandingAuthFlow } from "@/components/auth/landing-auth-flow";

export const metadata: Metadata = {
  title: "Maven — How It Works",
  description:
    "Index-like returns at roughly half the drawdown — F+ survived covid at -27% while the market fell -38%. Risk management is the edge. Research tool, paper-traded, not advice.",
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
