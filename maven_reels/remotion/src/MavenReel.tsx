import React from "react";
import {
  AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig,
  interpolate, spring, Easing,
} from "remotion";

// ---------------------------------------------------------------- types
export type Scene = {
  start: number; duration: number;
  kind: "hook" | "stat" | "chips" | "reason" | "chart" | "outro";
  bg?: string; title?: string; label?: string; value?: number; suffix?: string;
  sub?: string; chips?: string[]; text?: string; points?: number[]; accent?: string;
};
export type Caption = { start: number; end: number; text: string; emphasis?: string };
export type ReelProps = {
  fps: number; durationSeconds: number;
  brand: { name: string; site: string };
  theme?: { accent?: string };
  template?: string; variation?: string;
  scenes: Scene[]; subtitles: Caption[];
};

const TEAL = "#22D3EE", GREEN = "#27C281", RED = "#EF4444", INK = "#E6EDF3", FAINT = "#5B6B7E";
const SANS = "Segoe UI, Arial, system-ui, sans-serif";

// ---------------------------------------------------------------- helpers
const useEnter = (delay = 0, dur = 12) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, durationInFrames: dur, config: { damping: 14, mass: 0.6 } });
};

// ---------------------------------------------------------------- background
const Background: React.FC<{ scene?: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [0, 300], [0, -40]);
  return (
    <AbsoluteFill style={{ backgroundColor: "#05070A" }}>
      {scene?.bg && (
        <AbsoluteFill style={{ opacity: 0.55 }}>
          <Img src={staticFile(`run/${scene.bg}`)}
            style={{ width: "100%", height: "100%", objectFit: "cover",
              transform: `scale(${interpolate(frame, [0, 120], [1.06, 1.12])})` }} />
        </AbsoluteFill>
      )}
      {/* moving grid */}
      <AbsoluteFill style={{
        backgroundImage:
          "linear-gradient(rgba(148,163,184,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.06) 1px, transparent 1px)",
        backgroundSize: "80px 80px", transform: `translateY(${drift}px)`, opacity: 0.7 }} />
      {/* radial glow */}
      <AbsoluteFill style={{ background:
        "radial-gradient(900px 700px at 70% 18%, rgba(31,182,166,0.14), transparent 60%)" }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(5,7,10,0.2) 0%, rgba(5,7,10,0.75) 100%)" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- scene bodies
const Hook: React.FC<{ s: Scene }> = ({ s }) => {
  const e = useEnter(0, 14);
  const accent = s.accent || TEAL;
  const under = interpolate(e, [0.4, 1], [0, 1], { extrapolateLeft: "clamp" });
  return (
    <Center>
      <div style={{ transform: `scale(${interpolate(e, [0, 1], [0.7, 1])}) translateY(${interpolate(e, [0, 1], [40, 0])}px)`, opacity: e, textAlign: "center", padding: "0 90px" }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 96, lineHeight: 1.02, color: INK, letterSpacing: -1 }}>
          {s.title}
        </div>
        <div style={{ height: 8, width: 220, background: accent, borderRadius: 4, margin: "34px auto 0", transform: `scaleX(${under})`, boxShadow: `0 0 24px ${accent}` }} />
      </div>
    </Center>
  );
};

const Counter: React.FC<{ value: number; suffix?: string; color: string }> = ({ value, suffix, color }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [4, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const v = value * t;
  const shown = Math.abs(value) < 10 ? v.toFixed(1) : Math.round(v).toString();
  return <span style={{ color }}>{value < 0 ? "" : "+"}{shown}{suffix ?? ""}</span>;
};

const Stat: React.FC<{ s: Scene }> = ({ s }) => {
  const e = useEnter(0, 16);
  const neg = (s.value ?? 0) < 0;
  const color = neg ? RED : GREEN;
  return (
    <Center>
      <div style={{ transform: `translateY(${interpolate(e, [0, 1], [60, 0])}px)`, opacity: e,
        background: "rgba(14,22,33,0.92)", border: "1px solid rgba(148,163,184,0.18)", borderRadius: 28,
        padding: "54px 64px", minWidth: 640, textAlign: "center", boxShadow: "0 24px 60px -20px rgba(0,0,0,0.7)" }}>
        <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, letterSpacing: 4, color: FAINT, textTransform: "uppercase" }}>{s.label}</div>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 150, lineHeight: 1, marginTop: 14 }}>
          <Counter value={s.value ?? 0} suffix={s.suffix} color={color} />
        </div>
        {s.sub && <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 34, color: INK, marginTop: 16 }}>{s.sub}</div>}
      </div>
    </Center>
  );
};

