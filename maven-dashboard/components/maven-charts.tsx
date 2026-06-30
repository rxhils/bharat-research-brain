"use client";
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from "recharts";
import type { CSSProperties, ReactNode } from "react";
import type { MavenChart } from "@/lib/maven-types";

const EM = "#34d399", ROSE = "#fb7185", AX = "#5a616a", GRID = "rgba(255,255,255,0.06)";
const TIP: CSSProperties = { background: "#0E1621", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 11, color: "#e9ebed" };

function Panel({ title, desc, wide = false, children }: { title: string; desc?: string; wide?: boolean; children: ReactNode }) {
  return (
    <div className={"rounded-xl border border-hairline bg-white/[0.02] p-3 " + (wide ? "sm:col-span-2" : "")}>
      <div className="text-[11px] font-medium text-ink">{title}</div>
      {desc && <div className="mt-0.5 text-[10px] leading-snug text-dim">{desc}</div>}
      <div className="mt-2">{children}</div>
    </div>
  );
}
function NoData({ title }: { title: string }) {
  return <Panel title={title}><div className="py-6 text-center text-[11px] text-dim">Data unavailable</div></Panel>;
}

function BarCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} />;
  const xKey = c.xKey ?? "name"; const yKey = (c.yKeys && c.yKeys[0]) ?? "changePct";
  return (
    <Panel title={c.title} desc={c.description}>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} margin={{ top: 4, right: 6, left: -18, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: AX, fontSize: 10 }} axisLine={false} tickLine={false} interval={0} angle={-20} textAnchor="end" height={44} />
          <YAxis tick={{ fill: AX, fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={TIP} />
          <Bar dataKey={yKey} radius={[3, 3, 0, 0]}>
            {data.map((d, i) => <Cell key={i} fill={Number((d as any)[yKey]) >= 0 ? EM : ROSE} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Panel>
  );
}

function LineCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (data.length < 2) return <NoData title={c.title} />;
  const xKey = c.xKey ?? "i"; const yKey = (c.yKeys && c.yKeys[0]) ?? "price";
  return (
    <Panel title={c.title} desc={c.description}>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: AX, fontSize: 10 }} axisLine={false} tickLine={false} hide />
          <YAxis tick={{ fill: AX, fontSize: 10 }} axisLine={false} tickLine={false} domain={["dataMin", "dataMax"]} />
          <Tooltip contentStyle={TIP} />
          <Line type="monotone" dataKey={yKey} stroke={EM} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Panel>
  );
}

function TableCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} />;
  const cols = Object.keys(data[0]);
  return (
    <Panel title={c.title} desc={c.description} wide>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead><tr className="border-b border-hairline text-dim">{cols.map((k) => <th key={k} className="py-1.5 pr-3 font-medium capitalize">{k}</th>)}</tr></thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-hairline/50">
                {cols.map((k) => {
                  const v = (row as any)[k]; const num = typeof v === "number"; const isPct = k.toLowerCase().includes("change");
                  const cls = isPct && num ? (v >= 0 ? "text-emerald" : "text-rose") : "text-ink";
                  return <td key={k} className={"py-1.5 pr-3 tnum " + cls}>{num ? (isPct ? (v >= 0 ? "+" : "") + v + "%" : v) : String(v ?? "-")}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function FlowCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} />;
  return (
    <Panel title={c.title} desc={c.description} wide>
      <div className="flex flex-wrap items-center gap-1.5">
        {data.map((s, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <span className="rounded-md border border-hairline bg-white/[0.03] px-2 py-1 text-[11px] text-ink/80">{String((s as any).label ?? (s as any).step ?? "")}</span>
            {i < data.length - 1 && <span className="text-emerald" aria-hidden>&rarr;</span>}
          </span>
        ))}
      </div>
    </Panel>
  );
}

function HeatmapCard({ c }: { c: MavenChart }) {
  const data = c.data ?? []; if (!data.length) return <NoData title={c.title} />;
  const yKey = (c.yKeys && c.yKeys[0]) ?? "changePct"; const xKey = c.xKey ?? "name";
  return (
    <Panel title={c.title} desc={c.description} wide>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {data.map((d, i) => {
          const v = Number((d as any)[yKey]); const up = v >= 0;
          return (
            <div key={i} className={"rounded-lg border p-2 " + (up ? "border-emerald/25 bg-emerald/10" : "border-rose/25 bg-rose/10")}>
              <div className="text-[11px] text-ink">{String((d as any)[xKey])}</div>
              <div className={"tnum text-sm " + (up ? "text-emerald" : "text-rose")}>{(up ? "+" : "") + v + "%"}</div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function GaugeCard({ c }: { c: MavenChart }) {
  const d = (c.data && c.data[0]) as any; if (!d) return <NoData title={c.title} />;
  const adv = Number(d.advances ?? d.adv ?? 0), dec = Number(d.declines ?? d.dec ?? 0); const tot = adv + dec || 1;
  const ap = Math.round((adv / tot) * 100);
  return (
    <Panel title={c.title} desc={c.description}>
      <div className="flex h-3 overflow-hidden rounded-full bg-white/5"><div className="bg-emerald" style={{ width: ap + "%" }} /><div className="bg-rose" style={{ width: (100 - ap) + "%" }} /></div>
      <div className="mt-1.5 flex justify-between text-[11px]"><span className="text-emerald">Advances {adv}</span><span className="text-rose">Declines {dec}</span></div>
    </Panel>
  );
}

export function MavenChartRenderer({ charts }: { charts?: MavenChart[] }) {
  const list = (charts ?? []).filter(Boolean);
  if (!list.length) return null;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {list.map((c, i) => {
        const t = (c.type || "").toLowerCase();
        if (t === "bar" || t === "stacked_bar" || t === "valuation_chart") return <BarCard key={i} c={c} />;
        if (t === "line" || t === "area") return <LineCard key={i} c={c} />;
        if (t === "comparison_table") return <TableCard key={i} c={c} />;
        if (t === "flow" || t === "flow_chart") return <FlowCard key={i} c={c} />;
        if (t === "sector_heatmap") return <HeatmapCard key={i} c={c} />;
        if (t === "market_breadth_gauge") return <GaugeCard key={i} c={c} />;
        return null;
      })}
    </div>
  );
}