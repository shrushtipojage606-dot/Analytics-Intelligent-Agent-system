import type { Severity } from "../types/api";
import { SEVERITY_COLOR } from "../types/api";
import clsx from "clsx";

export function SeverityBadge({ severity, size = "sm" }: { severity: Severity; size?: "sm" | "md" }) {
  const color = SEVERITY_COLOR[severity];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border font-mono-data uppercase tracking-wider",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      )}
      style={{
        color,
        borderColor: `${color}55`,
        backgroundColor: `${color}14`,
      }}
    >
      <span
        className={clsx("h-1.5 w-1.5 rounded-full", (severity === "High" || severity === "Critical") && "animate-pulse-dot")}
        style={{ backgroundColor: color }}
      />
      {severity}
    </span>
  );
}
