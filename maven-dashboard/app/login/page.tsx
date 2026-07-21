import type { Metadata } from "next";
import { LoginClient } from "@/components/auth/login-client";

export const metadata: Metadata = {
  title: "Sign in — Maven",
  description: "Sign in with Google to Maven — your private India market research workspace.",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return <LoginClient />;
}
