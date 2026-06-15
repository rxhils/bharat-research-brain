import type { Config } from "tailwindcss";

// Maven theme — quiet-luxury trading terminal. Near-black canvas, layered panels,
// ONE accent (emerald). Rose only for losses (functional). Geist via CSS vars.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0b0d",
        panel: "#111316",
        panel2: "#16191d",
        border: "rgba(255,255,255,0.07)",
        hairline: "rgba(255,255,255,0.045)",
        ink: "#e9ebed",
        muted: "#8b9298",
        dim: "#5a616a",
        emerald: "#34d399",
        "emerald-deep": "#10b981",
        rose: "#fb7185",
        amber: "#fbbf24",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: { xl2: "16px" },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
