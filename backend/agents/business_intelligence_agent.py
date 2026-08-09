"""
Business Intelligence Agent
------------------------------
Converts statistical findings (KPIs, trends, anomalies) into business-context
narratives: Observed Facts vs Possible Causes vs Business Impact vs
Recommended Action. Facts are always taken verbatim from computed numbers;
causes are explicitly labeled as inferences, never asserted as confirmed.

If ANTHROPIC_API_KEY is set, this agent asks the LLM to *interpret* the
already-computed statistics into fluent narrative text (the LLM never
computes or invents numbers itself — see generate_narrative()). Without a
key, a deterministic template-based fallback produces equivalent structured
output so the whole pipeline works offline / for grading without any
external API calls.
"""
from __future__ import annotations
import os
import re
import uuid
from typing import Optional

from models.schemas import (
    Anomaly, BusinessInsight, ExecutiveSummary, KPI, MetricTrend, Severity, SEVERITY_ORDER,
)

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


def _llm_client() -> Optional["anthropic.Anthropic"]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if key and _ANTHROPIC_AVAILABLE:
        return anthropic.Anthropic(api_key=key)
    return None


def generate_narrative(system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Ask the LLM to phrase pre-computed facts as fluent prose. Falls back to a template if no API key."""
    client = _llm_client()
    if not client:
        return fallback
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text.strip() or fallback
    except Exception:  # noqa: BLE001 — never let an LLM/network hiccup break the pipeline
        return fallback


NARRATIVE_SYSTEM_PROMPT = (
    "You are a business intelligence analyst. You will be given pre-computed statistics "
    "(facts) about a dataset. Write 1-3 fluent sentences interpreting them for a business "
    "stakeholder. Do NOT invent, recompute, or alter any numbers — only use the numbers given. "
    "Clearly distinguish confirmed facts from possible explanations."
)


def _anomaly_insight(anomaly: Anomaly) -> BusinessInsight:
    facts = [
        f"{anomaly.metric}{' (' + anomaly.dimension + ')' if anomaly.dimension else ''} "
        f"was {anomaly.current_value:,.2f} against an expected {anomaly.expected_value:,.2f} "
        f"on {anomaly.date or 'the affected record'} — a {anomaly.pct_deviation:+.1f}% deviation."
    ]
    causes = []
    if anomaly.dimension and "=" in (anomaly.dimension or ""):
        causes.append(f"The deviation is concentrated in {anomaly.dimension}, suggesting a localized rather than global cause.")
    else:
        causes.append("Insufficient data to determine the root cause with certainty; further segmentation is recommended.")

    fallback = (
        f"{anomaly.explanation} {causes[0]} {anomaly.business_impact}"
    )
    narrative = generate_narrative(
        NARRATIVE_SYSTEM_PROMPT,
        f"Anomaly detected — metric: {anomaly.metric}, dimension: {anomaly.dimension}, "
        f"date: {anomaly.date}, actual: {anomaly.current_value}, expected: {anomaly.expected_value}, "
        f"deviation: {anomaly.pct_deviation}%, severity: {anomaly.severity.value}. "
        f"Write a short business explanation.",
        fallback,
    )

    action = {
        Severity.CRITICAL: f"Investigate {anomaly.metric} immediately — pull the underlying records for "
                            f"{anomaly.dimension or 'this period'} and confirm whether this is a data issue or a real business event.",
        Severity.HIGH: f"Review {anomaly.metric} for {anomaly.dimension or 'this period'} within the next reporting cycle.",
        Severity.MEDIUM: f"Monitor {anomaly.metric} over the next few periods to see if the pattern persists.",
    }.get(anomaly.severity, f"Note the deviation in {anomaly.metric} for awareness; no immediate action required.")

    return BusinessInsight(
        id=str(uuid.uuid4()),
        title=f"{anomaly.metric} {'Decline' if anomaly.difference < 0 else 'Spike'}"
              f"{' — ' + anomaly.dimension if anomaly.dimension else ''}",
        severity=anomaly.severity,
        observed_facts=facts,
        possible_causes=causes,
        business_impact=anomaly.business_impact,
        recommended_action=action,
    )


def _trend_insight(trend: MetricTrend) -> Optional[BusinessInsight]:
    if trend.direction == "Stable":
        return None
    facts = [
        f"{trend.metric} moved from {trend.previous_value:,.2f} to {trend.current_value:,.2f} "
        f"({trend.pct_change:+.1f}%), classified as {trend.direction}."
    ]
    causes = ["Possible causes include seasonality, pricing/discount changes, or shifts in demand; "
              "cross-check against category or region-level breakdowns for confirmation."]
    severity = Severity.HIGH if abs(trend.pct_change) > 20 else (Severity.MEDIUM if abs(trend.pct_change) > 8 else Severity.LOW)
    impact = (f"This {trend.direction.lower()} trend in {trend.metric} is material enough to affect "
              f"period-over-period reporting and forecasts." if severity != Severity.LOW else
              f"This is a modest movement in {trend.metric}, likely within normal business variation.")
    action = (f"Investigate drivers of the {trend.direction.lower()} {trend.metric} trend and validate against "
              f"the anomaly center for related spikes/drops." if severity != Severity.LOW else
              f"Continue routine monitoring of {trend.metric}.")

    return BusinessInsight(
        id=str(uuid.uuid4()), title=f"{trend.metric} is {trend.direction}", severity=severity,
        observed_facts=facts, possible_causes=causes, business_impact=impact, recommended_action=action,
    )


def generate_insights(anomalies: list[Anomaly], trends: list[MetricTrend], max_insights: int = 8) -> list[BusinessInsight]:
    insights: list[BusinessInsight] = []
    # Prioritize the most severe anomalies first
    for a in sorted(anomalies, key=lambda x: SEVERITY_ORDER[x.severity], reverse=True)[:5]:
        insights.append(_anomaly_insight(a))
    for t in trends[:5]:
        ti = _trend_insight(t)
        if ti:
            insights.append(ti)
    return insights[:max_insights]


def generate_executive_summary(
    kpis: list[KPI], trends: list[MetricTrend], anomalies: list[Anomaly], insights: list[BusinessInsight],
) -> ExecutiveSummary:
    positives = [f"{t.metric} is {t.direction.lower()} ({t.pct_change:+.1f}%)" for t in trends if t.direction == "Increasing"][:4]
    negatives = [f"{t.metric} is {t.direction.lower()} ({t.pct_change:+.1f}%)" for t in trends if t.direction in ("Decreasing", "Volatile")][:4]
    critical = [f"{a.metric}{' — ' + a.dimension if a.dimension else ''} on {a.date or 'flagged record'} "
                f"({a.pct_deviation:+.1f}%)" for a in anomalies if a.severity in (Severity.CRITICAL, Severity.HIGH)][:5]

    risks = [i.business_impact for i in insights if i.severity in (Severity.HIGH, Severity.CRITICAL)][:3]
    opportunities = [f"{t.metric} growth ({t.pct_change:+.1f}%) may be worth reinforcing with additional investment."
                      for t in trends if t.direction == "Increasing"][:2]
    actions = [i.recommended_action for i in sorted(insights, key=lambda x: SEVERITY_ORDER[x.severity], reverse=True)][:5]

    kpi_fragment = "; ".join(f"{k.name} {k.formatted_value}" + (f" ({k.pct_change:+.1f}%)" if k.pct_change is not None else "")
                              for k in kpis[:3])
    fallback = (
        f"Overall performance summary based on {kpi_fragment}. "
        + (f"{len(positives)} metric(s) trending positively" if positives else "No strongly positive trends detected")
        + " while "
        + (f"{len(negatives)} metric(s) trending negatively." if negatives else "no strongly negative trends were detected.")
        + (f" {len(critical)} high/critical severity anomal{'y was' if len(critical)==1 else 'ies were'} detected and warrant investigation."
           if critical else " No high or critical severity anomalies were detected in this period.")
    )
    summary = generate_narrative(
        NARRATIVE_SYSTEM_PROMPT.replace("1-3 fluent sentences", "a 3-4 sentence executive summary"),
        f"KPIs: {kpi_fragment}. Positive trends: {positives}. Negative trends: {negatives}. "
        f"Critical/high anomalies: {critical}. Write an executive summary for a business stakeholder.",
        fallback,
    )

    return ExecutiveSummary(
        summary=summary,
        key_positive_trends=positives or ["No strongly positive trends detected this period."],
        key_negative_trends=negatives or ["No strongly negative trends detected this period."],
        critical_anomalies=critical or ["No critical or high-severity anomalies detected."],
        business_risks=risks or ["No significant business risks flagged."],
        business_opportunities=opportunities or ["No standout growth opportunities identified from current data."],
        recommended_actions=actions or ["Continue routine monitoring; no urgent action required."],
    )
