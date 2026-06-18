import type { Metadata } from "next";
import { Explainer } from "@/components/explainer";

export const metadata: Metadata = {
  title: "Maven — How It Works",
  description:
    "Index-like returns at roughly half the drawdown — F+ survived covid at -27% while the market fell -38%. Risk management is the edge. Research tool, paper-traded, not advice.",
};

// "How it works" is the landing page. The live paper portfolio lives at /portfolio.
export default function HomePage() {
  return <Explainer />;
}
