import type { Anomaly } from "../types/api";
import { SeverityBadge } from "./SeverityBadge";

export function AnomalyTable({ anomalies }: { anomalies: Anomaly[] }) {
  if (anomalies.length === 0) {
    return (
      <div className="rounded-xl border border-line bg-ink-850/80 p-8 text-center">
        <p className="text-sm text-mist-500">No anomalies detected — every monitored metric is within its expected range.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-ink-850/80">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mist-600">
            <th className="px-4 py-3 font-medium">Metric</th>
            <th className="px-4 py-3 font-medium">Dimension</th>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 text-right font-medium">Actual</th>
            <th className="px-4 py-3 text-right font-medium">Expected</th>
            <th className="px-4 py-3 text-right font-medium">Deviation</th>
            <th className="px-4 py-3 font-medium">Severity</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a) => (
            <tr key={a.id} className="border-b border-line/50 transition-colors last:border-0 hover:bg-ink-800/60">
              <td className="px-4 py-3 font-medium text-mist-200">{a.metric}</td>
              <td className="px-4 py-3 font-mono-data text-xs text-mist-500">{a.dimension ?? "—"}</td>
              <td className="px-4 py-3 font-mono-data text-xs text-mist-500">{a.date ?? "—"}</td>
              <td className="px-4 py-3 text-right font-mono-data text-xs text-mist-300">{a.current_value.toLocaleString()}</td>
              <td className="px-4 py-3 text-right font-mono-data text-xs text-mist-600">{a.expected_value.toLocaleString()}</td>
              <td className={`px-4 py-3 text-right font-mono-data text-xs ${a.pct_deviation < 0 ? "text-signal-coral" : "text-signal-teal"}`}>
                {a.pct_deviation > 0 ? "+" : ""}{a.pct_deviation.toFixed(1)}%
              </td>
              <td className="px-4 py-3"><SeverityBadge severity={a.severity} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
