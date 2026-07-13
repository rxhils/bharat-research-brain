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
        // muted gold — premium accent used only on the explainer "story" page
        gold: "#c9a961",
        "gold-soft": "#e3cb8f",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        // editorial serif — explainer headlines only (loaded on /how-it-works)
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      letterSpacing: { label: "0.28em" },
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
        spinSlow: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        spinReverse: {
          "0%": { transform: "rotate(360deg)" },
          "100%": { transform: "rotate(0deg)" },
        },
        floatY: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        // --- Maven Google gate (components/auth) ambient motion ---
        gateGlow: {
          "0%,100%": { opacity: "0.7", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        gateGlow2: {
          "0%,100%": { opacity: "0.5" },
          "50%": { opacity: "0.9" },
        },
        gateSweep: {
          "0%": { transform: "translateX(-130%)" },
          "100%": { transform: "translateX(260%)" },
        },
        gateDraw: { to: { strokeDashoffset: "0" } },
        gateSpark: {
          "0%,100%": { opacity: "0.5", transform: "scale(0.82)" },
          "50%": { opacity: "1", transform: "scale(1.15)" },
        },
        gateBlink: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.15" },
        },
        gateSpin: { to: { transform: "rotate(360deg)" } },
        gateShimmer: {
          "0%": { backgroundPosition: "-180% 0" },
          "100%": { backgroundPosition: "180% 0" },
        },
        // Chat hero core: a market line draws across the disc, holds, fades, loops.
        coreTrace: {
          "0%": { strokeDashoffset: "150", opacity: "0" },
          "10%": { opacity: "1" },
          "55%": { strokeDashoffset: "0", opacity: "1" },
          "75%": { strokeDashoffset: "0", opacity: "1" },
          "90%": { strokeDashoffset: "0", opacity: "0" },
          "100%": { strokeDashoffset: "150", opacity: "0" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
        spinSlow: "spinSlow 34s linear infinite",
        spinReverse: "spinReverse 48s linear infinite",
        floatY: "floatY 7s ease-in-out infinite",
        // ticker: content is duplicated once so -50% loops seamlessly
        marquee: "marquee 38s linear infinite",
        // Maven Google gate — respected by the global reduced-motion damp in
        // globals.css (all animations collapse to a single 0.001ms tick).
        "gate-glow": "gateGlow 9s ease-in-out infinite",
        "gate-glow2": "gateGlow2 11s ease-in-out infinite",
        "gate-sweep": "gateSweep 2.6s ease-in-out infinite",
        "gate-draw": "gateDraw 2.4s ease-out .5s forwards",
        "gate-spark": "gateSpark 1.8s ease-in-out infinite",
        "gate-blink": "gateBlink 1.1s step-end infinite",
        "gate-spin": "gateSpin .75s linear infinite",
        "gate-shimmer": "gateShimmer 4.5s linear infinite",
        "core-trace": "coreTrace 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
