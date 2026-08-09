"""
Email Service
---------------
Thin wrapper around SMTP for sending anomaly alert emails. Credentials are
read exclusively from environment variables (never hardcoded). If SMTP is
not configured, calls are logged and treated as a no-op success in dev mode
so the rest of the pipeline can be exercised without real credentials.
"""
from __future__ import annotations
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models.schemas import Anomaly

logger = logging.getLogger("analytics_agent.email")


class EmailService:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.sender = os.getenv("ALERT_EMAIL_FROM", self.username or "alerts@analytics-agent.local")
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:5173")
        self.dry_run = not all([self.host, self.username, self.password])
        if self.dry_run:
            logger.warning("SMTP not fully configured — email_service running in DRY-RUN mode (no real emails sent).")

    def build_alert_email(self, dataset_name: str, anomaly: Anomaly) -> tuple[str, str]:
        subject_icon = "🚨" if anomaly.severity.value == "Critical" else "🔴"
        subject = f"{subject_icon} {anomaly.severity.value} Analytics Alert: {anomaly.metric} Anomaly Detected"
        body = f"""
Analytics Alert — {anomaly.severity.value} Severity

Dataset: {dataset_name}
Metric: {anomaly.metric}{f" ({anomaly.dimension})" if anomaly.dimension else ""}
Date/Time: {anomaly.date or "N/A"}

Current Value: {anomaly.current_value:,.2f}
Expected Value: {anomaly.expected_value:,.2f}
Deviation: {anomaly.difference:,.2f} ({anomaly.pct_deviation:+.1f}%)
Severity: {anomaly.severity.value}

Explanation:
{anomaly.explanation}

Business Impact:
{anomaly.business_impact}

Recommended Action:
Review this metric in the Anomaly Center and confirm whether this reflects
a genuine business event or a data-quality issue.

View full dashboard: {self.dashboard_url}/dashboard?dataset={dataset_name}
""".strip()
        return subject, body

    def send_alert(self, to_email: str, dataset_name: str, anomaly: Anomaly) -> bool:
        subject, body = self.build_alert_email(dataset_name, anomaly)
        if self.dry_run:
            logger.info("[DRY-RUN] Would send email to %s | Subject: %s", to_email, subject)
            return True

        msg = MIMEMultipart()
        msg["From"] = self.sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, [to_email], msg.as_string())
            logger.info("Alert email sent to %s for %s", to_email, anomaly.metric)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send alert email: %s", exc)
            return False


email_service = EmailService()
