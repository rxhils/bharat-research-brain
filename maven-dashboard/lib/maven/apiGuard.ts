// API guard: verified identity + durable quota enforcement for the public Maven endpoints.
// The brain (lib/maven/answerQuestion.ts) stays identity-free; wrappers call ONE function.
//
// Identity: Supabase access token (Authorization: Bearer, mobile/API callers) or Supabase
// session cookies (web). body.userId is NEVER read. Tokens are verified server-side via
// supabase.auth.getUser() - no unverified JWT decode exists in this codebase.
//
// Durable limits: lib/maven/rateLimiter.ts (Upstash REST when configured; memory ONLY outside
// production). /api/mobile/ask REQUIRES a durable limiter in production and fails closed with
// SERVICE_UNAVAILABLE when it is missing - an unconfigured limiter never means unlimited traffic.
// Authenticated web users additionally meter durable daily usage via the usage_events table
// under the caller's own JWT (RLS; no service-role key exists in this app).
//
// Error contract (stable codes, mapped to envelopes by the routes):
//   INVALID_REQUEST | UNAUTHENTICATED | FORBIDDEN | RATE_LIMITED | SERVICE_UNAVAILABLE | INTERNAL_ERROR
//
// Env knobs (names only - see docs/MOBILE-API.md):
//   MOBILE_BURST_MAX (10) / MOBILE_BURST_WINDOW_SEC (60)   pre-auth IP burst
//   MOBILE_USER_DAILY_MAX (150)                            per verified user per day
//   MOBILE_DEEP_DAILY_MAX (10)                             deep-research class per user per day
//   MOBILE_CONCURRENT_MAX (3)                              global concurrent deep requests
//   WEB_ANON_BURST_MAX (30)                                web anonymous burst per minute
//   API_DAILY_CAP (150) + QUOTA_MODE (soft|strict)         web authenticated daily (usage_events)
//   RATE_LIMIT_ENABLED (web path master switch; default on-Vercel)
//   MAVEN_EVAL_TOKEN                                       rate-limit bypass header (never auth)
//   MAVEN_TEST_AUTH_SECRET                                 TEST-ONLY auth (hard-disabled on VERCEL)
//
// Nothing here logs tokens, headers, bodies or queries. See lib/maven/apiLog.ts.

import { supabaseConfigured, getSupabaseServer, getSupabaseForToken } from "@/lib/supabase/server";
import type { SupabaseClient } from "@supabase/supabase-js";
import { selectRateLimiter } from "@/lib/maven/rateLimiter";
import { apiLog, idHash } from "@/lib/maven/apiLog";
import { routeAnswerType } from "@/lib/maven/answerTypeRouter";
import { detectReportMode } from "@/lib/maven/reportModeDetector";

export type GuardErrorCode =
  | "INVALID_REQUEST" | "UNAUTHENTICATED" | "FORBIDDEN" | "RATE_LIMITED" | "SERVICE_UNAVAILABLE" | "INTERNAL_ERROR";

export type ApiIdentity =
  | { kind: "user"; id: string; client: SupabaseClient | null }
  | { kind: "anon"; id: string };

export type GuardOk = { ok: true; identity: ApiIdentity; release?: () => Promise<void> };
export type GuardFail = { ok: false; status: number; code: GuardErrorCode; message: string; retryAfterSeconds?: number };
export type GuardResult = GuardOk | GuardFail;

const DAY_MS = 24 * 60 * 60_000;

