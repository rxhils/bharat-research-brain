"use client";

// Landing sequence: preserve the existing intro exactly, then reveal the Google
// gate for unauthenticated visitors once the intro finishes (played, skipped, or
// already-seen). Authenticated / guest users skip straight past — the "How It
// Works" explainer (rendered behind, in app/page.tsx) stays fully visible.
//
//   app opens → IntroOverlay (unchanged) → onFinished → gate (if no access)
//             → Continue with Google → /chat
//
// The gate here is dismissible (Esc / backdrop / "Continue as guest") so the
// marketing page is never trapped behind it.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { IntroOverlay } from "../intro";
import { MavenGoogleGate } from "./MavenGoogleGate";
import { useMavenAuth } from "./useMavenAuth";

// Dismissal is remembered for the tab session so a returning visitor can read
// the marketing page without re-dismissing the gate on every reload.
const DISMISSED_KEY = "maven.gate.dismissed.v1";

export function LandingAuthFlow() {
  const router = useRouter();
  const auth = useMavenAuth();
  const [introDone, setIntroDone] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    try {
      if (window.sessionStorage.getItem(DISMISSED_KEY)) setDismissed(true);
    } catch {
      /* ignore */
    }
    // A failed OAuth callback bounces to /?auth_error=1 — surface it in the
    // gate (and force the gate open past any remembered dismissal), then strip
    // the param so a refresh doesn't re-show it.
    const params = new URLSearchParams(window.location.search);
    if (params.get("auth_error")) {
      setAuthError("Google sign-in didn't complete. Please try again.");
      setDismissed(false);
      params.delete("auth_error");
      const qs = params.toString();
      window.history.replaceState(null, "", window.location.pathname + (qs ? `?${qs}` : ""));
    }
  }, []);

  const dismiss = () => {
    setDismissed(true);
    try {
      window.sessionStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      /* ignore */
    }
  };

  const gateOpen = auth.ready && introDone && !auth.hasAccess && !dismissed;

  return (
    <>
      {/* IntroOverlay is unchanged visually; onFinished fires when the video
          ends / Skip is pressed, or immediately if the intro was already seen. */}
      <IntroOverlay onFinished={() => setIntroDone(true)} />

      <MavenGoogleGate
        open={gateOpen}
        dismissible
        showGuest
        initialError={authError}
        onGoogleSignIn={auth.signInWithGoogle}
        onComplete={() => {
          auth.markSignedIn();
          router.push("/chat");
        }}
        onGuest={auth.continueAsGuest}
        onReset={auth.signOut}
        onDismiss={dismiss}
      />
    </>
  );
}
