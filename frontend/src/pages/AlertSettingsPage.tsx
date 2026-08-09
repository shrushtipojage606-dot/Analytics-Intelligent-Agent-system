import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { BellRing, Send, CheckCircle2, Loader2 } from "lucide-react";
import {
  getAlertSettings,
  updateAlertSettings,
  evaluateAlerts,
  getAlertHistory,
  subscribeEmailAlerts,
} from "../lib/api";
import type { AlertSettings, AlertRecord } from "../types/api";
import { SeverityBadge } from "../components/SeverityBadge";
import { Shell } from "../components/Shell";

const THRESHOLDS = [5, 10, 15, 20];

const PREFERENCE_TOGGLES: { key: keyof AlertSettings; label: string }[] = [
  { key: "notify_critical", label: "Critical anomalies" },
  { key: "notify_high", label: "High-severity anomalies" },
  { key: "notify_metric_drops", label: "Metric drops" },
  { key: "notify_metric_increases", label: "Metric increases" },
  { key: "notify_data_quality", label: "Data quality issues" },
  { key: "notify_daily_summary", label: "Daily summary" },
  { key: "notify_weekly_summary", label: "Weekly business summary" },
];

export default function AlertSettingsPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [settings, setSettings] = useState<AlertSettings | null>(null);
  const [history, setHistory] = useState<AlertRecord[]>([]);
  const [saving, setSaving] = useState(false);
  const [justEnabled, setJustEnabled] = useState(false);
  const [customThreshold, setCustomThreshold] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState<string | null>(null);

  useEffect(() => {
    getAlertSettings().then((s) => {
      setSettings(s);
      setCustomThreshold(!THRESHOLDS.includes(s.threshold_pct));
    });
    getAlertHistory().then(setHistory);
  }, []);

  if (!settings) {
    return (
      <Shell datasetId={datasetId}>
        <div className="flex min-h-screen items-center justify-center">
          <span className="font-mono-data text-sm text-mist-500">Loading settings…</span>
        </div>
      </Shell>
    );
  }

  const enableAlerts = async () => {
    if (!settings.email) return;
    setSaving(true);
    setJustEnabled(false);
    try {
      const updated = await subscribeEmailAlerts({
        email: settings.email,
        notify_critical: settings.notify_critical,
        notify_high: settings.notify_high,
        notify_metric_drops: settings.notify_metric_drops,
        notify_metric_increases: settings.notify_metric_increases,
        notify_data_quality: settings.notify_data_quality,
        notify_daily_summary: settings.notify_daily_summary,
        notify_weekly_summary: settings.notify_weekly_summary,
        threshold_pct: settings.threshold_pct,
        severity_threshold: settings.severity_threshold,
        metrics_to_monitor: settings.metrics_to_monitor,
        alert_frequency: settings.alert_frequency,
      });
      setSettings(updated);
      setJustEnabled(true);
    } finally {
      setSaving(false);
    }
  };

  const saveOnly = async () => {
    setSaving(true);
    try {
      const updated = await updateAlertSettings(settings);
      setSettings(updated);
    } finally {
      setSaving(false);
    }
  };

  const runEvaluation = async () => {
    if (!datasetId) return;
    setEvaluating(true);
    setEvalMessage(null);
    try {
      const records = await evaluateAlerts(datasetId);
      const sent = records.filter((r) => r.status === "Sent").length;
      const skipped = records.filter((r) => r.status.startsWith("Skipped")).length;
      setEvalMessage(`${sent} alert(s) sent, ${skipped} skipped as duplicates, ${records.length} anomalies evaluated.`);
      getAlertHistory().then(setHistory);
    } catch (err: any) {
      setEvalMessage(err?.response?.data?.detail || "Could not evaluate alerts.");
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <Shell datasetId={datasetId}>
      <div className="min-h-screen pb-24">
        <header className="border-b border-line">
          <div className="mx-auto flex max-w-4xl items-center gap-3 px-6 py-4">
            <BellRing className="text-signal-teal" size={18} />
            <span className="font-mono-data text-sm text-mist-200">Email Alerts</span>
          </div>
        </header>

        <main className="mx-auto max-w-4xl space-y-8 px-6 pt-8">
          <section className="rounded-xl border border-line bg-ink-850/80 p-6">
            <p className="text-lg font-semibold text-mist-100">Never miss an important anomaly</p>
            <p className="mt-1 text-sm text-mist-500">
              Get notified automatically when our AI detects unusual changes in your business data.
            </p>

            <div className="mt-6 space-y-6">
              <div>
                <label className="mb-1.5 block text-xs text-mist-400">Email Address</label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={settings.email ?? ""}
                  onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                  className="w-full rounded-lg border border-line bg-ink-900 px-3 py-2 text-sm text-mist-100 outline-none focus:border-signal-teal/50"
                />
              </div>

              <div>
                <label className="mb-2 block text-xs text-mist-400">Alert Preferences</label>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {PREFERENCE_TOGGLES.map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2 rounded-lg border border-line/60 px-3 py-2 text-sm text-mist-300">
                      <input
                        type="checkbox"
                        checked={Boolean(settings[key])}
                        onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                        className="h-4 w-4 rounded border-line accent-[#2dd9c3]"
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-xs text-mist-400">Alert Threshold</label>
                <div className="flex flex-wrap gap-2">
                  {THRESHOLDS.map((t) => (
                    <button
                      key={t}
                      onClick={() => { setCustomThreshold(false); setSettings({ ...settings, threshold_pct: t }); }}
                      className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                        !customThreshold && settings.threshold_pct === t
                          ? "border-signal-teal/50 bg-signal-teal/10 text-signal-teal"
                          : "border-line text-mist-500 hover:border-ink-500"
                      }`}
                    >
                      {t}%
                    </button>
                  ))}
                  <button
                    onClick={() => setCustomThreshold(true)}
                    className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                      customThreshold
                        ? "border-signal-teal/50 bg-signal-teal/10 text-signal-teal"
                        : "border-line text-mist-500 hover:border-ink-500"
                    }`}
                  >
                    Custom
                  </button>
                  {customThreshold && (
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={settings.threshold_pct}
                      onChange={(e) => setSettings({ ...settings, threshold_pct: Number(e.target.value) })}
                      className="w-20 rounded-lg border border-line bg-ink-900 px-2 py-1.5 text-xs text-mist-100 outline-none focus:border-signal-teal/50"
                    />
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center gap-3">
              <button
                onClick={enableAlerts}
                disabled={saving || !settings.email}
                className="rounded-lg bg-signal-teal px-4 py-2 text-xs font-medium text-ink-950 transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Enable Email Alerts"}
              </button>
              <button
                onClick={saveOnly}
                disabled={saving}
                className="rounded-lg border border-line px-4 py-2 text-xs text-mist-300 hover:border-ink-500 disabled:opacity-50"
              >
                Save preferences only
              </button>

              {datasetId && (
                <button
                  onClick={runEvaluation}
                  disabled={evaluating}
                  className="ml-auto flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-xs text-mist-300 hover:border-signal-blue/40 disabled:opacity-50"
                >
                  {evaluating ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  {evaluating ? "Evaluating…" : "Evaluate current anomalies"}
                </button>
              )}
            </div>

            {justEnabled && (
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-signal-teal/30 bg-signal-teal/10 px-4 py-3">
                <CheckCircle2 size={16} className="text-signal-teal" />
                <div>
                  <p className="text-sm text-signal-teal">✓ Email alerts enabled</p>
                  <p className="text-xs text-mist-500">Anomaly notifications will be sent to your registered email.</p>
                </div>
              </div>
            )}
            {evalMessage && <p className="mt-3 font-mono-data text-xs text-mist-500">{evalMessage}</p>}
          </section>

          <section>
            <p className="mb-3 font-mono-data text-xs uppercase tracking-wider text-mist-600">Alert History</p>
            <div className="overflow-hidden rounded-xl border border-line bg-ink-850/80">
              {history.length === 0 ? (
                <p className="p-6 text-center text-xs text-mist-500">No alerts have been triggered yet.</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mist-600">
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium">Metric</th>
                      <th className="px-4 py-3 font-medium">Severity</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Email</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((r) => (
                      <tr key={r.id} className="border-b border-line/50 last:border-0">
                        <td className="px-4 py-3 font-mono-data text-xs text-mist-500">{r.date}</td>
                        <td className="px-4 py-3 text-mist-200">{r.metric}</td>
                        <td className="px-4 py-3"><SeverityBadge severity={r.severity} /></td>
                        <td className="px-4 py-3 font-mono-data text-xs text-mist-400">{r.status}</td>
                        <td className="px-4 py-3 font-mono-data text-xs text-mist-600">{r.email ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </main>
      </div>
    </Shell>
  );
}
