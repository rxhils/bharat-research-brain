"use client";
import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function JsonViewer({ data, maxHeight = "100%" }: { data: unknown; maxHeight?: string }) {
  const [copied, setCopied] = useState(false);
  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  async function copy() {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1200); } catch {}
  }
  return (
    <div className="relative rounded-lg border border-line bg-bg-soft/80 overflow-hidden">
      <button onClick={copy}
        className="absolute right-2 top-2 z-10 chip border-line text-ink-muted hover:text-ink bg-card">
        {copied ? <Check size={12} className="text-ok" /> : <Copy size={12} />} {copied ? "Copied" : "Copy"}
      </button>
      <pre className="mono text-[12px] leading-relaxed text-ink-muted p-3.5 overflow-auto" style={{ maxHeight }}>
        {text}
      </pre>
    </div>
  );
}