function intEnv(name: string, fallback: number): number {
  const n = parseInt(process.env[name] ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

export function guardEnabled(): boolean {
  const flag = process.env.RATE_LIMIT_ENABLED;
  if (flag === "1") return true;
  if (flag === "0") return false;
  return !!process.env.VERCEL;
}

function evalBypass(req: Request): boolean {
  const expected = process.env.MAVEN_EVAL_TOKEN;
  return !!expected && req.headers.get("x-maven-eval-token") === expected;
}

/**
 * Safe client IP. On Vercel the platform sets x-vercel-forwarded-for / x-real-ip; outside a
 * trusted proxy we do NOT trust arbitrary forwarded headers (callers collapse to one bucket,
 * which is fine for local dev/tests).
 */
export function clientIp(req: Request): string {
  if (process.env.VERCEL) {
    const v = req.headers.get("x-vercel-forwarded-for") || req.headers.get("x-real-ip") || req.headers.get("x-forwarded-for") || "";
    const first = v.split(",")[0].trim();
    if (first) return first;
  }
  // Local/test: honor x-forwarded-for so limiter tests can simulate distinct clients.
  const xff = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim();
  return xff || "local";
}

const failure = (status: number, code: GuardErrorCode, message: string, retryAfterSeconds?: number): GuardFail =>
  ({ ok: false, status, code, message, ...(retryAfterSeconds != null ? { retryAfterSeconds } : {}) });

// ---- identity ---------------------------------------------------------------------------------

type AuthOutcome = { identity: ApiIdentity; category: "ok_token" | "ok_cookie" | "missing" | "malformed" | "invalid_or_expired" | "unresolved" | "anon" };

/** TEST-ONLY identity: requires MAVEN_TEST_AUTH_SECRET, hard-disabled in production builds. */
function testAuth(req: Request): ApiIdentity | null {
  if (process.env.VERCEL) return null; // impossible in production
  const secret = process.env.MAVEN_TEST_AUTH_SECRET;
  if (!secret) return null;
  if (req.headers.get("x-maven-test-secret") !== secret) return null;
  const user = req.headers.get("x-maven-test-user");
  return user ? { kind: "user", id: user, client: null } : null;
}

export async function resolveIdentity(req: Request): Promise<AuthOutcome> {
  const test = testAuth(req);
  if (test) return { identity: test, category: "ok_token" };

  const auth = req.headers.get("authorization") ?? "";
  const hasBearer = auth.toLowerCase().startsWith("bearer ");
  const bearer = hasBearer ? auth.slice(7).trim() : "";

  if (hasBearer) {
    if (!bearer || bearer.split(".").length !== 3) {
      return { identity: { kind: "anon", id: clientIp(req) }, category: "malformed" };
    }
    if (!supabaseConfigured()) {
      return { identity: { kind: "anon", id: clientIp(req) }, category: "unresolved" };
    }
    try {
      const client = getSupabaseForToken(bearer);
      const { data, error } = await client.auth.getUser();
      if (!error && data?.user?.id) return { identity: { kind: "user", id: data.user.id, client }, category: "ok_token" };
      return { identity: { kind: "anon", id: clientIp(req) }, category: "invalid_or_expired" };
    } catch {
      return { identity: { kind: "anon", id: clientIp(req) }, category: "invalid_or_expired" };
    }
  }

  if (supabaseConfigured()) {
    try {
      const client = getSupabaseServer();
      const { data } = await client.auth.getUser();
      if (data?.user?.id) return { identity: { kind: "user", id: data.user.id, client }, category: "ok_cookie" };
    } catch { /* outside request scope / no session */ }
  }
  return { identity: { kind: "anon", id: clientIp(req) }, category: "anon" };
}

// ---- durable daily quota via usage_events (web authenticated; caller's own JWT) ----------------

async function usageEventsQuota(identity: Extract<ApiIdentity, { kind: "user" }>, route: string, cap: number): Promise<{ exceeded: boolean; infraError: boolean }> {
  if (!identity.client) return { exceeded: false, infraError: false }; // test identity: limiter covers it
  try {
    const since = new Date(Date.now() - DAY_MS).toISOString();
    const { count, error: countErr } = await identity.client
      .from("usage_events").select("id", { count: "exact", head: true })
      .eq("user_id", identity.id).eq("route", route).gte("created_at", since);
    if (countErr) return { exceeded: false, infraError: true };
    if ((count ?? 0) >= cap) return { exceeded: true, infraError: false };
    const { error: insErr } = await identity.client.from("usage_events").insert({ user_id: identity.id, route });
    return { exceeded: false, infraError: !!insErr };
  } catch {
    return { exceeded: false, infraError: true };
  }
}

// ---- deep-research classification (reuses the brain's own detectors; read-only) -----------------

export function isExpensiveQuery(query: string): boolean {
  try {
    const { answerType } = routeAnswerType(query);
    return detectReportMode(query, answerType).reportMode === true;
  } catch {
    return false;
  }
}

// ---- WEB guard (/api/ask, /api/feedback): anonymous allowed, best-effort limits ------------------

export async function checkApiGuard(req: Request, route: string, requestId = ""): Promise<GuardResult> {
  const { identity, category } = await resolveIdentity(req);
  if (requestId) apiLog({ evt: "auth", requestId, route, authCategory: category, authenticated: identity.kind === "user", who: idHash(identity.id) });

  if (!guardEnabled() || evalBypass(req)) return { ok: true, identity };

  const limiter = selectRateLimiter();
  if (limiter) {
    const burst = await limiter.check(
      identity.kind === "user"
        ? { bucket: "web_burst_user", id: identity.id, max: intEnv("API_BURST_PER_MIN", 30), windowSeconds: 60 }
        : { bucket: "web_burst_anon", id: identity.id, max: intEnv("WEB_ANON_BURST_MAX", 30), windowSeconds: 60 },
    );
    if (requestId) apiLog({ evt: "quota", requestId, route, bucket: identity.kind === "user" ? "web_burst_user" : "web_burst_anon", outcome: burst.allowed ? "allow" : "limit", who: idHash(identity.id) });
    if (!burst.allowed) return failure(429, "RATE_LIMITED", "Too many requests. Please try again shortly.", burst.retryAfterSeconds);
  }

  if (identity.kind === "user") {
    const daily = await usageEventsQuota(identity, route, intEnv("API_DAILY_CAP", 150));
    if (daily.exceeded) return failure(429, "RATE_LIMITED", "Daily request limit reached. Resets within 24 hours.");
    if (daily.infraError && process.env.QUOTA_MODE === "strict") {
      return failure(503, "SERVICE_UNAVAILABLE", "Temporarily unavailable.");
    }
  }
  return { ok: true, identity };
}

// ---- MOBILE guard (/api/mobile/ask): token required, durable limits required in production ------

export async function checkMobileGuard(req: Request, requestId: string, query: string): Promise<GuardResult> {
  const route = "/api/mobile/ask";
  const limiter = selectRateLimiter();

  // Production without a durable shared limiter -> fail CLOSED (never silently unlimited).
  if (!limiter) {
    apiLog({ evt: "quota", requestId, route, outcome: "no_durable_limiter" });
    return failure(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable. Please try again later.");
  }

  const bypass = evalBypass(req);

  // 1) Pre-auth IP burst - cheap protection before any token verification work.
  if (!bypass) {
    const ip = clientIp(req);
    const burst = await limiter.check({ bucket: "mobile_burst_ip", id: ip, max: intEnv("MOBILE_BURST_MAX", 10), windowSeconds: intEnv("MOBILE_BURST_WINDOW_SEC", 60) });
    apiLog({ evt: "quota", requestId, route, bucket: "mobile_burst_ip", outcome: burst.allowed ? "allow" : "limit", who: idHash(ip) });
    if (!burst.allowed) return failure(429, "RATE_LIMITED", "Too many requests. Please try again shortly.", burst.retryAfterSeconds);
    if (burst.infraError && process.env.VERCEL) {
      // Durable store configured but unreachable in production: fail closed for mobile.
      return failure(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable. Please try again later.");
    }
  }

  // 2) Verified identity - Bearer only. No client-supplied ids, no unverified decodes.
  const { identity, category } = await resolveIdentity(req);
  apiLog({ evt: "auth", requestId, route, authCategory: category, authenticated: identity.kind === "user", who: idHash(identity.id) });
  if (identity.kind !== "user") {
    if (category === "unresolved" && !supabaseConfigured()) {
      return failure(503, "SERVICE_UNAVAILABLE", "Sign-in is temporarily unavailable.");
    }
    return failure(401, "UNAUTHENTICATED", "Sign-in required.");
  }

  if (bypass) return { ok: true, identity };

  // 3) Per-user daily cap (durable, keyed by verified user id -> a new IP cannot reset it).
  const daily = await limiter.check({ bucket: "mobile_daily_user", id: identity.id, max: intEnv("MOBILE_USER_DAILY_MAX", 150), windowSeconds: 86_400 });
  apiLog({ evt: "quota", requestId, route, bucket: "mobile_daily_user", outcome: daily.allowed ? "allow" : "limit", who: idHash(identity.id) });
  if (!daily.allowed) return failure(429, "RATE_LIMITED", "Daily limit reached. Resets within 24 hours.", daily.retryAfterSeconds);

  // 4) Expensive/deep-research class: stricter daily quota + a global concurrency slot.
  if (isExpensiveQuery(query)) {
    const deep = await limiter.check({ bucket: "mobile_deep_user", id: identity.id, max: intEnv("MOBILE_DEEP_DAILY_MAX", 10), windowSeconds: 86_400 });
    apiLog({ evt: "quota", requestId, route, bucket: "mobile_deep_user", outcome: deep.allowed ? "allow" : "limit", who: idHash(identity.id) });
    if (!deep.allowed) return failure(429, "RATE_LIMITED", "Deep-research limit reached for today.", deep.retryAfterSeconds);

    const release = await limiter.acquireSlot("mobile_deep_concurrent", intEnv("MOBILE_CONCURRENT_MAX", 3), 120);
    if (!release) return failure(429, "RATE_LIMITED", "Busy with other research right now. Please retry in a moment.", 15);
    return { ok: true, identity, release };
  }

  return { ok: true, identity };
}
