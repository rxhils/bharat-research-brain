import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#05070A", soft: "#070A0F" },
        card: { DEFAULT: "#0B1117", raised: "#0E1621", hover: "#111A24" },
        line: { DEFAULT: "rgba(148,163,184,0.12)", strong: "rgba(148,163,184,0.22)" },
        ink: { DEFAULT: "#E6EDF3", muted: "#94A3B8", faint: "#5B6B7E" },
        teal: { DEFAULT: "#1FB6A6", bright: "#22D3EE" },
        ok: "#27C281",
        warn: "#F2994A",
        danger: "#EF4444",
        mcp: "#8B5CF6",
        info: "#3B82F6",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(31,182,166,0.35), 0 0 24px -4px rgba(31,182,166,0.35)",
        card: "0 1px 0 0 rgba(255,255,255,0.02) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        pulseGlow: {
          "0%,100%": { boxShadow: "0 0 0 1px rgba(31,182,166,0.4), 0 0 18px -6px rgba(31,182,166,0.5)" },
          "50%": { boxShadow: "0 0 0 1px rgba(31,182,166,0.7), 0 0 28px -2px rgba(31,182,166,0.8)" },
        },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        pulseGlow: "pulseGlow 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
      },
    },
  },
  plugins: [],
};
export default config;
