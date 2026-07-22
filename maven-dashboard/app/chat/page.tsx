import type { Metadata } from "next";
import { ChatShell } from "@/components/chat-shell";
import { MarketTicker } from "@/components/market-ticker";
import { ChatAuthGate } from "@/components/auth/chat-auth-gate";
import { AccountChip } from "@/components/auth/account-chip";

export const metadata: Metadata = {
  title: "Ask AI About Indian Stocks, Sectors & Market Moves",
  description:
    "Chat with Maven AI about Indian stocks, sectors, macro trends and market moves on NSE/BSE, with cited sources, official filings and stated limitations.",
  alternates: { canonical: "https://www.trymaven.in/chat" },
  openGraph: {
    title: "Ask AI About Indian Stocks, Sectors & Market Moves",
    description:
      "Chat with Maven AI about Indian stocks, sectors, macro trends and market moves on NSE/BSE, with cited sources, official filings and stated limitations.",
    url: "https://www.trymaven.in/chat",
  },
  twitter: {
    title: "Ask AI About Indian Stocks, Sectors & Market Moves",
    description:
      "Chat with Maven AI about Indian stocks, sectors, macro trends and market moves on NSE/BSE, with cited sources, official filings and stated limitations.",
  },
};

export default function ChatPage() {
  return (
    <div className="space-y-4 sm:space-y-5">
      <MarketTicker />
      <div>
        <div className="flex items-center justify-between gap-3">
          {/* Technical mono eyebrow (house label spec) — the only brand text up here;
              the medallion below is the page's single brand mark. */}
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-dim sm:text-[11px]">AI copilot &middot; India markets</div>
          {/* signed-in account + Log out */}
          <AccountChip />
        </div>
        {/* Duplicate 8×8 logo tile removed — brand appears exactly once above the fold (the medallion). */}
        <h1 className="mt-1.5 font-serif text-[clamp(1.5rem,1rem+1.5vw,1.875rem)] leading-tight text-ink">Ask Maven</h1>
        <p className="mt-1.5 max-w-2xl text-[0.8rem] leading-relaxed text-muted sm:text-sm">
          Educational market context for NSE/BSE &mdash; what moved and why it matters. Not investment advice.
        </p>
      </div>
      <ChatShell />
      {/* Unauthenticated visitors get the Google gate over the (untouched) chat;
          signing in or continuing as guest reveals it. */}
      <ChatAuthGate />
    </div>
  );
}