// Durable, shared rate limiting behind a small testable interface (roadmap Phase 2 hardening).
//
// Implementations:
//   UpstashRateLimiter  - durable + shared across serverless instances (Upstash Redis REST,
//                         plain fetch, no SDK). Fixed-window INCR with TTL. Also provides a
//                         best-effort distributed concurrency gate (INCR/DECR with a safety TTL).
//   MemoryRateLimiter   - tests/local development ONLY. selectRateLimiter() refuses to hand it
//                         out in production (VERCEL) - callers treat `null` as "durable limiter
//                         unavailable" and fail closed on routes that demand durability.
//
// Env (names only, see docs): UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN.
// Keys look like mvn:rl:<class>:<identity>:<windowIndex>; values are counters. No tokens,
// queries or bodies ever reach the store or logs.

export type RateLimitInput = {
  /** Bucket class, e.g. "mobile_burst_ip" | "mobile_daily_user" | "mobile_deep_user" | "web_burst_anon". */
  bucket: string;
  /** Identity within the bucket (client IP or verified user id). */
  id: string;
  /** Max requests per window. */
  max: number;
  /** Window length in seconds. */
  windowSeconds: number;
};

export type RateLimitDecision = {
  allowed: boolean;
  retryAfterSeconds: number;
  /** True when the decision came from a durable shared store (vs per-instance memory). */
  durable: boolean;
  /** True when the store errored; callers choose fail-open (web) or fail-closed (mobile strict). */
  infraError?: boolean;
};

export interface MavenRateLimiter {
  check(input: RateLimitInput): Promise<RateLimitDecision>;
  /** Best-effort concurrency gate. Returns a release fn when a slot was acquired, null when full. */
  acquireSlot(bucket: string, max: number, ttlSeconds: number): Promise<(() => Promise<void>) | null>;
  readonly durable: boolean;
}

// ---- Upstash (durable) --------------------------------------------------------------------

export function upstashConfigured(): boolean {
  return !!process.env.UPSTASH_REDIS_REST_URL && !!process.env.UPSTASH_REDIS_REST_TOKEN;
}

class UpstashRateLimiter implements MavenRateLimiter {
  readonly durable = true;

  private async pipeline(cmds: (string | number)[][]): Promise<any[] | null> {
    try {
      const r = await fetch(`${process.env.UPSTASH_REDIS_REST_URL}/pipeline`, {
        method: "POST",
        headers: { Authorization: `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify(cmds),
        cache: "no-store",
      });
      if (!r.ok) return null;
      const j = (await r.json()) as { result?: unknown; error?: string }[];
      if (!Array.isArray(j) || j.some((x) => x && typeof x === "object" && "error" in x && x.error)) return null;
      return j.map((x) => (x as any).result);
    } catch {
      return null;
    }
  }

  async check(input: RateLimitInput): Promise<RateLimitDecision> {
    const windowIndex = Math.floor(Date.now() / (input.windowSeconds * 1000));
    const key = `mvn:rl:${input.bucket}:${input.id}:${windowIndex}`;
    // INCR + set the TTL only when the key is fresh (NX). Fixed window - simple and shared.
    const res = await this.pipeline([["INCR", key], ["EXPIRE", key, input.windowSeconds + 5, "NX"]]);
    if (!res) return { allowed: true, retryAfterSeconds: 0, durable: true, infraError: true };
    const count = Number(res[0] ?? 0);
    if (count <= input.max) return { allowed: true, retryAfterSeconds: 0, durable: true };
    const secondsIntoWindow = Math.floor((Date.now() / 1000) % input.windowSeconds);
    return { allowed: false, retryAfterSeconds: Math.max(1, input.windowSeconds - secondsIntoWindow), durable: true };
  }

  async acquireSlot(bucket: string, max: number, ttlSeconds: number): Promise<(() => Promise<void>) | null> {
    const key = `mvn:slots:${bucket}`;
    const res = await this.pipeline([["INCR", key], ["EXPIRE", key, ttlSeconds, "NX"]]);
    if (!res) return async () => {}; // store hiccup: don't dead-lock requests on the gate
    const count = Number(res[0] ?? 0);
    if (count > max) {
      void this.pipeline([["DECR", key]]);
      return null;
    }
    return async () => { void this.pipeline([["DECR", key]]); };
  }
}

// ---- Memory (tests / local dev ONLY - never selected in production) ---------------------------

const memHits = new Map<string, { count: number; windowStart: number }>();
let memSlots = new Map<string, number>();

export class MemoryRateLimiter implements MavenRateLimiter {
  readonly durable = false;

  async check(input: RateLimitInput): Promise<RateLimitDecision> {
    const now = Date.now();
    const windowMs = input.windowSeconds * 1000;
    const key = `${input.bucket}:${input.id}`;
    const rec = memHits.get(key);
    if (!rec || now - rec.windowStart > windowMs) {
      memHits.set(key, { count: 1, windowStart: now });
      return { allowed: true, retryAfterSeconds: 0, durable: false };
    }
    rec.count += 1;
    if (rec.count <= input.max) return { allowed: true, retryAfterSeconds: 0, durable: false };
    return { allowed: false, retryAfterSeconds: Math.ceil((rec.windowStart + windowMs - now) / 1000), durable: false };
  }

  async acquireSlot(bucket: string, max: number): Promise<(() => Promise<void>) | null> {
    const cur = memSlots.get(bucket) ?? 0;
    if (cur >= max) return null;
    memSlots.set(bucket, cur + 1);
    return async () => { memSlots.set(bucket, Math.max(0, (memSlots.get(bucket) ?? 1) - 1)); };
  }
}

// ---- selection --------------------------------------------------------------------------------

let upstashSingleton: UpstashRateLimiter | null = null;
let memorySingleton: MemoryRateLimiter | null = null;

/**
 * Pick the limiter for this environment.
 *  - Upstash configured -> durable limiter (always preferred).
 *  - No Upstash + NOT production -> memory limiter (tests/local dev).
 *  - No Upstash + production (VERCEL) -> null. Routes that REQUIRE durability (mobile)
 *    must fail closed with SERVICE_UNAVAILABLE; best-effort routes (web) may degrade.
 */
export function selectRateLimiter(): MavenRateLimiter | null {
  if (upstashConfigured()) return (upstashSingleton ??= new UpstashRateLimiter());
  if (!process.env.VERCEL) return (memorySingleton ??= new MemoryRateLimiter());
  return null;
}
