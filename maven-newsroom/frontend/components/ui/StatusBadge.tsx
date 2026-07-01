import { statusMeta } from "@/lib/constants";

export function StatusBadge({ status, glow = false }: { status: string; glow?: boolean }) {
  const s = statusMeta(status);
  return (
    <span
      className={`chip ${s.ring} ${s.text} bg-white/[0.03] ${glow && (status === "running" || status === "progress") ? "animate-pulseGlow" : ""}`}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  );
}
