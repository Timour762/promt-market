"""Prepare a private Render env file; never read or reuse local application secrets."""
import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]


def read_neon_url(path: Path) -> str:
    value = dotenv_values(path, interpolate=False).get("NEON_DATABASE_URL")
    try:
        parts = urlsplit(value or "")
        valid = (
            parts.scheme in ("postgres", "postgresql", "postgresql+asyncpg")
            and parts.hostname
            and parts.hostname.endswith(".neon.tech")
            and parts.username
            and parts.password
            and parts.path not in ("", "/")
            and not parts.fragment
            and not any(char.isspace() for char in value)
            and parse_qs(parts.query).get("sslmode") in (["require"], ["verify-ca"], ["verify-full"])
        )
        parts.port  # Validate port syntax without displaying the URL on errors.
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("A valid private Neon URL with SSL is required in NEON_DATABASE_URL.")
    return value


def env_text(database_url: str) -> str:
    values = {
        "APP_ENV": "production",
        "DATABASE_URL": database_url,
        "COOKIE_SECURE": "true",
        "CSRF_SECRET": secrets.token_urlsafe(48),
        "AUTH_PROXY_SECRET": secrets.token_urlsafe(48),
        "MAIL_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "PAYMENT_DETAILS_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "MAIL_DELIVERY": "google_apps_script",
        "GOOGLE_MAIL_URL": "",
        "GOOGLE_MAIL_SECRET": secrets.token_urlsafe(48),
        "LEGAL_READY": "false",
        "LOCAL_TEST_ACCESS_ENABLED": "false",
        "SBER_SANDBOX_ENABLED": "false",
        "SBER_WEBHOOK_ENABLED": "false",
        "PLATEGA_ENABLED": "false",
    }
    lines = [
        "# Private Render configuration. Never commit or paste into chat.",
        "# Import into Render with Add from .env after completing the missing settings.",
        "# GOOGLE_MAIL_URL: paste the deployed Google Apps Script /exec URL.",
        "# Copy GOOGLE_MAIL_SECRET into the script property with the same name.",
        "# LEGAL_READY must stay false until seller details and documents are finalized.",
        "# The Render launcher derives the public HTTPS origin from RENDER_EXTERNAL_URL.",
        "# Keep these encryption/signing keys unchanged on future deployments.",
    ]
    for key, value in values.items():
        quoted = value.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"{key}='{quoted}'")
    return "\n".join(lines) + "\n"


def prepare(source: Path, output: Path, private_root: Path) -> None:
    private_root = private_root.resolve()
    output = output.resolve()
    if not output.is_relative_to(private_root):
        raise ValueError("Output must be inside the ignored .local directory.")
    # Check before generating keys; never rotate any existing deployment secrets.
    if output.exists():
        raise ValueError("Render configuration already exists; it was not changed.")
    database_url = read_neon_url(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as target:
        target.write(env_text(database_url))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neon-env", type=Path, default=ROOT / ".local" / "neon.env")
    parser.add_argument("--output", type=Path, default=ROOT / ".local" / "render.env")
    args = parser.parse_args()
    try:
        prepare(args.neon_env, args.output, ROOT / ".local")
    except (ValueError, OSError):
        # Do not display exceptions from URL/env parsers or paths containing input.
        print("Configuration was not written. Check the Neon file and ensure the private output does not already exist.")
        return 1
    print("Private Render configuration prepared. Google mail deployment and finalized documents are still required; no deployment was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
