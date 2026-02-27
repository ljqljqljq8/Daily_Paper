from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from daily_paper.config import Settings


def send_email(settings: Settings, subject: str, html_body: str, text_body: str) -> None:
    if not settings.email_receivers:
        raise ValueError("EMAIL_RECEIVERS is empty.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_sender
    msg["To"] = ", ".join(settings.email_receivers)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, timeout=30) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.email_sender, settings.email_receivers, msg.as_string())
    else:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.email_sender, settings.email_receivers, msg.as_string())

