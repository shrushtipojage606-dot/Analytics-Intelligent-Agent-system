"""
Report Agent
--------------
Final stage of the pipeline: assembles the outputs of every upstream agent
into a single AnalysisResult, and can render a plain-text / markdown
executive report for export or emailing.
"""
from __future__ import annotations
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable,
)

from models.schemas import (
    AnalysisResult, DatasetProfile, KPI, MetricTrend, Anomaly, ChartSpec, BusinessInsight,
    ExecutiveSummary, Severity,
)

_SEVERITY_COLOR = {
    Severity.CRITICAL: colors.HexColor("#ff3d5a"),
    Severity.HIGH: colors.HexColor("#ff6b6b"),
    Severity.MEDIUM: colors.HexColor("#f5b942"),
    Severity.LOW: colors.HexColor("#5b8def"),
    Severity.NORMAL: colors.HexColor("#2dd9c3"),
}


def _pdf_safe(text: str) -> str:
    """The base-14 PDF fonts (Helvetica) don't include the ₹ glyph, which
    renders as a black box. Swap it for an ASCII-safe 'Rs.' so the report is
    readable everywhere without bundling extra font files into the app."""
    return text.replace("₹", "Rs. ") if isinstance(text, str) else text


def assemble_analysis_result(
    dataset_id: str, profile: DatasetProfile, kpis: list[KPI], trends: list[MetricTrend],
    anomalies: list[Anomaly], charts: list[ChartSpec], insights: list[BusinessInsight],
    executive_summary: ExecutiveSummary,
) -> AnalysisResult:
    return AnalysisResult(
        dataset_id=dataset_id, profile=profile, kpis=kpis, trends=trends, anomalies=anomalies,
        charts=charts, insights=insights, executive_summary=executive_summary,
        generated_at=datetime.now(timezone.utc),
    )


def render_markdown_report(result: AnalysisResult) -> str:
    p = result.profile
    lines = [
        f"# Analytics Report — {p.filename}",
        f"_Generated {result.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"## Data Quality: {p.quality.score}%",
        f"- Rows: {p.n_rows:,} | Columns: {p.n_columns} | Duplicate rows: {p.quality.duplicate_rows}",
        "",
        "## KPI Summary",
    ]
    for k in result.kpis:
        change = f" ({k.pct_change:+.1f}%)" if k.pct_change is not None else ""
        lines.append(f"- **{k.name}**: {k.formatted_value}{change}")

    lines += ["", "## Trend Detection"]
    for t in result.trends:
        lines.append(f"- **{t.metric}** → {t.direction} ({t.pct_change:+.1f}%)")

    lines += ["", f"## Anomalies ({len(result.anomalies)} total)"]
    for a in result.anomalies[:10]:
        lines.append(f"- [{a.severity.value}] {a.metric}{' — ' + a.dimension if a.dimension else ''} "
                      f"on {a.date or 'flagged record'}: {a.pct_deviation:+.1f}%")

    lines += ["", "## Executive Summary", result.executive_summary.summary]
    lines += ["", "### Recommended Actions"]
    for i, action in enumerate(result.executive_summary.recommended_actions, 1):
        lines.append(f"{i}. {action}")

    return "\n".join(lines)


