// Refreshes the Supabase auth session on every request so SSR/server components
// and route handlers see a valid session (tokens rotate silently). No-op when
// Supabase isn't configured, so mock/local mode is completely unaffected.
import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return response; // mock mode — nothing to refresh

  // No Supabase auth cookie → no session to refresh. Skip the network call to
  // Supabase Auth that getUser() makes, so unauthenticated visitors and API
  // requests don't pay a per-request round-trip for nothing.
  if (!request.cookies.getAll().some((c) => c.name.startsWith("sb-"))) return response;

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // Touch the user to trigger a token refresh + cookie write when needed.
  await supabase.auth.getUser();
  return response;
}

export const config = {
  // Run on everything except static assets and media (keeps /intro.mp4, images,
  // and the Next static pipeline off the auth path).
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|mp4|webm|woff2?)$).*)",
  ],
};
