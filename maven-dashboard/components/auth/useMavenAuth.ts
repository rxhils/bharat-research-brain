"use client";

// Auth state for the Maven Google gate. Two modes, chosen automatically:
//
//   • supabase mode  — when NEXT_PUBLIC_SUPABASE_* are set. Real Google OAuth via
//                      Supabase; signed-in state is derived from the live session.
//   • mock mode      — when Supabase is not configured. A localStorage placeholder
//                      flag so the UI flow stays fully demoable with no backend.
//
// The gate branches on the result of signInWithGoogle(): a real sign-in redirects
// the browser to Google; a mock sign-in returns { mock: true } and the gate plays
// its local confirmation animation instead.

import { useCallback, useEffect, useState } from "react";
import { getSupabaseBrowser, supabaseConfigured } from "@/lib/supabase/client";

const AUTH_KEY = "maven.auth.mock.v1";
const GUEST_KEY = "maven.auth.guest.v1";
const GUEST_MSG_KEY = "maven.guest.chatcount.v1";
/** Guests (not signed in) get this many messages per calendar day before the
 *  chat asks them to sign in with Google — an intentional conversion nudge. */
const GUEST_DAILY_LIMIT = 3;

// Cross-instance sync for the localStorage-backed flags: several components
// (gate, account chip) each call useMavenAuth, and Supabase's onAuthStateChange
// only covers real sessions — guest/mock changes must be broadcast by hand so
// e.g. "Log out" in the chip immediately reopens the gate.
const authListeners = new Set<() => void>();
function notifyAuthChange() {
  authListeners.forEach((fn) => fn());
}

/** Result of an attempted sign-in. `mock` → play the local confirmation; `error`
 *  → surface it and return to idle; neither → the browser is redirecting. */
export type SignInResult = { error?: string; mock?: boolean };

function readFlag(key: string): boolean {
  try {
    return typeof window !== "undefined" && !!window.localStorage.getItem(key);
  } catch {
    return false;
  }
}

