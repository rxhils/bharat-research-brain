import type { Metadata } from "next";
import { LoginClient } from "@/components/auth/login-client";

export const metadata: Metadata = { title: "Sign in — Maven", robots: { index: false, follow: false } };

export default function LoginPage() {
  return <LoginClient />;
}
