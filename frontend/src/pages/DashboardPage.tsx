import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Radar, Bell, ArrowLeft, ListChecks, Download, Loader2, CheckCircle2 } from "lucide-react";
import { getAnalysis, downloadReportPdf } from "../lib/api";
import type { AnalysisResult } from "../types/api";
import { KpiCard } from "../components/KpiCard";
import { SignalStrip } from "../components/SignalStrip";
import { ChartCard } from "../components/ChartCard";
import { InsightCard } from "../components/InsightCard";
import { AnomalyTable } from "../components/AnomalyTable";
import { SeverityBadge } from "../components/SeverityBadge";
import { Shell } from "../components/Shell";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reportState, setReportState] = useState<"idle" | "generating" | "ready" | "error">("idle");

  useEffect(() => {
    if (!datasetId) return;
    getAnalysis(datasetId).then(setResult).catch((err) => {
      setError(err?.response?.data?.detail || "Could not load this analysis.");
    });
  }, [datasetId]);

  const handleDownloadReport = async () => {
    if (!datasetId || !result) return;
    setReportState("generating");
    try {
      await downloadReportPdf(datasetId, result.profile.filename);
      setReportState("ready");
      setTimeout(() => setReportState("idle"), 2500);
    } catch {
      setReportState("error");
      setTimeout(() => setReportState("idle"), 3000);
    }
  };

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-sm text-signal-coral">{error}</p>
        <Link to="/" className="font-mono-data text-xs text-mist-500 underline underline-offset-4">← Back to upload</Link>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-mist-500">
          <Radar className="animate-pulse-dot text-signal-teal" size={18} />
          <span className="font-mono-data text-sm">Loading analysis…</span>
        </div>
      </div>
    );
  }

  const { profile, kpis, anomalies, charts, insights, executive_summary } = result;
  const criticalCount = anomalies.filter((a) => a.severity === "Critical").length;
  const highCount = anomalies.filter((a) => a.severity === "High").length;

  return (
    <Shell datasetId={datasetId}>
    <div className="min-h-screen pb-24">
      <header className="sticky top-0 z-10 border-b border-line bg-ink-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-mist-600 hover:text-mist-300"><ArrowLeft size={16} /></Link>
            <Radar className="text-signal-teal" size={18} />
            <div>
              <p className="font-mono-data text-sm text-mist-200">{greeting()} 👋</p>
              <p className="font-mono-data text-[10px] text-mist-600">
                {profile.filename} · {profile.n_rows.toLocaleString()} rows · {profile.n_columns} cols · quality {profile.quality.score}%
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadReport}
              disabled={reportState === "generating"}
              className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs text-mist-300 transition-colors hover:border-signal-teal/40 hover:text-mist-100 disabled:opacity-60"
            >
              {reportState === "generating" && <><Loader2 size={14} className="animate-spin" /> Generating your report…</>}
              {reportState === "ready" && <><CheckCircle2 size={14} className="text-signal-teal" /> Report ready ✓</>}
              {reportState === "error" && <span className="text-signal-coral">Failed — try again</span>}
              {reportState === "idle" && <><Download size={14} /> Download Report</>}
            </button>
            <Link
              to={`/alerts/${datasetId}`}
              className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs text-mist-400 transition-colors hover:border-signal-teal/40 hover:text-mist-100"
            >
              <Bell size={14} /> Alert Settings
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-10 px-6 pt-8">
        <p className="-mb-4 text-sm text-mist-500">Here's your latest business intelligence summary.</p>
        {/* Overview */}
        <section>
          <SectionLabel>Overview</SectionLabel>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {kpis.slice(0, 6).map((k) => <KpiCard key={k.name} kpi={k} />)}
          </div>
        </section>

        {/* Signal Strip */}
        <section>
          <SignalStrip anomalies={anomalies} />
        </section>

        {/* Executive Summary */}
        <section>
          <SectionLabel>Executive Summary</SectionLabel>
          <div className="rounded-xl border border-line bg-ink-850/80 p-6">
            <p className="text-sm leading-relaxed text-mist-200">{executive_summary.summary}</p>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <SummaryList title="Positive Trends" color="text-signal-teal" items={executive_summary.key_positive_trends} />
              <SummaryList title="Negative Trends" color="text-signal-coral" items={executive_summary.key_negative_trends} />
              <SummaryList title="Business Risks" color="text-signal-amber" items={executive_summary.business_risks} />
              <SummaryList title="Opportunities" color="text-signal-blue" items={executive_summary.business_opportunities} />
            </div>
          </div>
        </section>

        {/* Trend Analysis */}
        {charts.length > 0 && (
          <section>
            <SectionLabel>Trend Analysis</SectionLabel>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {charts.map((c) => <ChartCard key={c.id} spec={c} />)}
            </div>
          </section>
        )}

        {/* Anomaly Center */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <SectionLabel>Anomaly Center</SectionLabel>
            <div className="flex gap-2">
              <span className="font-mono-data text-[10px] text-mist-600">{criticalCount} critical · {highCount} high</span>
            </div>
          </div>
          <AnomalyTable anomalies={anomalies.slice(0, 20)} />
        </section>

        {/* Business Insights */}
        {insights.length > 0 && (
          <section>
            <SectionLabel>Business Insights</SectionLabel>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {insights.map((i) => <InsightCard key={i.id} insight={i} />)}
            </div>
          </section>
        )}

        {/* Recommendations */}
        <section>
          <SectionLabel>Recommendations</SectionLabel>
          <div className="rounded-xl border border-line bg-ink-850/80 p-6">
            <ol className="space-y-3">
              {executive_summary.recommended_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-mist-300">
                  <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full border border-signal-teal/30 font-mono-data text-[10px] text-signal-teal">
                    {i + 1}
                  </span>
                  {a}
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Data Quality */}
        <section>
          <SectionLabel>Data Quality</SectionLabel>
          <div className="rounded-xl border border-line bg-ink-850/80 p-6">
            <div className="mb-4 flex items-center gap-4">
              <span className="font-mono-data text-3xl font-semibold text-mist-100">{profile.quality.score}%</span>
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-ink-700">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-signal-coral via-signal-amber to-signal-teal"
                    style={{ width: `${profile.quality.score}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              {profile.quality.issues.slice(0, 8).map((issue, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-line/60 px-3 py-2">
                  <SeverityBadge severity={issue.severity} />
                  <div className="flex-1">
                    <p className="text-xs text-mist-300">{issue.description}</p>
                    <p className="mt-0.5 flex items-center gap-1 text-[11px] text-mist-600">
                      <ListChecks size={11} /> {issue.recommendation}
                    </p>
                  </div>
                </div>
              ))}
              {profile.quality.issues.length === 0 && (
                <p className="text-xs text-mist-500">No data quality issues detected.</p>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
    </Shell>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 font-mono-data text-xs uppercase tracking-wider text-mist-600">{children}</p>;
}

function SummaryList({ title, color, items }: { title: string; color: string; items: string[] }) {
  return (
    <div>
      <p className={`mb-1.5 text-[10px] uppercase tracking-wider ${color}`}>{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-xs leading-relaxed text-mist-400">{item}</li>
        ))}
      </ul>
    </div>
  );
}
