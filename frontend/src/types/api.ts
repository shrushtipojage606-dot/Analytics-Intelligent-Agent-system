export type Severity = "Normal" | "Low" | "Medium" | "High" | "Critical";

export const SEVERITY_COLOR: Record<Severity, string> = {
  Normal: "#2dd9c3",
  Low: "#5b8def",
  Medium: "#f5b942",
  High: "#ff6b6b",
  Critical: "#ff3d5a",
};

export const SEVERITY_ICON: Record<Severity, string> = {
  Normal: "🟢",
  Low: "🔵",
  Medium: "🟡",
  High: "🟠",
  Critical: "🚨",
};

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  dtype: string;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  is_constant: boolean;
  is_highly_sparse: boolean;
  sample_values: string[];
}

export interface DataQualityIssue {
  kind: string;
  description: string;
  severity: Severity;
  affected_count: number;
  recommendation: string;
}

export interface DataQualityReport {
  score: number;
  total_rows: number;
  total_columns: number;
  duplicate_rows: number;
  issues: DataQualityIssue[];
}

export interface DatasetProfile {
  dataset_id: string;
  filename: string;
  n_rows: number;
  n_columns: number;
  columns: ColumnProfile[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  id_columns: string[];
  kpi_candidate_columns: string[];
  preview: Record<string, unknown>[];
  quality: DataQualityReport;
}

export interface KPI {
  name: string;
  value: number;
  formatted_value: string;
  previous_value?: number | null;
  pct_change?: number | null;
  trend?: "up" | "down" | "flat" | null;
}

export interface TrendPoint {
  period: string;
  value: number;
}

export interface MetricTrend {
  metric: string;
  direction: "Increasing" | "Decreasing" | "Stable" | "Volatile";
  current_value: number;
  previous_value: number;
  absolute_change: number;
  pct_change: number;
  series: TrendPoint[];
}

export interface Anomaly {
  id: string;
  metric: string;
  dimension?: string | null;
  date?: string | null;
  current_value: number;
  expected_value: number;
  difference: number;
  pct_deviation: number;
  severity: Severity;
  method: string;
  business_impact: string;
  explanation: string;
  status: string;
}

export interface ChartSpec {
  id: string;
  chart_type: "line" | "bar" | "area" | "scatter" | "histogram" | "box" | "heatmap" | "pie";
  title: string;
  x_field?: string | null;
  y_field?: string | null;
  series_field?: string | null;
  data: Record<string, unknown>[];
  anomaly_markers: string[];
}

export interface BusinessInsight {
  id: string;
  title: string;
  severity: Severity;
  observed_facts: string[];
  possible_causes: string[];
  business_impact: string;
  recommended_action: string;
}

export interface ExecutiveSummary {
  summary: string;
  key_positive_trends: string[];
  key_negative_trends: string[];
  critical_anomalies: string[];
  business_risks: string[];
  business_opportunities: string[];
  recommended_actions: string[];
}

export interface AnalysisResult {
  dataset_id: string;
  profile: DatasetProfile;
  kpis: KPI[];
  trends: MetricTrend[];
  anomalies: Anomaly[];
  charts: ChartSpec[];
  insights: BusinessInsight[];
  executive_summary: ExecutiveSummary;
  generated_at: string;
}

export interface AlertSettings {
  email?: string | null;
  severity_threshold: Severity;
  metrics_to_monitor: string[];
  alert_frequency: "immediate" | "hourly" | "daily";
  enabled: boolean;
  notify_critical: boolean;
  notify_high: boolean;
  notify_metric_drops: boolean;
  notify_metric_increases: boolean;
  notify_data_quality: boolean;
  notify_daily_summary: boolean;
  notify_weekly_summary: boolean;
  threshold_pct: number;
  subscribed_at?: string | null;
}

export interface AlertRecord {
  id: string;
  date: string;
  metric: string;
  severity: Severity;
  status: string;
  email?: string | null;
}
