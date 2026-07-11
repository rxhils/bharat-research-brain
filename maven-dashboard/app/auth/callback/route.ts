// OAuth callback: Google redirects here with a `code`. We exchange it for a
// Supabase session cookie, then send the user on to `next` (the chat workspace).
// Only reached in supabase mode; mock mode never links out to Google.
import { NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // Only allow same-origin relative paths as the post-login destination.
  const nextParam = searchParams.get("next") || "/chat";
  const next = nextParam.startsWith("/") ? nextParam : "/chat";

  if (code) {
    const supabase = getSupabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // No code, or the exchange failed — bounce back to the landing with a flag the
  // UI can surface. Never leak the raw error to the URL.
  return NextResponse.redirect(`${origin}/?auth_error=1`);
}