const Chips: React.FC<{ s: Scene; accent: string }> = ({ s, accent }) => (
  <Center>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 22, justifyContent: "center", padding: "0 80px", maxWidth: 900 }}>
      {(s.chips ?? []).map((c, i) => {
        const e = useEnter(i * 5, 12);
        return (
          <div key={c} style={{ transform: `scale(${interpolate(e, [0, 1], [0.5, 1])})`, opacity: e,
            background: `${accent}1F`, border: `1px solid ${accent}73`, color: accent,
            fontFamily: SANS, fontWeight: 700, fontSize: 46, padding: "20px 40px", borderRadius: 999 }}>{c}</div>
        );
      })}
    </div>
  </Center>
);

const Reason: React.FC<{ s: Scene }> = ({ s }) => {
  const words = (s.text ?? "").split(" ");
  return (
    <Center>
      <div style={{ padding: "0 90px", textAlign: "center", fontFamily: SANS, fontWeight: 800, fontSize: 78, lineHeight: 1.12, color: INK }}>
        {words.map((w, i) => {
          const e = useEnter(i * 3, 10);
          return <span key={i} style={{ display: "inline-block", marginRight: 18, opacity: e, transform: `translateY(${interpolate(e, [0, 1], [24, 0])}px)` }}>{w}</span>;
        })}
      </div>
    </Center>
  );
};

