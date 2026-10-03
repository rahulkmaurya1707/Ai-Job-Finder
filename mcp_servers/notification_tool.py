import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
from config import get_logger

load_dotenv()

logger = get_logger(__name__)


def send_notification(
    message: str,
    subject: Optional[str] = "Job Finder Shortlist Notification",
    is_ping: bool = False,
) -> Dict[str, Any]:
    """Send notification via Telegram Bot API or SMTP Email.

    If is_ping is True, return ping status without sending notifications.
    If credentials are not configured in environment, safely log message.
    """
    if is_ping:
        logger.info("[PING] Notification tool ping check successful.")
        return {"status": "success", "message": "Notification tool reachable (ping check)"}

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    notification_email = os.getenv("NOTIFICATION_EMAIL", "").strip()

    sent_channels = []

    # 1. Telegram Bot API Notification
    if telegram_token and telegram_chat_id:
        try:
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": telegram_chat_id,
                "text": f"<b>{subject}</b>\n\n{message}",
                "parse_mode": "HTML",
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                sent_channels.append("Telegram")
            else:
                logger.warning(f"Telegram notification failed: {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram notification error: {e}")

    # 2. SMTP Email Notification
    if smtp_server and smtp_user and smtp_password and notification_email:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = notification_email
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, notification_email, msg.as_string())
            sent_channels.append("Email")
        except Exception as e:
            logger.warning(f"SMTP notification error: {e}")

    if sent_channels:
        success_msg = f"Notification successfully sent via {', '.join(sent_channels)}"
        logger.info(success_msg)
        return {"status": "success", "channels": sent_channels, "message": success_msg}

    # Fallback log if no live notification credentials configured
    logger.info(f"[NOTIFICATION LOGGED] Subject: {subject} | Body:\n{message}")

    return {
        "status": "logged_to_console",
        "channels": ["Console/Log"],
        "message": "No live notification credentials configured (TELEGRAM_BOT_TOKEN / SMTP). Notification logged.",
    }
