// Structured, privacy-safe API logging (Vercel-friendly single-line JSON on stdout).
//
// HARD RULES: never log bearer tokens, API keys, request bodies, queries, conversation
// history, or raw provider responses. Identities are logged only as short hashes so an
// operator can correlate abuse without storing user ids / IPs in plaintext logs.

import { createHash, randomUUID } from "node:crypto";

export function newRequestId(): string {
  return randomUUID();
}

/** Short one-way hash for identity correlation in logs (never the raw ip/user id). */
export function idHash(value: string): string {
  return createHash("sha256").update(value).digest("hex").slice(0, 12);
}

type ApiEvent = {
  evt: "request_start" | "auth" | "quota" | "complete" | "error";
  requestId: string;
  route: string;
  /** auth: outcome category only (never token material). */
  authCategory?: "ok_token" | "ok_cookie" | "missing" | "malformed" | "invalid_or_expired" | "unresolved" | "anon";
  authenticated?: boolean;
  /** quota: bucket + outcome. */
  bucket?: string;
  outcome?: "allow" | "limit" | "infra_error" | "no_durable_limiter";
  /** complete: coarse answer type + latency. */
  answerType?: string;
  latencyMs?: number;
  /** error: safe category only. */
  errorCategory?: "invalid_request" | "unauthenticated" | "rate_limited" | "service_unavailable" | "internal";
  /** hashed identity for correlation (idHash output). */
  who?: string;
};

export function apiLog(e: ApiEvent): void {
  try {
    console.log(JSON.stringify({ src: "maven-api", t: new Date().toISOString(), ...e }));
  } catch {
    /* logging must never break a request */
  }
}