def _footer(canvas, doc):  # noqa: ANN001
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7492"))
    canvas.drawString(2 * cm, 1.2 * cm, "Analytics Intelligence Agent — AI-generated report")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def render_pdf_report(result: AnalysisResult, brand: str = "Analytics Intelligence Agent") -> bytes:
    """Renders a full branded PDF report for an AnalysisResult using the real
    analysis output (no hardcoded/fake data)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Analytics Report — {result.profile.filename}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], textColor=colors.HexColor("#0a0f1a"), fontSize=22)
    h2 = ParagraphStyle("H2X", parent=styles["Heading2"], textColor=colors.HexColor("#1b2540"), spaceBefore=14, spaceAfter=8)
    body = ParagraphStyle("BodyX", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=colors.HexColor("#222"))
    small = ParagraphStyle("SmallX", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#6b7492"))

    p = result.profile
    story: list = []

    # --- Cover / header ---
    story.append(Paragraph(brand, ParagraphStyle("Brand", fontSize=11, textColor=colors.HexColor("#2dd9c3"))))
    story.append(Paragraph("Analytics Report", title_style))
    story.append(Paragraph(
        f"Dataset: <b>{p.filename}</b> &nbsp;|&nbsp; Generated: "
        f"{result.generated_at.strftime('%B %d, %Y %H:%M UTC')}", small,
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dde3f0")))
    story.append(Spacer(1, 6))

    # --- Executive summary ---
    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(_pdf_safe(result.executive_summary.summary), body))

    # --- Dataset summary / KPI overview ---
    story.append(Paragraph("Dataset Summary", h2))
    ds_rows = [
        ["Rows", f"{p.n_rows:,}", "Columns", str(p.n_columns)],
        ["Data Quality Score", f"{p.quality.score}%", "Duplicate Rows", str(p.quality.duplicate_rows)],
    ]
    ds_table = Table(ds_rows, colWidths=[3.5 * cm, 4 * cm, 3.5 * cm, 4 * cm])
    ds_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7492")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#6b7492")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#eef1f8")),
    ]))
    story.append(ds_table)

    if result.kpis:
        story.append(Paragraph("KPI Overview", h2))
        kpi_rows = [["Metric", "Value", "Change", "Trend"]] + [
            [k.name, _pdf_safe(k.formatted_value), f"{k.pct_change:+.1f}%" if k.pct_change is not None else "—", (k.trend or "—")]
            for k in result.kpis
        ]
        kpi_table = Table(kpi_rows, colWidths=[6 * cm, 4 * cm, 3 * cm, 3 * cm])
        kpi_table.setStyle(_std_table_style())
        story.append(kpi_table)

    if result.trends:
        story.append(Paragraph("Trend Analysis", h2))
        tr_rows = [["Metric", "Direction", "Current", "Previous", "% Change"]] + [
            [t.metric, t.direction, f"{t.current_value:,.2f}", f"{t.previous_value:,.2f}", f"{t.pct_change:+.1f}%"]
            for t in result.trends
        ]
        tr_table = Table(tr_rows, colWidths=[4.5 * cm, 3 * cm, 3 * cm, 3 * cm, 2.5 * cm])
        tr_table.setStyle(_std_table_style())
        story.append(tr_table)

    if result.anomalies:
        story.append(Paragraph(f"Detected Anomalies ({len(result.anomalies)})", h2))
        an_rows = [["Metric", "Severity", "Current", "Expected", "Deviation"]]
        row_colors = []
        for a in result.anomalies[:25]:
            an_rows.append([
                a.metric + (f" ({a.dimension})" if a.dimension else ""),
                a.severity.value,
                f"{a.current_value:,.2f}",
                f"{a.expected_value:,.2f}",
                f"{a.pct_deviation:+.1f}%",
            ])
            row_colors.append(_SEVERITY_COLOR.get(a.severity, colors.grey))
        an_table = Table(an_rows, colWidths=[5.5 * cm, 2.5 * cm, 3 * cm, 3 * cm, 2.5 * cm])
        ts = _std_table_style()
        for i, c in enumerate(row_colors, start=1):
            ts.add("TEXTCOLOR", (1, i), (1, i), c)
            ts.add("FONTNAME", (1, i), (1, i), "Helvetica-Bold")
        an_table.setStyle(ts)
        story.append(an_table)

        for a in result.anomalies[:8]:
            story.append(Paragraph(_pdf_safe(f"<b>{a.metric}</b> — {a.severity.value}: {a.explanation}"), body))

    if result.insights:
        story.append(Paragraph("AI Business Insights", h2))
        for ins in result.insights:
            story.append(Paragraph(_pdf_safe(f"<b>{ins.title}</b>"), body))
            story.append(Paragraph(_pdf_safe(f"Impact: {ins.business_impact}"), small))
            story.append(Paragraph(_pdf_safe(f"Recommended Action: {ins.recommended_action}"), small))
            story.append(Spacer(1, 6))

    story.append(Paragraph("Recommended Actions", h2))
    for i, action in enumerate(result.executive_summary.recommended_actions, 1):
        story.append(Paragraph(_pdf_safe(f"{i}. {action}"), body))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _std_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a0f1a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde3f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fd")]),
    ])
