"""Check the private Google mail endpoint without sending an email."""
import argparse
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.auth.google_mail import check_google_mail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".local" / "render.env")
    args = parser.parse_args()
    values = dotenv_values(args.env_file, interpolate=False)
    url, secret = values.get("GOOGLE_MAIL_URL"), values.get("GOOGLE_MAIL_SECRET")
    if not url or not secret:
        print("Google mail settings are incomplete. Save the deployed /exec URL and shared secret in the private Render env file.")
        return 2
    try:
        result = check_google_mail(url=url, secret=secret)
    except Exception:
        # Provider errors and URLs can contain private information.
        print("Google mail check failed. Check deployment access, script properties and owner authorization. No email was sent.")
        return 1
    print(json.dumps({"status": "authenticated", "remaining_daily_recipients": result["remainingDailyQuota"], "email_sent": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
