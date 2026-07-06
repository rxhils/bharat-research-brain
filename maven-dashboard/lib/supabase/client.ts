// Browser-side Supabase client. Uses the publishable key only — Postgres RLS is the
// authorization boundary, so this key is safe to ship to the client by design.
import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

/** True when the Supabase env vars are present. When false the chat falls back to
 *  the legacy localStorage-only mode so an unconfigured deploy never hard-crashes. */
export function supabaseConfigured(): boolean {
  return !!process.env.NEXT_PUBLIC_SUPABASE_URL && !!process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
}

export function getSupabaseBrowser(): SupabaseClient {
  if (!_client) {
    _client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    );
  }
  return _client;
}
