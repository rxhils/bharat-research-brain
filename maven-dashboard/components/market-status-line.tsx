"use client";

// One calm market-status line for /chat — replaces the scrolling ticker there.
// Two headline indices and a freshness stamp; nothing moves on its own.
import { useEffect, useState } from "react";
import type { Quote } from "@/lib/maven/types";

export function MarketStatusLine() {
  const [indices, setIndices] = useState<Quote[] | null>(null);
  const [fetchedAt, setFetchedAt] = useState<number>(0);
  // re-render each minute so "Updated Xm ago" stays honest without refetching
  const [, tick] = useState(0);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch("/api/market/ticker", { cache: "no-store" });
        if (!r.ok) return;
        const j: { indices?: Quote[] } = await r.json();
        if (!alive) return;
        const idx = (j.indices ?? []).filter((q) => q.changePct != null).slice(0, 2);
        if (idx.length) {
          setIndices(idx);
          setFetchedAt(Date.now());
        }
      } catch {
        /* decorative — stay empty rather than show an error */
      }
    })();
    const t = setInterval(() => tick((x) => x + 1), 60_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (!indices) return null;
  const min = Math.max(0, Math.floor((Date.now() - fetchedAt) / 60_000));
  return (
    <div className="min-w-0 truncate text-xs text-dim">
      India markets
      {indices.map((q) => (
        <span key={q.label}>
          {" · "}
          <span className="text-muted">{q.label}</span>{" "}
          <span className={"tnum " + ((q.changePct ?? 0) >= 0 ? "text-emerald" : "text-rose")}>
            {(q.changePct ?? 0) >= 0 ? "+" : ""}
            {(q.changePct ?? 0).toFixed(2)}%
          </span>
        </span>
      ))}
      {" · "}Updated {min < 1 ? "just now" : `${min}m ago`}
    </div>
  );
}
