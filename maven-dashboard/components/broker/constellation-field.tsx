"use client";

// The site's ONLY WebGL canvas: a subtle emerald particle constellation that
// sits between the aurora back plane and the orbit SVG in broker-hero.tsx.
// REVERT SEAM: delete the <ConstellationField /> line (and its dynamic import)
// in broker-hero.tsx — this file is otherwise inert and its chunk never loads.
//
// Gates (all must pass or we render nothing and the aurora remains the 0KB
// fallback): lg viewport, hardwareConcurrency > 4, WebGL context available.
// The frameloop hard-pauses when the hero leaves view or the tab is hidden.

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useEffect, useMemo, useRef, useState } from "react";

const COUNT = 800;
const RIM = 5.6; // disc radius — respawn distance for the inward drift
const EMERALD = new THREE.Color("#34d399");
const GOLD = new THREE.Color("#c9a961");

function Particles({ pointer, reduced, running }: {
  pointer: React.MutableRefObject<{ x: number; y: number }>; reduced: boolean; running: boolean;
}) {
  const ref = useRef<THREE.Points>(null);
  // frameloop="demand": we render only when there's something to show. invalidate()
  // schedules the next frame; the loop self-sustains while drifting and settles to
  // truly idle once the pointer parallax comes to rest (or under reduced motion).
  const invalidate = useThree((s) => s.invalidate);

  // angle + radius kept alongside positions so the inward drift is a cheap
  // radius decrement (no per-frame atan2); z stays constant per particle.
  const { positions, colors, angles, radii } = useMemo(() => {
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);
    const ang = new Float32Array(COUNT);
    const rad = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) {
      // disc distribution with depth — echoes the orbital rings above it
      const r = Math.sqrt(Math.random()) * RIM;
      const t = Math.random() * Math.PI * 2;
      ang[i] = t;
      rad[i] = r;
      pos[i * 3] = Math.cos(t) * r;
      pos[i * 3 + 1] = Math.sin(t) * r * 0.72;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 3.4;
      // ~1 in 14 particles is gold; the rest emerald at varying brightness
      const c = Math.random() < 0.07 ? GOLD : EMERALD;
      const dim = 0.35 + Math.random() * 0.65;
      col[i * 3] = c.r * dim;
      col[i * 3 + 1] = c.g * dim;
      col[i * 3 + 2] = c.b * dim;
    }
    return { positions: pos, colors: col, angles: ang, radii: rad };
  }, []);

  // kick a frame whenever we (re)enter view so the demand loop restarts
  useEffect(() => {
    if (running) invalidate();
  }, [running, invalidate]);

  // wake the demand loop on pointer input (the parallax target moved); gated by
  // `running` via a ref so an off-screen hero stays fully idle
  const runningRef = useRef(running);
  runningRef.current = running;
  useEffect(() => {
    const onMove = () => { if (runningRef.current) invalidate(); };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [invalidate]);

  useFrame(() => {
    const p = ref.current;
    if (!p) return;
    // inward radial drift is the read-only metaphor at the particle layer — data
    // flows toward the medallion, never out. DECORATIVE, so frozen under OS
    // reduced-motion. Time-based motion isn't needed here: a fixed per-frame step
    // reads as a steady inward current and stays deterministic under demand.
    if (!reduced) {
      const arr = p.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < COUNT; i++) {
        let rr = radii[i] - 0.006;
        if (rr < 0.12) {
          // respawn at the rim on a fresh angle — a continuous, seamless inflow
          rr = RIM;
          angles[i] = Math.random() * Math.PI * 2;
        }
        radii[i] = rr;
        arr[i * 3] = Math.cos(angles[i]) * rr;
        arr[i * 3 + 1] = Math.sin(angles[i]) * rr * 0.72;
      }
      p.geometry.attributes.position.needsUpdate = true;
    }
    // pointer parallax is input-driven (house .brand-motion treatment) and stays
    // live even under reduced motion; it eases toward the target each frame
    const tx = pointer.current.y * 0.22;
    const ty = pointer.current.x * 0.28;
    p.rotation.x += (tx - p.rotation.x) * 0.04;
    p.rotation.y += (ty - p.rotation.y) * 0.04;
    // keep the loop alive only while there's motion to render, and only in view
    if (running && (!reduced || Math.abs(tx - p.rotation.x) > 1e-4 || Math.abs(ty - p.rotation.y) > 1e-4)) {
      invalidate();
    }
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.045}
        vertexColors
        transparent
        opacity={0.5}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        sizeAttenuation
      />
    </points>
  );
}

export default function ConstellationField() {
  const hostRef = useRef<HTMLDivElement>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [capable, setCapable] = useState(false);
  const [running, setRunning] = useState(true);
  const [reduced, setReduced] = useState(false);

  // OS reduced-motion: freezes the decorative auto-drift (pointer parallax stays)
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  // capability gate — runs once on the client; SSR renders nothing
  useEffect(() => {
    if (!window.matchMedia("(min-width: 1024px)").matches) return;
    if ((navigator.hardwareConcurrency || 0) <= 4) return;
    try {
      const c = document.createElement("canvas");
      if (!c.getContext("webgl2") && !c.getContext("webgl")) return;
    } catch {
      return;
    }
    setCapable(true);
  }, []);

  // pause when the hero is off-screen or the tab is hidden
  useEffect(() => {
    if (!capable || !hostRef.current) return;
    let inView = true;
    let tabVisible = document.visibilityState === "visible";
    const apply = () => setRunning(inView && tabVisible);
    const io = new IntersectionObserver(([e]) => { inView = e.isIntersecting; apply(); }, { threshold: 0.05 });
    io.observe(hostRef.current);
    const onVis = () => { tabVisible = document.visibilityState === "visible"; apply(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", onVis); };
  }, [capable]);

  // pointer parallax source — window-level, normalized to [-1, 1]
  useEffect(() => {
    if (!capable) return;
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [capable]);

  if (!capable) return null;

  return (
    <div ref={hostRef} className="pointer-events-none absolute inset-0" aria-hidden>
      <Canvas
        dpr={[1, 1.5]}
        frameloop="demand"
        gl={{ antialias: false, alpha: true, powerPreference: "low-power" }}
        camera={{ position: [0, 0, 7], fov: 42 }}
      >
        <Particles pointer={pointer} reduced={reduced} running={running} />
      </Canvas>
    </div>
  );
}
