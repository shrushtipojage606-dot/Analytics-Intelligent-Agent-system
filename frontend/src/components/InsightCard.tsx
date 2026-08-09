import type { BusinessInsight } from "../types/api";
import { SeverityBadge } from "./SeverityBadge";

export function InsightCard({ insight }: { insight: BusinessInsight }) {
  return (
    <div className="rounded-xl border border-line bg-ink-850/80 p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="font-display text-sm font-semibold text-mist-100">{insight.title}</h3>
        <SeverityBadge severity={insight.severity} />
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wider text-signal-blue">Observed Facts</p>
          <ul className="space-y-1">
            {insight.observed_facts.map((f, i) => (
              <li key={i} className="font-mono-data text-xs leading-relaxed text-mist-300">{f}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wider text-signal-amber">Possible Causes</p>
          <ul className="space-y-1">
            {insight.possible_causes.map((c, i) => (
              <li key={i} className="text-xs leading-relaxed text-mist-400">{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wider text-mist-600">Business Impact</p>
          <p className="text-xs leading-relaxed text-mist-400">{insight.business_impact}</p>
        </div>
        <div className="rounded-lg border border-signal-teal/25 bg-signal-teal/5 p-3">
          <p className="mb-1 text-[10px] uppercase tracking-wider text-signal-teal">Recommended Action</p>
          <p className="text-xs leading-relaxed text-mist-200">{insight.recommended_action}</p>
        </div>
      </div>
    </div>
  );
}
