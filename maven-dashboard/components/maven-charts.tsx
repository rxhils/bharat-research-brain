"use client";
import { Fragment } from "react";
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from "recharts";
import type { CSSProperties, ReactNode } from "react";
import type { MavenChart } from "@/lib/maven-types";

const EM = "#34d399", ROSE = "#fb7185", AX = "#8b9298", GRID = "rgba(255,255,255,0.06)";
const TIP: CSSProperties = { background: "#0E1621", border: "1px solid rgba(255,255,255,0.10)", borderRadius: 10, fontSize: 12, color: "#e9ebed", padding: "6px 10px" };

function ChartCard({ title, subtitle, footer, wide = false, children }: { title: string; subtitle?: string; footer?: string; wide?: boolean; children: ReactNode }) {
  return (
    <div className={"rounded-2xl border border-hairline bg-white/[0.02] p-4 " + (wide ? "lg:col-span-2" : "")}>
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-[13px] font-medium text-ink">{title}</div>
        {subtitle && <div className="text-[10px] uppercase tracking-wider text-dim">{subtitle}</div>}
      </div>
      <div className="mt-3.5">{children}</div>
      {footer && <div className="mt-2.5 text-[10px] leading-snug text-dim">{footer}</div>}
    </div>
  );
}
function NoData({ title, wide = false }: { title: string; wide?: boolean }) {
  return <ChartCard title={title} wide={wide}><div className="grid h-[180px] place-items-center text-[11px] text-dim">Data unavailable</div></ChartCard>;
}

function BarCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} />;
  const xKey = c.xKey ?? "name"; const yKey = (c.yKeys && c.yKeys[0]) ?? "changePct";
  return (
    <ChartCard title={c.title} subtitle={c.description}>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 6, right: 8, left: -12, bottom: 6 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: AX, fontSize: 11 }} axisLine={false} tickLine={false} interval={0} angle={-18} textAnchor="end" height={52} />
          <YAxis tick={{ fill: AX, fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={TIP} />
          <Bar dataKey={yKey} radius={[4, 4, 0, 0]} maxBarSize={46}>
            {data.map((d, i) => <Cell key={i} fill={Number((d as any)[yKey]) >= 0 ? EM : ROSE} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function LineCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (data.length < 2) return <NoData title={c.title} />;
  const xKey = c.xKey ?? "i"; const yKey = (c.yKeys && c.yKeys[0]) ?? "price";
  return (
    <ChartCard title={c.title} subtitle={c.description}>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 6, right: 10, left: -12, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: AX, fontSize: 11 }} axisLine={false} tickLine={false} hide />
          <YAxis tick={{ fill: AX, fontSize: 11 }} axisLine={false} tickLine={false} width={48} domain={["dataMin", "dataMax"]} tickFormatter={(v) => Number(v).toFixed(0)} />
          <Tooltip contentStyle={TIP} />
          <Line type="monotone" dataKey={yKey} stroke={EM} strokeWidth={2.2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function TableCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} wide />;
  const cols = Object.keys(data[0]);
  return (
    <ChartCard title={c.title} subtitle={c.description} wide>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead><tr className="border-b border-hairline text-[11px] uppercase tracking-wider text-dim">{cols.map((k) => <th key={k} className="py-2 pr-4 font-medium">{k}</th>)}</tr></thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-hairline/50">
                {cols.map((k) => {
                  const v = (row as any)[k]; const num = typeof v === "number"; const isPct = k.toLowerCase().includes("change");
                  const cls = isPct && num ? (v >= 0 ? "text-emerald" : "text-rose") : "text-ink";
                  return <td key={k} className={"py-2.5 pr-4 tnum " + cls}>{num ? (isPct ? (v >= 0 ? "+" : "") + v + "%" : v) : String(v ?? "-")}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartCard>
  );
}

function HeatmapCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} wide />;
  const yKey = (c.yKeys && c.yKeys[0]) ?? "changePct"; const xKey = c.xKey ?? "name";
  return (
    <ChartCard title={c.title} subtitle={c.description} wide>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {data.map((d, i) => {
          const v = Number((d as any)[yKey]); const up = v >= 0;
          return (
            <div key={i} className={"rounded-xl border p-3 " + (up ? "border-emerald/25 bg-emerald/10" : "border-rose/25 bg-rose/10")}>
              <div className="text-[12px] text-ink">{String((d as any)[xKey])}</div>
              <div className={"mt-0.5 tnum text-base " + (up ? "text-emerald" : "text-rose")}>{(up ? "+" : "") + v + "%"}</div>
            </div>
          );
        })}
      </div>
    </ChartCard>
  );
}

function GaugeCard({ c }: { c: MavenChart }) {
  const d = (c.data && c.data[0]) as any; if (!d) return <NoData title={c.title} />;
  const adv = Number(d.advances ?? d.adv ?? 0), dec = Number(d.declines ?? d.dec ?? 0); const tot = adv + dec || 1;
  const ap = Math.round((adv / tot) * 100);
  return (
    <ChartCard title={c.title} subtitle={c.description}>
      <div className="flex h-4 overflow-hidden rounded-full bg-white/5"><div className="bg-emerald" style={{ width: ap + "%" }} /><div className="bg-rose" style={{ width: (100 - ap) + "%" }} /></div>
      <div className="mt-2 flex justify-between text-[12px]"><span className="text-emerald">Advances {adv}</span><span className="text-rose">Declines {dec}</span></div>
    </ChartCard>
  );
}

const ROLES = ["Driver", "Transmission", "Market variable", "Sector impact", "Risk"];
function roleFor(i: number, n: number): string {
  if (i === 0) return ROLES[0];
  if (i === n - 1) return ROLES[4];
  if (i === 1) return ROLES[1];
  if (i === n - 2) return ROLES[3];
  return ROLES[2];
}

export function MechanismStepper({ steps }: { steps?: { label?: string; step?: number }[] }) {
  const list = (steps ?? []).filter((s) => s && (s.label || s.step != null));
  if (!list.length) return null;
  const n = list.length;
  return (
    <div className="rounded-2xl border border-hairline bg-white/[0.02] p-4">
      <div className="mb-3.5 text-[13px] font-medium text-ink">Mechanism chain</div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        {list.map((s, i) => (
          <Fragment key={i}>
            <div className="min-w-0 flex-1 rounded-xl border border-hairline bg-panel/40 p-3">
              <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-emerald/80">{roleFor(i, n)}</div>
              <div className="mt-1.5 text-[12.5px] leading-snug text-ink/85">{String(s.label ?? s.step)}</div>
            </div>
            {i < n - 1 && (
              <div className="flex items-center justify-center px-1 text-emerald/60 sm:px-1.5">
                <span className="rotate-90 text-base sm:rotate-0" aria-hidden>&rarr;</span>
              </div>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

export function MavenChartRenderer({ charts }: { charts?: MavenChart[] }) {
  const list = (charts ?? []).filter((c) => c && !["flow", "flow_chart"].includes((c.type || "").toLowerCase()));
  if (!list.length) return null;
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {list.map((c, i) => {
        const t = (c.type || "").toLowerCase();
        if (t === "bar" || t === "stacked_bar" || t === "valuation_chart") return <BarCard key={i} c={c} />;
        if (t === "line" || t === "area") return <LineCard key={i} c={c} />;
        if (t === "comparison_table") return <TableCard key={i} c={c} />;
        if (t === "sector_heatmap") return <HeatmapCard key={i} c={c} />;
        if (t === "market_breadth_gauge") return <GaugeCard key={i} c={c} />;
        return null;
      })}
    </div>
  );
}