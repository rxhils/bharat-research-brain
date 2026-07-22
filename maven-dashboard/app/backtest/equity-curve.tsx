"use client";

// Full-period equity curve + underwater (drawdown) ribbon — the artifact every
// serious backtest report ships. Enhanced F+ vs Nifty 500 TRI, monthly,
// 2021-06 → 2026-05. Endpoints and max drawdowns are verbatim from the frozen
// engine (see data/equity-series.ts); the monthly shape between anchors is an
// interpolation for charting.

import { useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartReveal, useReducedMotionSafe } from "@/components/motion";
import { ENGINE_COMMIT, EQUITY_SERIES, MAX_DD_FPLUS, MAX_DD_NIFTY } from "./data/equity-series";

const EMERALD = "#34d399";
const SLATE = "#64748b";
const ROSE = "#fb7185";

const tipStyle = {
  background: "#0a0b0d",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  fontSize: 12,
};

const lakh = (n: number) => `₹${(n / 100000).toFixed(n >= 1000000 ? 0 : 1)}L`;
const inr = (n: number) => "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });

/** One draw pass on mount, then hard-disable; skipped under reduced motion
 *  (mirrors the bar-chart convention on this page). */
function useDrawOnce() {
  const reduce = useReducedMotionSafe();
  const [firstPass, setFirstPass] = useState(true);
  useEffect(() => {
    const id = window.setTimeout(() => setFirstPass(false), 1100);
    return () => window.clearTimeout(id);
  }, []);
  return firstPass && !reduce;
}

export function EquityCurve() {
  const draw = useDrawOnce();
  return (
    <div>
      <ChartReveal delay={0.05}>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={EQUITY_SERIES} margin={{ top: 8, right: 54, left: 4, bottom: 0 }} syncId="equity">
            <defs>
              <linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={EMERALD} stopOpacity={0.14} />
                <stop offset="100%" stopColor={EMERALD} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: SLATE, fontSize: 11 }} axisLine={false} tickLine={false} interval={11} />
            <YAxis
              tick={{ fill: SLATE, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={lakh}
              width={44}
              domain={[900000, 2400000]}
            />
            <Tooltip
              contentStyle={tipStyle}
              cursor={{ stroke: "rgba(255,255,255,0.15)" }}
              formatter={(v: number, name: string) => [inr(v), name]}
            />
            <Area
              type="monotone"
              dataKey="fplus"
              name="Enhanced F+"
              stroke={EMERALD}
              strokeWidth={2.2}
              fill="url(#eqfill)"
              isAnimationActive={draw}
              animationDuration={900}
              animationEasing="ease-out"
            />
            <Line
              type="monotone"
              dataKey="nifty"
              name="Nifty 500 TRI"
              stroke={SLATE}
              strokeWidth={1.4}
              dot={false}
              isAnimationActive={draw}
              animationDuration={900}
              animationEasing="ease-out"
            />
            {/* editorial end-of-line value labels — the conclusion on the chart */}
            <ReferenceDot
              x="May 26"
              y={2299700}
              r={3}
              fill={EMERALD}
              stroke="none"
              isFront
              label={{ value: "₹22.99L", position: "right", fill: EMERALD, fontSize: 11, fontWeight: 600 }}
            />
            <ReferenceDot
              x="May 26"
              y={1821735}
              r={3}
              fill={SLATE}
              stroke="none"
              isFront
              label={{ value: "₹18.22L", position: "right", fill: SLATE, fontSize: 11 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartReveal>

      {/* underwater ribbon — drawdown from running peak, shared x-axis */}
      <ChartReveal delay={0.15}>
        <ResponsiveContainer width="100%" height={110}>
          <ComposedChart data={EQUITY_SERIES} margin={{ top: 2, right: 54, left: 4, bottom: 0 }} syncId="equity">
            <defs>
              <linearGradient id="ddfill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={ROSE} stopOpacity={0.02} />
                <stop offset="100%" stopColor={ROSE} stopOpacity={0.16} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" tick={false} axisLine={false} tickLine={false} height={4} />
            <YAxis
              tick={{ fill: SLATE, fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={44}
              domain={[-20, 0]}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              contentStyle={tipStyle}
              cursor={{ stroke: "rgba(255,255,255,0.15)" }}
              formatter={(v: number, name: string) => [`${v.toFixed(2)}%`, name]}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.12)" />
            <Area
              type="monotone"
              dataKey="ddF"
              name="Enhanced F+ drawdown"
              stroke={ROSE}
              strokeWidth={1.4}
              fill="url(#ddfill)"
              isAnimationActive={draw}
              animationDuration={900}
              animationEasing="ease-out"
            />
            <Line
              type="monotone"
              dataKey="ddN"
              name="Nifty 500 drawdown"
              stroke={SLATE}
              strokeWidth={1.1}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={draw}
              animationDuration={900}
              animationEasing="ease-out"
            />
            {/* mark the worst point — the verbatim −14.05% max drawdown */}
            <ReferenceDot
              x="Feb 25"
              y={-14.05}
              r={3}
              fill={ROSE}
              stroke="none"
              isFront
              label={{ value: "−14.05% · worst point", position: "left", fill: ROSE, fontSize: 10 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartReveal>

      <p className="mt-3 text-[11px] leading-relaxed text-dim">
        ₹10,00,000 → ₹22,99,700 (+129.97%) vs the index&apos;s ₹18,21,735 (+82.17%), 2021-06-01 →
        2026-05-26, with max drawdowns of {MAX_DD_FPLUS}% vs {MAX_DD_NIFTY}%. Endpoints and both max
        drawdowns are verbatim from the frozen engine (commit {ENGINE_COMMIT}); the monthly path
        between those anchors is an interpolation of the committed simulation, drawn for shape.
        Backtested, not a live track record.
      </p>
    </div>
  );
}
