import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, UploadCloud, FileSpreadsheet, Radar, Bell, TrendingUp } from "lucide-react";
import { uploadDataset, uploadSampleDataset, runAnalysis } from "../lib/api";

const STEPS = [
  { label: "Reading data", icon: FileSpreadsheet },
  { label: "Checking data quality", icon: Activity },
  { label: "Running AI analysis", icon: TrendingUp },
  { label: "Scanning for anomalies", icon: Radar },
  { label: "Generating insights", icon: Bell },
];

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setProcessing(true);
    setStepIndex(0);
    try {
      const stepTimer = setInterval(() => {
        setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
      }, 500);

      const profile = await uploadDataset(file);
      setStepIndex(2);
      await runAnalysis(profile.dataset_id);
      clearInterval(stepTimer);
      setStepIndex(STEPS.length - 1);

      setTimeout(() => navigate(`/dashboard/${profile.dataset_id}`), 400);
    } catch (err: any) {
      setProcessing(false);
      setError(err?.response?.data?.detail || "Something went wrong while processing your file.");
    }
  }, [navigate]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const handleSample = async () => {
    setError(null);
    setProcessing(true);
    setStepIndex(0);
    try {
      const stepTimer = setInterval(() => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1)), 400);
      const profile = await uploadSampleDataset();
      setStepIndex(2);
      await runAnalysis(profile.dataset_id);
      clearInterval(stepTimer);
      setStepIndex(STEPS.length - 1);
      setTimeout(() => navigate(`/dashboard/${profile.dataset_id}`), 300);
    } catch (err: any) {
      setProcessing(false);
      setError(err?.response?.data?.detail || "Could not load the sample dataset.");
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* ambient scan line */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden opacity-30">
        <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-signal-teal to-transparent animate-[scan-line_6s_linear_infinite]" />
      </div>

      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Radar className="text-signal-teal" size={20} />
          <span className="font-mono-data text-sm tracking-wide text-mist-300">ANALYTICS INTELLIGENCE AGENT</span>
        </div>
        <span className="rounded-full border border-line px-3 py-1 font-mono-data text-[10px] uppercase tracking-wider text-mist-600">
          v1.0 · autonomous
        </span>
      </header>

      <main className="mx-auto flex max-w-4xl flex-col items-center px-6 pb-24 pt-16 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-signal-teal/25 bg-signal-teal/5 px-3 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-signal-teal animate-pulse-dot" />
          <span className="font-mono-data text-[11px] uppercase tracking-wider text-signal-teal">Agent pipeline online</span>
        </div>

        <h1 className="font-display text-4xl font-semibold leading-tight text-mist-100 sm:text-5xl">
          Your data has a pulse.
          <br />
          <span className="text-mist-500">Let the agent read it.</span>
        </h1>
        <p className="mt-5 max-w-xl text-balance text-sm leading-relaxed text-mist-500 sm:text-base">
          Upload a spreadsheet. The agent understands the schema, cleans and scores it,
          detects anomalies, and writes the business explanation — no KPIs or charts to configure.
        </p>

        {!processing ? (
          <>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={`mt-10 flex w-full max-w-xl cursor-pointer flex-col items-center gap-4 rounded-2xl border-2 border-dashed px-10 py-14 transition-colors ${
                dragOver ? "border-signal-teal bg-signal-teal/5" : "border-line bg-ink-850/50 hover:border-ink-500"
              }`}
            >
              <UploadCloud size={32} className="text-signal-blue" />
              <div>
                <p className="font-medium text-mist-200">Drop your dataset here, or click to browse</p>
                <p className="mt-1 font-mono-data text-xs text-mist-600">.csv · .xlsx · .xls · up to 50MB</p>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
            </div>

            {error && (
              <div className="mt-4 w-full max-w-xl rounded-lg border border-signal-coral/30 bg-signal-coral/10 px-4 py-3 text-left text-sm text-signal-coral">
                {error}
              </div>
            )}

            <button
              onClick={handleSample}
              className="mt-6 font-mono-data text-xs text-mist-600 underline decoration-dotted underline-offset-4 hover:text-mist-300"
            >
              or explore with the sample sales dataset →
            </button>
          </>
        ) : (
          <div className="mt-14 w-full max-w-md space-y-3">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              const done = i < stepIndex;
              const active = i === stepIndex;
              return (
                <div
                  key={step.label}
                  className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors ${
                    active ? "border-signal-teal/40 bg-signal-teal/5" : done ? "border-line bg-ink-850/40" : "border-line/50 bg-transparent"
                  }`}
                >
                  <Icon size={16} className={active ? "text-signal-teal animate-pulse-dot" : done ? "text-mist-500" : "text-mist-700"} />
                  <span className={`font-mono-data text-xs ${active ? "text-mist-200" : done ? "text-mist-500" : "text-mist-700"}`}>
                    {step.label}
                  </span>
                  {done && <span className="ml-auto font-mono-data text-[10px] text-signal-teal">done</span>}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-20 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-3">
          {[
            { title: "Understands your schema", body: "Numeric, categorical, date, and ID columns are inferred automatically — nothing to configure." },
            { title: "Explains, not just describes", body: "Every anomaly separates observed fact from inferred cause, with a recommended next step." },
            { title: "Alerts your team", body: "High and critical anomalies can trigger deduplicated email alerts the moment they're found." },
          ].map((f) => (
            <div key={f.title} className="rounded-xl border border-line bg-ink-850/40 p-5">
              <p className="text-sm font-medium text-mist-200">{f.title}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-mist-600">{f.body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
