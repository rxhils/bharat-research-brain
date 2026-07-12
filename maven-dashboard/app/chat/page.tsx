import type { Metadata } from "next";
import { ChatShell } from "@/components/chat-shell";
import { MarketStatusLine } from "@/components/market-status-line";
import { ChatAuthGate } from "@/components/auth/chat-auth-gate";
import { AccountChip } from "@/components/auth/account-chip";

export const metadata: Metadata = { title: "Chat - Maven" };

// One quiet status row (calm market line + account), then the workspace.
// The old stack — scrolling ticker, eyebrow label, page title, description —
// competed with the composer; the empty-state headline carries the page now.
export default function ChatPage() {
  return (
    <div className="space-y-5 sm:space-y-6">
      <div className="flex items-center justify-between gap-3 pt-1">
        <MarketStatusLine />
        <AccountChip />
      </div>
      <ChatShell />
      {/* Unauthenticated visitors are redirected to /login. */}
      <ChatAuthGate />
    </div>
  );
}
