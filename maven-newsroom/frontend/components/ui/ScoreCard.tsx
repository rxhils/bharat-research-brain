import { Check, X } from "lucide-react";

export function ScoreCard({ label, score, threshold, sub }: {
  label: string; score: number | null | undefined; threshold?: number; sub?: string;
}) {
  const has = score != null;
  const pass = has && threshold != null ? score >= threshold : undefined;
  const color = !has ? "#5B6B7E" : pass === false ? "#EF4444" : score >= 90 ? "#27C281" : "#F2994A";
  return (
    <div className="glass card-pad">
      <div className="flex items-center justify-between">
        <span className="eyebrow">{label}</span>
        {pass != null && (
          <span className={`chip ${pass ? "border-ok/40 text-ok bg-ok/10" : "border-danger/40 text-danger bg-danger/10"}`}>
            {pass ? <Check size={12} /> : <X size={12} />} {pass ? "Pass" : "Fail"}
          </span>
        )}
      </div>
      <div className="mt-2 flex items-end gap-1">
        <span className="text-4xl font-semibold tracking-tight" style={{ color }}>
          {has ? score : "—"}
        </span>
        {has && <span className="text-ink-faint mb-1.5 text-sm">/100</span>}
      </div>
      {threshold != null && (
        <div className="mt-3 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${has ? score : 0}%`, background: color }} />
        </div>
      )}
      <div className="mt-2 text-xs text-ink-faint">
        {sub ?? (threshold != null ? `Gate ≥ ${threshold}` : "")}
      </div>
    </div>
  );
}
