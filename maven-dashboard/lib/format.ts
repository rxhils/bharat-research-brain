// Indian number formatting: ₹, lakh/crore, signed percentages.

export function inr(n: number, opts: { paise?: boolean } = {}): string {
  const v = Math.round(n * (opts.paise ? 100 : 1)) / (opts.paise ? 100 : 1);
  return "₹" + v.toLocaleString("en-IN", {
    maximumFractionDigits: opts.paise ? 2 : 0,
  });
}

// Compact: ₹12.41L / ₹3.21Cr — for headline figures.
export function inrCompact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1_00_00_000) return "₹" + (n / 1_00_00_000).toFixed(2) + "Cr";
  if (a >= 1_00_000) return "₹" + (n / 1_00_000).toFixed(2) + "L";
  if (a >= 1_000) return "₹" + (n / 1_000).toFixed(1) + "K";
  return "₹" + n.toFixed(0);
}

export function pct(n: number, digits = 2): string {
  return (n >= 0 ? "+" : "") + n.toFixed(digits) + "%";
}

export function plain(n: number, digits = 2): string {
  return n.toFixed(digits);
}

// emerald for positive, muted rose for negative (the only two value colors).
export function signClass(n: number): string {
  return n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted";
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

export function ago(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}
