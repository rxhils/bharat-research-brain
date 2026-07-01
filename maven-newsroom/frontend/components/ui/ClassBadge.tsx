import { CLASS_ACCENT, CLASS_LABEL } from "@/lib/constants";
import type { ComponentClass } from "@/lib/types";

export function ClassBadge({ cls, intelligent, compact = false }: {
  cls: ComponentClass | ""; intelligent?: boolean | number; compact?: boolean;
}) {
  if (!cls) return null;
  const accent = CLASS_ACCENT[cls as ComponentClass];
  const smart = intelligent === true || intelligent === 1;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="chip font-mono"
        style={{ borderColor: `${accent}55`, color: accent, background: `${accent}14` }}
      >
        {cls === "Cprime" ? "C′" : cls}
        {!compact && <span className="text-ink-faint font-sans normal-case">· {CLASS_LABEL[cls as ComponentClass]}</span>}
      </span>
      {smart ? (
        <span className="chip border-teal/40 text-teal bg-teal/10" title="Genuine LLM reasoning">Intelligent</span>
      ) : (
        <span className="chip border-line text-ink-faint" title="Deterministic / service">Deterministic</span>
      )}
    </span>
  );
}
