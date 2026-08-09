import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import type { KPI } from "../types/api";
import clsx from "clsx";

export function KpiCard({ kpi }: { kpi: KPI }) {
  const isUp = kpi.trend === "up";
  const isDown = kpi.trend === "down";
  const trendColor = isUp ? "text-signal-teal" : isDown ? "text-signal-coral" : "text-mist-500";

  return (
    <div className="group relative overflow-hidden rounded-xl border border-line bg-ink-850/80 p-5 transition-colors hover:border-ink-500">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-signal-blue/40 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <p className="text-xs uppercase tracking-wider text-mist-600">{kpi.name}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-mono-data text-2xl font-semibold text-mist-100">{kpi.formatted_value}</span>
      </div>
      {kpi.pct_change !== null && kpi.pct_change !== undefined && (
        <div className={clsx("mt-2 flex items-center gap-1 text-xs font-mono-data", trendColor)}>
          {isUp ? <ArrowUpRight size={14} /> : isDown ? <ArrowDownRight size={14} /> : <Minus size={14} />}
          <span>{kpi.pct_change > 0 ? "+" : ""}{kpi.pct_change.toFixed(1)}%</span>
          <span className="text-mist-600">vs previous period</span>
        </div>
      )}
    </div>
  );
}
