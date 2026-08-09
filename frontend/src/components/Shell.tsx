import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

export function Shell({ datasetId, children }: { datasetId?: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar datasetId={datasetId} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
