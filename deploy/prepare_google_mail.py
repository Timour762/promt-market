"""Switch private Render mail configuration without rotating existing secrets."""
import argparse
import os
import secrets
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def configure(path: Path, private_root: Path) -> None:
    path = path.resolve()
    if not path.is_relative_to(private_root.resolve()) or not path.is_file():
        raise ValueError("An existing private Render env file is required.")
    values = dotenv_values(path, interpolate=False)
    if not values.get("DATABASE_URL") or not values.get("CSRF_SECRET") or not values.get("MAIL_ENCRYPTION_KEY"):
        raise ValueError("Prepare the Render configuration first.")
    secret = values.get("GOOGLE_MAIL_SECRET")
    if secret and len(secret) < 32:
        raise ValueError("Existing Google mail secret is too short; it was not replaced.")
    if values.get("MAIL_DELIVERY") == "google_apps_script" and secret and "GOOGLE_MAIL_URL" in values:
        return
    values["MAIL_DELIVERY"] = "google_apps_script"
    values.setdefault("GOOGLE_MAIL_URL", "")
    values["GOOGLE_MAIL_SECRET"] = secret or secrets.token_urlsafe(48)
    lines = [
        "# Private Render configuration: never commit or share in chat.",
        "# Mail now uses your own Google Apps Script deployment.",
        "# Set GOOGLE_MAIL_SECRET in Apps Script Properties with the same value.",
        "# Paste the deployed /exec URL into GOOGLE_MAIL_URL.",
        "# Keep LEGAL_READY=false until seller details and documents are finalized.",
        "# Keep signing and encryption keys unchanged on future deployments.",
    ]
    for key, value in values.items():
        escaped = (value or "").replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"{key}='{escaped}'")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".google-mail-", suffix=".tmp", delete=False) as target:
            temporary = Path(target.name)
            target.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".local" / "render.env")
    args = parser.parse_args()
    try:
        configure(args.env_file, ROOT / ".local")
    except (OSError, ValueError):
        print("Configuration was not changed. Check the existing private Render env file.")
        return 1
    print("Private Google mail settings prepared; existing database, signing and encryption keys preserved. No message was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
