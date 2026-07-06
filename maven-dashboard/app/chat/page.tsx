import type { Metadata } from "next";
import { ChatShell } from "@/components/chat-shell";
import { MarketTicker } from "@/components/market-ticker";

export const metadata: Metadata = { title: "Chat - Maven" };

export default function ChatPage() {
  return (
    <div className="space-y-4 sm:space-y-5">
      <MarketTicker />
      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-dim sm:text-[11px]">AI copilot &middot; India markets</div>
        <div className="mt-1.5 flex items-center gap-2.5">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-[28%]" style={{ background: "#0d0e11" }}>
            <svg width="22" height="22" viewBox="0 0 100 100" fill="none" role="img" aria-label="Maven">
              <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="89" cy="17" r="8" fill="#34d399" />
            </svg>
          </span>
          <h1 className="font-serif text-2xl text-ink">Ask Maven</h1>
        </div>
        <p className="mt-1.5 max-w-2xl text-[0.8rem] leading-relaxed text-muted sm:text-sm">
          Educational market context for NSE/BSE &mdash; what moved and why it matters. Not investment advice.
        </p>
      </div>
      <ChatShell />
    </div>
  );
}