import clsx from "clsx";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={clsx("glass card-pad", className)}>{children}</div>;
}

export function StatCard({ label, value, hint, accent }: {
  label: string; value: React.ReactNode; hint?: string; accent?: string;
}) {
  return (
    <div className="glass card-pad relative overflow-hidden">
      {accent && <div className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }} />}
      <div className="eyebrow">{label}</div>
      <div className="metric mt-2" style={accent ? { color: accent } : undefined}>{value}</div>
      {hint && <div className="text-xs text-ink-faint mt-1.5">{hint}</div>}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="glass card-pad grid place-items-center text-center py-12">
      <div>
        <div className="text-ink-muted font-medium">{title}</div>
        {hint && <div className="text-xs text-ink-faint mt-1.5 max-w-sm">{hint}</div>}
      </div>
    </div>
  );
}
