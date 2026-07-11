"use client";

// Chat gate: an unauthenticated visitor who opens /chat gets the Maven Google
// gate over the (untouched) chat UI. Signing in or continuing as guest flips
// hasAccess → the gate closes → the existing chat is revealed. The chat markup
// itself is not modified; this is purely an additive overlay.

import { MavenGoogleGate } from "./MavenGoogleGate";
import { useMavenAuth } from "./useMavenAuth";

export function ChatAuthGate() {
  const auth = useMavenAuth();

  return (
    <MavenGoogleGate
      open={auth.ready && !auth.hasAccess}
      showGuest
      onGoogleSignIn={auth.signInWithGoogle}
      // Persist at the end of the confirmation; hasAccess then flips true, the
      // gate closes, and the chat rendered behind it becomes visible.
      onComplete={auth.markSignedIn}
      onGuest={auth.continueAsGuest}
      onReset={auth.signOut}
    />
  );
}