function todayKey(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Guest messages sent so far today. Scoped by calendar day — a stored count
 *  from a previous day reads as 0 (the limit resets automatically). */
function readGuestCount(): number {
  try {
    const raw = window.localStorage.getItem(GUEST_MSG_KEY);
    if (!raw) return 0;
    const parsed = JSON.parse(raw) as { date?: string; count?: number };
    return parsed.date === todayKey() && typeof parsed.count === "number" ? parsed.count : 0;
  } catch {
    return 0;
  }
}

export interface MavenAuth {
  /** false on server + first client render (hydration-safe); true after the
   *  session/flag has been resolved. */
  ready: boolean;
  isSignedIn: boolean;
  isGuest: boolean;
  /** Signed in OR continuing as guest — gate chat/features on this. */
  hasAccess: boolean;
  /** Google account email of the live Supabase session; null in mock/guest mode. */
  userEmail: string | null;
  /** Google display name / profile photo from the session's user metadata. */
  userName: string | null;
  userAvatarUrl: string | null;
  mode: "supabase" | "mock";
  /** Guest messages sent today (resets at midnight, local time). */
  guestMessagesUsed: number;
  guestMessagesRemaining: number;
  /** True once a signed-out guest has used today's free messages — the chat
   *  should stop calling the API and prompt sign-in instead. Always false for
   *  a signed-in user, regardless of message count. */
  guestLimitReached: boolean;
  /** Call once per guest message actually sent (not on signed-in sends). */
  recordGuestMessage: () => void;
  /** Kicks off Google sign-in. Real mode redirects to Google; mock mode returns
   *  { mock: true } so the gate can animate a placeholder confirmation. */
  signInWithGoogle: () => Promise<SignInResult>;
  /** Mock-mode completion (persist the placeholder flag). No-op meaning in
   *  supabase mode, where the session is the source of truth. */
  markSignedIn: () => void;
  continueAsGuest: () => void;
  signOut: () => void;
}

export function useMavenAuth(): MavenAuth {
  // Env vars are inlined at build time, so this is stable across renders.
  const mode: "supabase" | "mock" = supabaseConfigured() ? "supabase" : "mock";
  const [ready, setReady] = useState(false);
  const [isSignedIn, setSignedIn] = useState(false);
  const [isGuest, setGuest] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [userAvatarUrl, setUserAvatarUrl] = useState<string | null>(null);
  const [guestUsed, setGuestUsed] = useState(0);

  // Google puts the profile on user_metadata (full_name / name, avatar_url /
  // picture) — harvest defensively since the exact keys vary by provider.
  const applySessionUser = (user: { email?: string; user_metadata?: Record<string, unknown> } | null | undefined) => {
    setUserEmail(user?.email ?? null);
    const meta = (user?.user_metadata ?? {}) as Record<string, unknown>;
    const name = meta.full_name ?? meta.name;
    const avatar = meta.avatar_url ?? meta.picture;
    setUserName(typeof name === "string" && name ? name : null);
    setUserAvatarUrl(typeof avatar === "string" && avatar ? avatar : null);
  };

  useEffect(() => {
    let active = true;
    setGuest(readFlag(GUEST_KEY));
    setGuestUsed(readGuestCount());

    // Re-read the local flags whenever any other hook instance mutates them
    // (e.g. ChatView records a guest message; ChatAuthGate's own instance
    // needs to see the new count to know the limit was hit).
    const onPeerChange = () => {
      if (!active) return;
      setGuest(readFlag(GUEST_KEY));
      setGuestUsed(readGuestCount());
      if (mode === "mock") setSignedIn(readFlag(AUTH_KEY));
    };
    authListeners.add(onPeerChange);

    if (mode === "mock") {
      setSignedIn(readFlag(AUTH_KEY));
      setReady(true);
      return () => {
        active = false;
        authListeners.delete(onPeerChange);
      };
    }

    // supabase mode: derive signed-in state from the live session and keep it in
    // sync (e.g. after the OAuth callback lands the user back on /chat).
    //
    // Readiness races three sources, because supabase-js's getSession() can hang
    // indefinitely on its internal navigator lock (observed in real Chrome, not
    // just headless): (1) the INITIAL_SESSION event, which fires immediately on
    // subscribe; (2) getSession(); (3) a timeout that defaults to signed-out so
    // the gate is never blocked by auth plumbing. First one wins.
    const supabase = getSupabaseBrowser();
    let ready = false;
    const markReady = () => {
      if (!active || ready) return;
      ready = true;
      setReady(true);
    };

    // Signed-in state is ALWAYS updated when a source resolves — even after the
    // readiness timeout — so a slow getSession() can only delay, never lose, a
    // real session: the gate closes itself the moment the session lands.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      setSignedIn(!!session?.user);
      applySessionUser(session?.user);
      markReady();
    });
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (!active) return;
        setSignedIn(!!data.session?.user);
        applySessionUser(data.session?.user);
        markReady();
      })
      .catch(() => markReady());
    // Timeout is a readiness fallback only — it never forces signed-out.
    const readyTimeout = window.setTimeout(markReady, 2500);

    return () => {
      active = false;
      authListeners.delete(onPeerChange);
      window.clearTimeout(readyTimeout);
      sub.subscription.unsubscribe();
    };
  }, [mode]);

  const signInWithGoogle = useCallback(async (): Promise<SignInResult> => {
    if (mode === "mock") {
      // No backend configured — the gate plays its mock confirmation instead.
      return { mock: true };
    }
    const supabase = getSupabaseBrowser();
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        // Route back through our callback, which exchanges the code for a
        // session cookie, then lands the user in the chat workspace.
        redirectTo: `${window.location.origin}/auth/callback?next=/chat`,
        queryParams: { access_type: "offline", prompt: "consent" },
        // Don't navigate yet — we preflight the authorize URL first so a
        // misconfigured provider surfaces as an inline alert in the gate
        // instead of stranding the user on Supabase's raw JSON error page.
        skipBrowserRedirect: true,
      },
    });
    if (error) return { error: error.message };
    if (!data?.url) return { error: "Could not start Google sign-in. Please try again." };

    try {
      // A healthy provider answers 3xx to Google (an opaque redirect from
      // fetch's perspective); a config problem answers 4xx JSON we can read.
      const preflight = await fetch(data.url, { redirect: "manual" });
      if (preflight.type === "opaqueredirect" || preflight.ok) {
        window.location.assign(data.url);
        return {};
      }
      const body = (await preflight.json().catch(() => null)) as { msg?: string } | null;
      return { error: body?.msg ? `Google sign-in unavailable: ${body.msg}` : "Google sign-in isn't configured yet." };
    } catch {
      // Preflight itself failed (CORS/network quirk) — fall back to the normal
      // redirect rather than blocking a possibly-working sign-in.
      window.location.assign(data.url);
      return {};
    }
  }, [mode]);

  const markSignedIn = useCallback(() => {
    // Mock-mode only. Real sessions are owned by Supabase (cookies), not here.
    try {
      window.localStorage.setItem(AUTH_KEY, JSON.stringify({ mock: true, at: Date.now() }));
    } catch {
      /* storage unavailable — session just won't persist across reloads */
    }
    setSignedIn(true);
    notifyAuthChange();
  }, []);

  const recordGuestMessage = useCallback(() => {
    const next = readGuestCount() + 1;
    try {
      window.localStorage.setItem(GUEST_MSG_KEY, JSON.stringify({ date: todayKey(), count: next }));
    } catch {
      /* storage unavailable — the limit just won't persist across reloads */
    }
    setGuestUsed(next);
    notifyAuthChange();
  }, []);

  const continueAsGuest = useCallback(() => {
    // Guest access is legitimate: the chat already supports a localStorage-only
    // mode when Supabase is unconfigured (see supabaseConfigured()).
    try {
      window.localStorage.setItem(GUEST_KEY, "1");
    } catch {
      /* ignore */
    }
    setGuest(true);
    notifyAuthChange();
  }, []);

  const signOut = useCallback(() => {
    try {
      window.localStorage.removeItem(AUTH_KEY);
      window.localStorage.removeItem(GUEST_KEY);
    } catch {
      /* ignore */
    }
    setGuest(false);
    if (mode === "supabase") {
      getSupabaseBrowser().auth.signOut().catch(() => {});
    }
    setSignedIn(false);
    setUserEmail(null);
    setUserName(null);
    setUserAvatarUrl(null);
    notifyAuthChange();
  }, [mode]);

  return {
    ready,
    isSignedIn,
    isGuest,
    hasAccess: isSignedIn || isGuest,
    userEmail,
    userName,
    userAvatarUrl,
    mode,
    guestMessagesUsed: guestUsed,
    guestMessagesRemaining: Math.max(0, GUEST_DAILY_LIMIT - guestUsed),
    guestLimitReached: !isSignedIn && guestUsed >= GUEST_DAILY_LIMIT,
    recordGuestMessage,
    signInWithGoogle,
    markSignedIn,
    continueAsGuest,
    signOut,
  };
}
