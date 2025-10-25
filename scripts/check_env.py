"""Simple environment checker for the SMS_AI project.

Usage (PowerShell):
  python .\scripts\check_env.py       # just prints parsed env variables (masked)
  python .\scripts\check_env.py --send-test  # attempt to send a test email using configured transport

The script will not print secrets directly; it masks them. It will try SendGrid first (if SENDGRID_API_KEY present) by doing a HEAD-like check (requests POST with minimal payload) and report status.
"""
import os
import json
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MASK_KEYS = ["SENDGRID_API_KEY", "SMTP_PASS", "PERSPECTIVE_API_KEY"]


def mask(v):
    if not v:
        return "<MISSING>"
    if len(v) <= 8:
        return v[:2] + "*" * (len(v) - 2)
    return v[:4] + "..." + v[-3:]


def show_env():
    keys = [
        "ADMIN_EMAIL",
        "FROM_EMAIL",
        "SENDGRID_API_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASS",

        "PERSPECTIVE_API_KEY",
    ]
    out = {}
    for k in keys:
        v = os.environ.get(k)
        out[k] = mask(v) if k in MASK_KEYS else (v or "<MISSING>")
    print(json.dumps(out, indent=2))


def test_send():
    import requests
    to_email = os.environ.get("ADMIN_EMAIL")
    sg = os.environ.get("SENDGRID_API_KEY")
    if sg:
        url = "https://api.sendgrid.com/v3/mail/send"
        from_email = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_USER") or to_email
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": "Test alert from SMS_AI",
            "content": [{"type": "text/plain", "value": "This is a test email from SMS_AI environment checker."}]
        }
        headers = {"Authorization": f"Bearer {sg}", "Content-Type": "application/json"}
        print("Sending test via SendGrid API...")
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=8)
            print("SendGrid response:", r.status_code, r.text[:1000])
            return r.status_code in (200, 202)
        except Exception as e:
            print("SendGrid request error:", e)
            return False
    else:
        print("No SENDGRID_API_KEY found; skipping SendGrid test.\nYou can test SMTP by running the Streamlit app and using Test Email button in the sidebar.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-test", action="store_true", help="Attempt to send a test email via SendGrid (if configured)")
    args = parser.parse_args()
    show_env()
    if args.send_test:
        ok = test_send()
        print("Test send result:", ok)
