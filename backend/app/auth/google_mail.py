"""Authenticated mail relay through the owner's Google Apps Script deployment."""
import hashlib
import hmac
import json
import ssl
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from uuid import UUID, uuid4

from pydantic import SecretStr
from app.core.config import get_settings, validate_google_mail_url


class NoGoogleMailRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Only the explicit ContentService GET below may follow a redirect.
        return None


def google_content_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 8192 or "\\" in value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise ValueError("Invalid Google mail redirect")
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname != "script.googleusercontent.com" or
            parts.port not in (None, 443) or parts.username is not None or parts.password is not None or parts.fragment):
        raise ValueError("Invalid Google mail redirect")
    return value


def _request_google_mail(payload: dict, *, url: str | None = None, secret: SecretStr | str | None = None) -> dict:
    """Authenticate a bounded request and verify its matching acknowledgement."""
    try:
        if url is None and secret is None:
            settings = get_settings()
            url, secret = settings.google_mail_url, settings.google_mail_secret
        url = validate_google_mail_url(url)
        secret = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        message_id = payload["id"]
        if not isinstance(secret, str) or len(secret.strip()) < 32 or str(UUID(message_id)) != message_id:
            raise ValueError("Invalid Google mail configuration or outbox ID")
        payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        encoded_payload = payload_text.encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), encoded_payload, hashlib.sha256).hexdigest()
        body = json.dumps({"payload": payload_text, "signature": signature}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(body) > 16384:
            raise ValueError("Google mail request is too large")
        request = Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoGoogleMailRedirects())
        try:
            response = opener.open(request, timeout=15)
        except HTTPError as error:
            code = error.code
            location = error.headers.get("Location") if error.headers else None
            error.close()
            if code not in (302, 303):
                raise ValueError("Google mail request failed")
            # Never forward the signed body, POST method, cookies or credentials.
            redirect = Request(google_content_url(location), headers={"Accept": "application/json"}, method="GET")
            response = opener.open(redirect, timeout=15)
        with response:
            if response.status != 200:
                raise ValueError("Unexpected Google mail response")
            raw = response.read(8193)
            if len(raw) > 8192:
                raise ValueError("Google mail response is too large")
            result = json.loads(raw)
            if not isinstance(result, dict) or result.get("ok") is not True or result.get("id") != message_id:
                raise ValueError("Google mail was not acknowledged")
            return result
    except Exception:
        # Never include the relay secret, payload, URL tokens or provider response.
        raise RuntimeError("Google mail delivery failed") from None


def send_google_mail(message_id: str, to: str, subject: str, text: str):
    """Send one outbox item with the same signed ID on every retry."""
    if (not isinstance(to, str) or not 1 <= len(to) <= 254 or not isinstance(subject, str) or
            not 1 <= len(subject) <= 200 or not isinstance(text, str) or not 1 <= len(text) <= 8000):
        raise RuntimeError("Google mail delivery failed")
    _request_google_mail({"op": "send", "id": message_id, "issued_at": int(time.time()),
                          "to": to, "subject": subject, "text": text})


def check_google_mail(*, url: str | None = None, secret: SecretStr | str | None = None) -> dict:
    """Check authentication/quota without sending; explicit relay credentials need no app settings."""
    result = _request_google_mail({"op": "check", "id": str(uuid4()), "issued_at": int(time.time())}, url=url, secret=secret)
    quota = result.get("remainingDailyQuota")
    if type(quota) is not int or quota < 0:
        raise RuntimeError("Google mail delivery failed")
    return result
