// Indian number formatting: rupee, lakh/crore, signed percentages.
export function inr(n: number): string {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}
export function inrCr(n: number): string {
  const sign = n < 0 ? "-" : "+";
  return sign + "₹" + Math.abs(n).toLocaleString("en-IN") + " Cr";
}
export function num(n: number, digits = 2): string {
  return n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export function pct(n: number, digits = 2): string {
  return (n >= 0 ? "+" : "") + n.toFixed(digits) + "%";
}
export function signClass(n: number): string {
  return n > 0 ? "text-emerald" : n < 0 ? "text-rose" : "text-muted";
}