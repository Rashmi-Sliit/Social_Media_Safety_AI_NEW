import os
import smtplib
from email.message import EmailMessage
import json

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


def send_alert(subject: str, body: str, to_email: str = None, force_smtp: bool = False):
    """
    Send an alert email using MailerSend API or SMTP as fallback.

    Returns:
        (True, None) on success.
        (False, error_message) on failure.
    """
    to_email = to_email or os.environ.get("ADMIN_EMAIL")
    if not to_email:
        return False, "No recipient email provided"

    ms_error = None

    # Try MailerSend API first
    ms_token = os.environ.get("MAILERSEND_API_KEY")
    from_email = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_USER") or to_email

    if ms_token and _HAS_REQUESTS and not force_smtp:
        try:
            url = "https://api.mailersend.com/v1/email"
            payload = {
                "from": {"email": from_email, "name": "Alert System"},
                "to": [{"email": to_email}],
                "subject": subject,
                "text": body
            }
            headers = {
                "Authorization": f"Bearer {ms_token}",
                "Content-Type": "application/json"
            }
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=8)
            if resp.status_code in (200, 202):
                return True, None
            ms_error = f"MailerSend failed: {resp.status_code} {resp.text}"
        except Exception as e:
            ms_error = f"MailerSend exception: {e}"

    # SMTP fallback (reliable)
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")

    if not all([to_email, host, port, user, password]):
        return False, ms_error or "Missing SMTP configuration"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True, None
    except Exception as e:
        smtp_err = f"SMTP exception: {e}"
        combined = ", ".join([s for s in [ms_error, smtp_err] if s])
        return False, combined
