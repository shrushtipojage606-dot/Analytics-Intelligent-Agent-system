import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FileBarChart2, Search, Download, Loader2, ExternalLink } from "lucide-react";
import { listReports, downloadReportPdf, type ReportListItem } from "../lib/api";
import { Shell } from "../components/Shell";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    listReports()
      .then(setReports)
      .catch((err) => setError(err?.response?.data?.detail || "Could not load reports."));
  }, []);

  const filtered = useMemo(() => {
    if (!reports) return [];
    const q = query.trim().toLowerCase();
    if (!q) return reports;
    return reports.filter((r) => r.filename.toLowerCase().includes(q));
  }, [reports, query]);

  const handleDownload = async (r: ReportListItem) => {
    setDownloadingId(r.dataset_id);
    try {
      await downloadReportPdf(r.dataset_id, r.filename);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <Shell>
      <div className="min-h-screen pb-24">
        <header className="border-b border-line">
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-4">
            <FileBarChart2 className="text-signal-teal" size={18} />
            <div>
              <p className="font-mono-data text-sm text-mist-200">Reports</p>
              <p className="font-mono-data text-[10px] text-mist-600">Every dataset you've analyzed, with a one-click PDF download.</p>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-6xl space-y-6 px-6 pt-8">
          <div className="relative w-full max-w-sm">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-mist-600" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by dataset name…"
              className="w-full rounded-lg border border-line bg-ink-900 py-2 pl-9 pr-3 text-sm text-mist-100 outline-none focus:border-signal-teal/50"
            />
          </div>

          {error && <p className="text-sm text-signal-coral">{error}</p>}

          {!reports && !error && (
            <div className="flex items-center gap-2 text-mist-500">
              <Loader2 size={14} className="animate-spin" />
              <span className="font-mono-data text-xs">Loading reports…</span>
            </div>
          )}

          {reports && filtered.length === 0 && (
            <div className="rounded-xl border border-dashed border-line px-6 py-14 text-center">
              <p className="text-sm text-mist-400">No reports yet.</p>
              <Link to="/" className="mt-2 inline-block font-mono-data text-xs text-signal-teal underline underline-offset-4">
                Upload a dataset to get started →
              </Link>
            </div>
          )}

          {filtered.length > 0 && (
            <div className="overflow-hidden rounded-xl border border-line bg-ink-850/80">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mist-600">
                    <th className="px-4 py-3 font-medium">Report</th>
                    <th className="px-4 py-3 font-medium">Dataset</th>
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Anomalies</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => (
                    <tr key={r.dataset_id} className="border-b border-line/50 last:border-0">
                      <td className="px-4 py-3 text-mist-200">{r.filename.replace(/\.[^/.]+$/, "")} Analysis</td>
                      <td className="px-4 py-3 font-mono-data text-xs text-mist-400">{r.filename}</td>
                      <td className="px-4 py-3 font-mono-data text-xs text-mist-500">
                        {new Date(r.uploaded_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                      </td>
                      <td className="px-4 py-3 font-mono-data text-xs text-mist-300">{r.anomaly_count}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full border px-2 py-0.5 font-mono-data text-[10px] uppercase tracking-wider ${
                            r.status === "Ready"
                              ? "border-signal-teal/40 text-signal-teal bg-signal-teal/10"
                              : "border-line text-mist-500"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <Link
                            to={`/dashboard/${r.dataset_id}`}
                            className="flex items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-xs text-mist-400 hover:border-signal-blue/40 hover:text-mist-100"
                          >
                            <ExternalLink size={12} /> Open
                          </Link>
                          <button
                            onClick={() => handleDownload(r)}
                            disabled={downloadingId === r.dataset_id}
                            className="flex items-center gap-1 rounded-lg bg-signal-teal px-2.5 py-1.5 text-xs font-medium text-ink-950 hover:opacity-90 disabled:opacity-50"
                          >
                            {downloadingId === r.dataset_id ? (
                              <><Loader2 size={12} className="animate-spin" /> Generating…</>
                            ) : (
                              <><Download size={12} /> Download</>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>
    </Shell>
  );
}
