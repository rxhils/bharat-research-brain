// Shared Maven Reel theme tokens. The daily reel's accent comes from the Motion
// Variation Engine (props.theme.accent); everything else is constant so the brand
// stays consistent across templates.
export const COLORS = {
  bg: "#05070A",
  teal: "#22D3EE",
  green: "#27C281",
  red: "#EF4444",
  ink: "#E6EDF3",
  faint: "#5B6B7E",
  white: "#FFFFFF",
};

export const SANS = "Segoe UI, Arial, system-ui, sans-serif";

// default accent if a reel doesn't specify a variation
export const DEFAULT_ACCENT = COLORS.teal;
