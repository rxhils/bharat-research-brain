"use client";

// Shared film tile for the auth gate: plays /intro.mp4 inside a clean branded
// frame. Handles the real-world messiness of <video> so the panels don't:
//   • seeks past the intro's fade-from-black so the first visible frame has
//     content (also gives reduced-motion users a real still instead of black)
//   • imperative muted + play() kick (React SSR drops the muted attribute,
//     which otherwise makes browsers veto autoplay)
//   • a branded cover that fades only once real frames are rendering, and
//     stays if playback never starts — the tile never reads as a black void
//   • skips fetch/decode entirely for the display:none copy at a breakpoint

import { useEffect, useRef, useState } from "react";

export function GateFilm({ className }: { className?: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [showingFrames, setShowingFrames] = useState(false);

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    if (v.offsetParent === null) return; // hidden at this breakpoint — skip
    v.muted = true;

    const reveal = () => setShowingFrames(true);
    v.addEventListener("playing", reveal);
    v.addEventListener("seeked", reveal);

    const kick = () => {
      try {
        if (v.currentTime < 1.2) v.currentTime = 1.2; // skip the black fade-in
      } catch {
        /* not seekable yet — the playing event still reveals */
      }
      // Deliberately NOT gated on prefers-reduced-motion: the OS flag froze the
      // film for the operator, who explicitly wants it playing (brand-motion
      // surface). The film is muted, small, and contained.
      v.play().catch(() => {
        /* autoplay denied — the branded cover stays, which is fine */
      });
    };
    if (v.readyState >= 1) kick();
    else v.addEventListener("loadedmetadata", kick, { once: true });

    return () => {
      v.removeEventListener("playing", reveal);
      v.removeEventListener("seeked", reveal);
      v.removeEventListener("loadedmetadata", kick);
    };
  }, []);

  return (
    <div className={`brand-motion relative overflow-hidden ${className ?? ""}`}>
      <video
        ref={ref}
        src="/intro.mp4"
        muted
        loop
        playsInline
        autoPlay
        preload="metadata"
        className="block aspect-video w-full object-cover"
      />
      {/* bottom vignette seats the film into the card */}
      <div className="pointer-events-none absolute inset-0" style={{ background: "linear-gradient(180deg, transparent 60%, rgba(9,11,13,0.55) 100%)" }} />
      {/* branded cover — visible until real frames render */}
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-0 grid place-items-center transition-opacity duration-700 ${showingFrames ? "opacity-0" : "opacity-100"}`}
        style={{ background: "linear-gradient(160deg, #101315 0%, #0b0e10 55%, #0d1412 100%)" }}
      >
        <div className="flex flex-col items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/[0.08]" style={{ background: "linear-gradient(160deg,#171b1f,#0e1114)", boxShadow: "0 0 24px -6px rgba(52,211,153,0.35)" }}>
            <svg width="22" height="22" viewBox="0 0 100 100" fill="none">
              <path d="M15 77 L30 29 L44 59 L55 34" stroke="#f4f4f1" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M59 37 L71 67 L89 19" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="89" cy="17" r="8" fill="#34d399" />
            </svg>
          </span>
          <span className="font-sans text-[10px] font-semibold uppercase leading-none tracking-[0.18em] text-dim">Maven · in motion</span>
          {/* static hairline — the looping gate-sweep shimmer was retired (the
              cover only shows until real frames render, so it needs no motion) */}
          <span className="h-0.5 w-10 rounded-sm bg-emerald/25" />
        </div>
      </div>
    </div>
  );
}
