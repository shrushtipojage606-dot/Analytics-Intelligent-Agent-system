import axios from "axios";
import type {
  AlertRecord,
  AlertSettings,
  AnalysisResult,
  DatasetProfile,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

export async function uploadDataset(file: File, sheetName?: string): Promise<DatasetProfile> {
  const form = new FormData();
  form.append("file", file);
  const params = sheetName ? { sheet_name: sheetName } : {};
  const { data } = await api.post<DatasetProfile>("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

export async function uploadSampleDataset(): Promise<DatasetProfile> {
  const { data } = await api.post<DatasetProfile>("/api/upload/sample");
  return data;
}

export async function getExcelSheets(file: File): Promise<string[]> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<{ sheets: string[] }>("/api/upload/sheets", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.sheets;
}

export async function runAnalysis(datasetId: string): Promise<AnalysisResult> {
  const { data } = await api.post<AnalysisResult>(`/api/analysis/${datasetId}/run`);
  return data;
}

export async function getAnalysis(datasetId: string): Promise<AnalysisResult> {
  const { data } = await api.get<AnalysisResult>(`/api/analysis/${datasetId}`);
  return data;
}

export async function getAlertSettings(): Promise<AlertSettings> {
  const { data } = await api.get<AlertSettings>("/api/alerts/settings");
  return data;
}

export async function updateAlertSettings(settings: AlertSettings): Promise<AlertSettings> {
  const { data } = await api.put<AlertSettings>("/api/alerts/settings", settings);
  return data;
}

export async function evaluateAlerts(datasetId: string): Promise<AlertRecord[]> {
  const { data } = await api.post<AlertRecord[]>(`/api/alerts/${datasetId}/evaluate`);
  return data;
}

export async function getAlertHistory(): Promise<AlertRecord[]> {
  const { data } = await api.get<AlertRecord[]>("/api/alerts/history");
  return data;
}

export interface ReportListItem {
  dataset_id: string;
  filename: string;
  uploaded_at: string;
  n_rows: number;
  n_columns: number;
  anomaly_count: number;
  status: string;
}

export async function listReports(): Promise<ReportListItem[]> {
  const { data } = await api.get<ReportListItem[]>("/api/upload/reports");
  return data;
}

/** Downloads the branded PDF report for a dataset and triggers a browser save. */
export async function downloadReportPdf(datasetId: string, filename: string): Promise<void> {
  const { data } = await api.get(`/api/report/download/${datasetId}`, { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  const safeName = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9-_]/g, "_") || "report";
  link.download = `${safeName}_analytics_report.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export interface EmailSubscribeRequest {
  email: string;
  notify_critical: boolean;
  notify_high: boolean;
  notify_metric_drops: boolean;
  notify_metric_increases: boolean;
  notify_data_quality: boolean;
  notify_daily_summary: boolean;
  notify_weekly_summary: boolean;
  threshold_pct: number;
  severity_threshold: AlertSettings["severity_threshold"];
  metrics_to_monitor: string[];
  alert_frequency: AlertSettings["alert_frequency"];
}

export async function subscribeEmailAlerts(payload: EmailSubscribeRequest): Promise<AlertSettings> {
  const { data } = await api.post<AlertSettings>("/api/email/subscribe", payload);
  return data;
}

export async function unsubscribeEmailAlerts(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>("/api/email/unsubscribe");
  return data;
}

export async function getEmailPreferences(): Promise<AlertSettings | null> {
  try {
    const { data } = await api.get<AlertSettings>("/api/email/preferences");
    return data;
  } catch {
    return null;
  }
}
