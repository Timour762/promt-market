import json
import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError, URLError
from uuid import uuid4

from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings, get_settings


MAIL_KEY = Fernet.generate_key().decode()
BASE_SETTINGS = {"_env_file": None, "csrf_secret": "fixture-csrf-secret-at-least-32-characters",
                 "mail_encryption_key": MAIL_KEY}
BREVO_SETTINGS = {"mail_delivery": "brevo", "brevo_api_key": "fixture-api-key", "brevo_from": "sender@example.com"}
PRODUCTION_SETTINGS = {"app_env": "production", "auth_proxy_secret": "fixture-proxy-secret-at-least-32-characters",
                       "cookie_secure": True, "public_web_url": "https://shop.example.com",
                       "allowed_origins": ["https://shop.example.com"], "legal_ready": True}

# Importing the database module constructs an engine but never opens a connection.
# Supply fixture settings here so no local .env secrets are loaded by this suite.
with patch("app.core.config.get_settings", return_value=Settings(**BASE_SETTINGS)):
    from app.auth import mail
mail.get_settings = get_settings


def configured(**overrides):
    return Settings(**(BASE_SETTINGS | BREVO_SETTINGS | overrides))


class MailSettingsTests(unittest.TestCase):
    def test_brevo_requires_key_and_sender(self):
        for overrides in [{"brevo_api_key": None}, {"brevo_api_key": ""}, {"brevo_api_key": "   "},
                          {"brevo_from": None}, {"brevo_from": ""}, {"brevo_from": "invalid"}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                configured(**overrides)
        self.assertEqual(configured().mail_delivery, "brevo")
        self.assertEqual(Settings(**BASE_SETTINGS, brevo_from="").mail_delivery, "local")

    def test_production_supports_brevo_and_preserves_every_guard(self):
        self.assertEqual(configured(**PRODUCTION_SETTINGS).mail_delivery, "brevo")
        for overrides in [{"legal_ready": False}, {"auth_proxy_secret": None}, {"cookie_secure": False},
                          {"public_web_url": "http://shop.example.com"}, {"local_test_access_enabled": True},
                          {"sber_sandbox_enabled": True}, {"sber_webhook_enabled": True},
                          {"allowed_origins": ["http://shop.example.com"]}, {"mail_delivery": "local"}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                configured(**(PRODUCTION_SETTINGS | overrides))

    def test_smtp_remains_available_and_requires_credentials(self):
        settings = Settings(**BASE_SETTINGS, **PRODUCTION_SETTINGS, mail_delivery="smtp",
                            smtp_username="sender@example.com", smtp_password="fixture-smtp-password")
        self.assertEqual(settings.mail_delivery, "smtp")
        with self.assertRaises(ValidationError):
            Settings(**BASE_SETTINGS, mail_delivery="smtp")


class BrevoTransportTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"email": "recipient@example.com", "subject": "Подтверждение email", "text": "Ваше письмо",
                        "link": "https://shop.example.com/verify-email?token=fixture-token"}
        self.settings_patch = patch.object(mail, "get_settings", return_value=configured())
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def response(self, status=201, body=b'{"messageId":"<fixture-id>"}'):
        response = MagicMock()
        response.status = status
        response.read.return_value = body
        response.__enter__.return_value = response
        return response

    def test_verified_https_request_contains_transactional_text_and_no_redirect_handler(self):
        opener = MagicMock()
        opener.open.return_value = self.response()
        with patch.object(mail, "build_opener", return_value=opener) as build:
            mail.send_brevo_message(str(uuid4()), self.payload)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Api-key"), "fixture-api-key")
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 15)
        self.assertEqual(json.loads(request.data), {
            "sender": {"email": "sender@example.com", "name": "ПромтМаркет"},
            "to": [{"email": "recipient@example.com"}], "subject": self.payload["subject"],
            "textContent": mail.message_text(self.payload),
        })
        https_handler, redirect_handler = build.call_args.args
        self.assertTrue(https_handler._context.check_hostname)
        self.assertEqual(https_handler._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertIsInstance(redirect_handler, mail.NoMailRedirects)
        self.assertIsNone(redirect_handler.redirect_request(request, None, 302, "redirect", {}, "https://other.example"))

    def test_missing_success_or_malformed_response_fails_without_leaking_body(self):
        for response in [self.response(200), self.response(202), self.response(201, b"not-json"),
                         self.response(201, b"[]"), self.response(201, b"{}"),
                         self.response(201, b'{"messageId":""}'), self.response(201, b'{"messageId":1}'),
                         self.response(201, b"x" * 8193)]:
            opener = MagicMock()
            opener.open.return_value = response
            with self.subTest(response=response), patch.object(mail, "build_opener", return_value=opener), \
                    self.assertRaisesRegex(RuntimeError, "^Brevo mail delivery failed$"):
                mail.send_brevo_message(str(uuid4()), self.payload)

    def test_http_network_and_redirect_errors_are_sanitized(self):
        for error in [TimeoutError("fixture-api-key and recipient@example.com"),
                      URLError("private provider detail"),
                      HTTPError(mail.BREVO_EMAIL_URL, 429, "provider rate limit", {}, None),
                      HTTPError(mail.BREVO_EMAIL_URL, 302, "provider redirect", {}, None)]:
            opener = MagicMock()
            opener.open.side_effect = error
            with self.subTest(error=type(error).__name__), patch.object(mail, "build_opener", return_value=opener), \
                    self.assertRaisesRegex(RuntimeError, "^Brevo mail delivery failed$"):
                mail.send_brevo_message(str(uuid4()), self.payload)


class MailOutboxDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def dispatch(self, mode, failure=False):
        settings = configured(mail_delivery=mode)
        encrypted = Fernet(MAIL_KEY.encode()).encrypt(json.dumps({"email": "recipient@example.com",
            "subject": "Fixture", "text": "Text"}).encode()).decode()
        message = SimpleNamespace(id=uuid4(), attempts=0, encrypted_payload=encrypted, delivered_at=None, last_error=None)
        db = MagicMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        db.begin.return_value = db
        db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [message]))
        sender = MagicMock(side_effect=RuntimeError("private response") if failure else None)

        async def run(sender, *args):
            sender(*args)

        selected = {"local": "save_local_message", "smtp": "send_smtp_message", "brevo": "send_brevo_message"}[mode]
        with patch.object(mail, "get_settings", return_value=settings), patch.object(mail, "SessionFactory", return_value=db), \
                patch.object(mail, "run_in_threadpool", side_effect=run), patch.object(mail, selected, sender), \
                patch.object(mail, "logger") as logger:
            await mail.deliver_mail()
        sender.assert_called_once()
        self.assertEqual(sender.call_args.args[0], str(message.id))
        self.assertEqual(message.attempts, 1)
        if failure:
            self.assertIsNone(message.delivered_at)
            self.assertEqual(message.encrypted_payload, encrypted)
            self.assertEqual(message.last_error, "mail_delivery_failed")
            logger.warning.assert_called_once_with("Mail delivery failed; message remains queued")
        else:
            self.assertIsNotNone(message.delivered_at)
            self.assertIsNone(message.encrypted_payload)
            self.assertIsNone(message.last_error)

    async def test_brevo_success_acknowledges_and_erases_payload(self):
        await self.dispatch("brevo")

    async def test_brevo_failure_stays_queued(self):
        await self.dispatch("brevo", failure=True)

    async def test_local_and_smtp_dispatch_are_preserved(self):
        await self.dispatch("local")
        # SMTP settings remain checked by Settings, as in the production configuration.
        with patch.dict(BREVO_SETTINGS, {"smtp_username": "sender@example.com", "smtp_password": "fixture-password"}):
            await self.dispatch("smtp")


if __name__ == "__main__":
    unittest.main()
