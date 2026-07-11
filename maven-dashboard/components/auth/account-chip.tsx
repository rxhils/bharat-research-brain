"use client";

// Signed-in account chip for the chat header: gradient avatar with the
// account's initial and a live pulse, the connected email, and a Log out
// action. Logging out clears the session — ChatAuthGate reopens automatically.
// brand-motion: its micro-animations run even under the OS reduced-motion flag.

import { motion } from "framer-motion";
import { EASE, PRESS, useReducedMotionSafe } from "../motion";
import { useMavenAuth } from "./useMavenAuth";

export function AccountChip() {
  const auth = useMavenAuth();
  const reduce = useReducedMotionSafe();
  if (!auth.ready || !auth.hasAccess) return null;

  const label = auth.userEmail ?? (auth.isGuest ? "Guest session" : "Signed in");
  const initial = (auth.userEmail?.[0] ?? "G").toUpperCase();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: -6, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, ease: EASE }}
      className="brand-motion group flex shrink-0 items-center gap-2 rounded-full border border-hairline bg-panel/40 p-1.5 backdrop-blur-sm transition-[border-color,box-shadow] duration-300 hover:border-emerald/25 hover:shadow-[0_0_24px_-8px_rgba(52,211,153,0.35)]"
    >
      {/* gradient avatar: account initial + live pulse */}
      <span
        className="relative grid h-6 w-6 shrink-0 place-items-center rounded-full font-sans text-[10px] font-bold"
        style={{ background: "linear-gradient(140deg,#34d399,#10b981)", color: "#06251b", boxShadow: "0 0 14px -4px rgba(52,211,153,0.55)" }}
        aria-hidden
      >
        {initial}
        <span className="absolute -right-px -top-px flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-emerald opacity-70 animate-ping" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald ring-2 ring-bg" />
        </span>
      </span>

      <span className="max-w-[180px] truncate font-sans text-xs text-muted transition-colors duration-300 group-hover:text-ink" title={label}>
        {label}
      </span>

      <button
        type="button"
        onClick={auth.signOut}
        aria-label="Log out of Maven"
        className={
          "flex items-center gap-1 rounded-full border border-hairline px-2.5 py-1 font-sans text-[11px] font-medium text-dim " +
          "transition-colors duration-150 hover:border-emerald/40 hover:bg-emerald/[0.06] hover:text-emerald " +
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald/60 hover:[&>svg]:translate-x-0.5 " +
          PRESS
        }
      >
        Log out
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-200" aria-hidden>
          <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
          <path d="M14 16l4-4-4-4M18 12H8" />
        </svg>
      </button>
    </motion.div>
  );
}
