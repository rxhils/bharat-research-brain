"use client";

// The actual /login page content. A genuine full-screen route (see
// app/login/page.tsx) — nothing else is mounted in the DOM, so the gate can
// never bleed through page content behind it (the bug with the old in-place
// overlay approach). Already-authenticated visitors are bounced to `next`.

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MavenGoogleGate } from "./MavenGoogleGate";
import { useMavenAuth } from "./useMavenAuth";

function LoginContent() {
  const router = useRouter();
  const params = useSearchParams();
  const auth = useMavenAuth();

  const nextParam = params.get("next");
  const next = nextParam && nextParam.startsWith("/") ? nextParam : "/chat";
  const authError = params.get("auth_error") ? "Google sign-in didn't complete. Please try again." : null;

  // Already signed in (or already a guest) and landed here directly — send
  // them straight on instead of showing the sign-in screen again.
  useEffect(() => {
    if (auth.ready && auth.hasAccess) router.replace(next);
  }, [auth.ready, auth.hasAccess, next, router]);

  return (
    <MavenGoogleGate
      open
      showGuest
      initialError={authError}
      onGoogleSignIn={auth.signInWithGoogle}
      onComplete={() => {
        auth.markSignedIn();
        router.replace(next);
      }}
      onGuest={() => {
        auth.continueAsGuest();
        router.replace(next);
      }}
      onReset={auth.signOut}
    />
  );
}

export function LoginClient() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}