const Chart: React.FC<{ s: Scene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const pts = s.points && s.points.length > 1 ? s.points : [8, 7, 7.4, 6, 5.2, 3, 2.4, 2];
  const W = 820, H = 420, pad = 20;
  const min = Math.min(...pts), max = Math.max(...pts);
  const coords = pts.map((p, i) => {
    const x = pad + (i / (pts.length - 1)) * (W - pad * 2);
    const y = pad + (1 - (p - min) / (max - min || 1)) * (H - pad * 2);
    return [x, y] as const;
  });
  const d = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c[0].toFixed(1)},${c[1].toFixed(1)}`).join(" ");
  const draw = interpolate(frame, [4, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const len = 2000;
  const dot = coords[Math.min(coords.length - 1, Math.floor(draw * (coords.length - 1)))];
  const e = useEnter(0, 12);
  return (
    <Center>
      <svg width={W} height={H} style={{ opacity: e }}>
        <defs>
          <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={RED} stopOpacity={0.28} />
            <stop offset="100%" stopColor={RED} stopOpacity={0} />
          </linearGradient>
        </defs>
        <path d={`${d} L${coords[coords.length - 1][0]},${H - pad} L${coords[0][0]},${H - pad} Z`} fill="url(#g)" opacity={draw} />
        <path d={d} fill="none" stroke={RED} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={len} strokeDashoffset={len * (1 - draw)} style={{ filter: `drop-shadow(0 0 12px ${RED})` }} />
        <circle cx={dot[0]} cy={dot[1]} r={12} fill={RED} style={{ filter: `drop-shadow(0 0 14px ${RED})` }} />
      </svg>
    </Center>
  );
};

const Outro: React.FC<{ s: Scene; brand: ReelProps["brand"] }> = ({ s, brand }) => {
  const e = useEnter(0, 16);
  return (
    <Center>
      <div style={{ textAlign: "center", transform: `scale(${interpolate(e, [0, 1], [0.8, 1])})`, opacity: e }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 120, color: INK, letterSpacing: 2 }}>{brand.name}</div>
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 40, color: TEAL, marginTop: 10 }}>{brand.site}</div>
        {s.text && <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 40, color: FAINT, marginTop: 34, padding: "0 90px" }}>{s.text}</div>}
      </div>
    </Center>
  );
};

const Center: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>{children}</AbsoluteFill>
);

const SceneBody: React.FC<{ s: Scene; brand: ReelProps["brand"]; accent: string }> = ({ s, brand, accent }) => {
  if (s.kind === "hook") return <Hook s={s} />;
  if (s.kind === "stat") return <Stat s={s} />;
  if (s.kind === "chips") return <Chips s={s} accent={accent} />;
  if (s.kind === "reason") return <Reason s={s} />;
  if (s.kind === "chart") return <Chart s={s} />;
  return <Outro s={s} brand={brand} />;
};

// ---------------------------------------------------------------- subtitles
const Subtitles: React.FC<{ subs: Caption[]; fps: number; accent: string }> = ({ subs, fps, accent }) => {
  const frame = useCurrentFrame();
  const t = frame / fps;
  const cur = subs.find((c) => t >= c.start && t < c.end);
  if (!cur) return null;
  const local = (t - cur.start) * fps;
  const pop = spring({ frame: local, fps, durationInFrames: 8, config: { damping: 12 } });
  const words = cur.text.split(" ");
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 320 }}>
      <div style={{ transform: `translateY(${interpolate(pop, [0, 1], [24, 0])}px) scale(${interpolate(pop, [0, 1], [0.9, 1])})`,
        opacity: pop, maxWidth: 900, textAlign: "center", background: "rgba(5,7,10,0.55)", padding: "14px 26px",
        borderRadius: 16, backdropFilter: "blur(2px)" }}>
        {words.map((w, i) => {
          const key = cur.emphasis && w.toLowerCase().replace(/[^a-z0-9%.-]/g, "").includes(cur.emphasis.toLowerCase());
          return <span key={i} style={{ fontFamily: SANS, fontWeight: 800, fontSize: 58, lineHeight: 1.15,
            color: key ? accent : "#FFFFFF", marginRight: 14, textShadow: "0 2px 8px rgba(0,0,0,0.8)" }}>{w}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- chrome (brand + progress)
const Chrome: React.FC<{ brand: ReelProps["brand"]; accent: string }> = ({ brand, accent }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = frame / durationInFrames;
  return (
    <>
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div style={{ position: "absolute", top: 0, left: 0, height: 6, width: `${p * 100}%`, background: accent, boxShadow: `0 0 12px ${accent}` }} />
        <div style={{ position: "absolute", top: 70, left: 60, fontFamily: SANS, fontWeight: 700, fontSize: 34, color: INK, letterSpacing: 1 }}>
          {brand.name}<span style={{ color: FAINT, fontWeight: 500 }}> · {brand.site}</span>
        </div>
      </AbsoluteFill>
    </>
  );
};

// ---------------------------------------------------------------- root
export const MavenReel: React.FC<ReelProps> = ({ fps, brand, scenes, subtitles, theme }) => {
  const frame = useCurrentFrame();
  const t = frame / fps;
  const accent = theme?.accent || TEAL;
  const active = [...scenes].reverse().find((s) => t >= s.start) ?? scenes[0];
  return (
    <AbsoluteFill>
      <Background scene={active} />
      {scenes.map((s, i) => (
        <Sequence key={i} from={Math.round(s.start * fps)} durationInFrames={Math.round(s.duration * fps)} layout="none">
          <SceneBody s={s} brand={brand} accent={accent} />
        </Sequence>
      ))}
      <Subtitles subs={subtitles} fps={fps} accent={accent} />
      <Chrome brand={brand} accent={accent} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- default sample props
export const defaultProps: ReelProps = {
  fps: 30, durationSeconds: 18,
  brand: { name: "Maven", site: "trymaven.in" },
  scenes: [
    { start: 0, duration: 1.4, kind: "hook", title: "Nifty moved. This is why.", accent: TEAL },
    { start: 1.4, duration: 3.0, kind: "stat", label: "NIFTY IT", value: -2.7, suffix: "%", sub: "3-year low" },
    { start: 4.4, duration: 2.2, kind: "chips", chips: ["Banks", "IT", "Energy", "Auto"] },
    { start: 6.6, duration: 3.4, kind: "reason", text: "US rate fears + AI disruption hit exporters" },
    { start: 10.0, duration: 3.0, kind: "chart", points: [8, 7.2, 7.4, 6, 5.2, 3.4, 2.7, 2.4] },
    { start: 13.0, duration: 2.4, kind: "reason", text: "When IT drops, the whole index feels it" },
    { start: 15.4, duration: 2.6, kind: "outro", text: "Understand the market with Maven" },
  ],
  subtitles: [
    { start: 0, end: 1.4, text: "Nifty moved. This is why.", emphasis: "why" },
    { start: 1.4, end: 4.4, text: "Nifty IT sank 2.7% — a 3-year low.", emphasis: "2.7%" },
    { start: 4.4, end: 6.6, text: "It dragged the whole market.", emphasis: "whole" },
    { start: 6.6, end: 10.0, text: "The trigger: US rates and AI fears.", emphasis: "AI" },
    { start: 10.0, end: 13.0, text: "A third straight down day.", emphasis: "third" },
    { start: 13.0, end: 15.4, text: "IT is a top index weight.", emphasis: "weight" },
    { start: 15.4, end: 18.0, text: "Understand the market with Maven.", emphasis: "Maven" },
  ],
};
