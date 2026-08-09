import type { Anomaly } from "../types/api";
import { SEVERITY_COLOR } from "../types/api";

/**
 * The Signal Strip is this app's signature visual element: a horizontal
 * pulse line (like a vitals monitor) representing the dataset's health over
 * time, with anomalies rendered as colored blips sized by severity. It's
 * the first thing shown after analysis completes — a single glance answer
 * to "is anything wrong right now?"
 */
export function SignalStrip({ anomalies }: { anomalies: Anomaly[] }) {
  const dated = anomalies.filter((a) => a.date).slice(0, 40);
  const width = 1000;
  const height = 90;
  const midY = height / 2;

  // Build a simple synthetic waveform, spiking at anomaly positions
  const points: string[] = [];
  const n = 60;
  for (let i = 0; i <= n; i++) {
    const x = (i / n) * width;
    const isBeat = i % 6 === 0;
    const y = isBeat ? midY - 14 - Math.sin(i) * 4 : midY + Math.sin(i * 1.3) * 3;
    points.push(`${x},${y}`);
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-line bg-ink-850/80 p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-mist-600">Signal Strip</p>
          <p className="font-mono-data text-sm text-mist-300">
            {anomalies.length} anomal{anomalies.length === 1 ? "y" : "ies"} detected across monitored metrics
          </p>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono-data uppercase text-mist-600">
          {(["Critical", "High", "Medium", "Low"] as const).map((s) => (
            <span key={s} className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: SEVERITY_COLOR[s] }} />
              {s}
            </span>
          ))}
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="h-20 w-full" preserveAspectRatio="none">
        <line x1={0} y1={midY} x2={width} y2={midY} stroke="var(--color-line)" strokeWidth={1} strokeDasharray="2 4" />
        <polyline
          points={points.join(" ")}
          fill="none"
          stroke="var(--color-signal-blue)"
          strokeWidth={1.5}
          opacity={0.5}
        />
        {dated.map((a, i) => {
          const x = 40 + (i / Math.max(dated.length - 1, 1)) * (width - 80);
          const r = a.severity === "Critical" ? 7 : a.severity === "High" ? 5.5 : a.severity === "Medium" ? 4 : 3;
          const color = SEVERITY_COLOR[a.severity];
          return (
            <g key={a.id}>
              <line x1={x} y1={midY} x2={x} y2={midY - 25} stroke={color} strokeWidth={1} opacity={0.35} />
              <circle cx={x} cy={midY - 25} r={r} fill={color} opacity={0.9}>
                <title>{`${a.metric}${a.dimension ? " — " + a.dimension : ""} · ${a.date} · ${a.pct_deviation > 0 ? "+" : ""}${a.pct_deviation.toFixed(1)}%`}</title>
              </circle>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
