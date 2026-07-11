"use client";

// Chat gate: an unauthenticated visitor who opens /chat is sent to the
// dedicated /login page (not shown as an overlay on top of the live chat —
// that was the bug where the page behind could bleed through). While the
// redirect is in flight, a plain opaque screen blocks the one-frame flash of
// chat content; once auth.hasAccess flips true, this renders nothing.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMavenAuth } from "./useMavenAuth";

export function ChatAuthGate() {
  const auth = useMavenAuth();
  const router = useRouter();
  const shouldGate = auth.ready && !auth.hasAccess;

  useEffect(() => {
    if (shouldGate) router.replace("/login?next=/chat");
  }, [shouldGate, router]);

  if (!shouldGate) return null;
  return <div className="fixed inset-0 z-[90] bg-bg" aria-hidden />;
}
