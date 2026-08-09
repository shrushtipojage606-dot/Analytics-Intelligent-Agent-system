import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceDot,
} from "recharts";
import type { ChartSpec } from "../types/api";

const AXIS_COLOR = "#6b7492";
const GRID_COLOR = "#202b47";

function ChartFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-ink-850/80 p-5">
      <p className="mb-4 text-xs uppercase tracking-wider text-mist-600">{title}</p>
      <ResponsiveContainer width="100%" height={240}>
        {children as any}
      </ResponsiveContainer>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: "#0e1524",
  border: "1px solid #202b47",
  borderRadius: 8,
  fontSize: 12,
  fontFamily: "JetBrains Mono, monospace",
  color: "#f4f6fb",
};

export function ChartCard({ spec }: { spec: ChartSpec }) {
  if (spec.chart_type === "line") {
    const markerSet = new Set(spec.anomaly_markers);
    return (
      <ChartFrame title={spec.title}>
        <LineChart data={spec.data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="period" stroke={AXIS_COLOR} tick={{ fontSize: 10 }} minTickGap={30} />
          <YAxis stroke={AXIS_COLOR} tick={{ fontSize: 10 }} width={50} />
          <Tooltip contentStyle={tooltipStyle} />
          <Line type="monotone" dataKey="value" stroke="#5b8def" strokeWidth={2} dot={false} />
          {spec.data.map((d, i) =>
            markerSet.has(String(d.period)) ? (
              <ReferenceDot key={i} x={String(d.period)} y={d.value as number} r={5} fill="#ff3d5a" stroke="none" />
            ) : null
          )}
        </LineChart>
      </ChartFrame>
    );
  }

  if (spec.chart_type === "bar" || spec.chart_type === "histogram") {
    const xKey = spec.chart_type === "bar" ? "category" : "bucket";
    return (
      <ChartFrame title={spec.title}>
        <BarChart data={spec.data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={xKey} stroke={AXIS_COLOR} tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
          <YAxis stroke={AXIS_COLOR} tick={{ fontSize: 10 }} width={50} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="value" fill="#2dd9c3" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartFrame>
    );
  }

  if (spec.chart_type === "scatter") {
    return (
      <ChartFrame title={spec.title}>
        <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" />
          <XAxis dataKey="x" stroke={AXIS_COLOR} tick={{ fontSize: 10 }} name={spec.x_field ?? "x"} />
          <YAxis dataKey="y" stroke={AXIS_COLOR} tick={{ fontSize: 10 }} name={spec.y_field ?? "y"} width={50} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={spec.data} fill="#f5b942" />
        </ScatterChart>
      </ChartFrame>
    );
  }

  if (spec.chart_type === "box") {
    return (
      <div className="rounded-xl border border-line bg-ink-850/80 p-5">
        <p className="mb-4 text-xs uppercase tracking-wider text-mist-600">{spec.title}</p>
        <div className="space-y-3">
          {spec.data.map((d: any, i) => (
            <div key={i} className="flex items-center gap-3 font-mono-data text-xs text-mist-300">
              <span className="w-24 truncate text-mist-500">{d.category}</span>
              <div className="relative h-2 flex-1 rounded bg-ink-700">
                <div
                  className="absolute h-2 rounded bg-signal-blue/40"
                  style={{
                    left: `${((d.q1 - d.min) / (d.max - d.min || 1)) * 100}%`,
                    width: `${((d.q3 - d.q1) / (d.max - d.min || 1)) * 100}%`,
                  }}
                />
                <div
                  className="absolute top-[-3px] h-3.5 w-0.5 bg-signal-teal"
                  style={{ left: `${((d.median - d.min) / (d.max - d.min || 1)) * 100}%` }}
                />
              </div>
              <span className="w-16 text-right text-mist-600">{Number(d.max).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
