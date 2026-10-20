import hashlib
import hmac
import json
import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError, URLError
from uuid import uuid4

from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from app.auth import google_mail
from app.core.config import Settings, get_settings


MAIL_KEY = Fernet.generate_key().decode()
BASE = {"_env_file": None, "csrf_secret": "fixture-csrf-secret-at-least-32-characters", "mail_encryption_key": MAIL_KEY}
GOOGLE = {"mail_delivery": "google_apps_script", "google_mail_url": "https://script.google.com/macros/s/fixture-id/exec",
          "google_mail_secret": "fixture-google-secret-at-least-32-characters"}
PRODUCTION = {"app_env": "production", "auth_proxy_secret": "fixture-proxy-secret-at-least-32-characters",
              "cookie_secure": True, "public_web_url": "https://shop.example.com",
              "allowed_origins": ["https://shop.example.com"], "legal_ready": True}

with patch("app.core.config.get_settings", return_value=Settings(**BASE)):
    from app.auth import mail
mail.get_settings = get_settings


def configured(**overrides):
    return Settings(**(BASE | GOOGLE | overrides))


class GoogleMailSettingsTests(unittest.TestCase):
    def test_requires_endpoint_and_nonblank_32_character_secret(self):
        self.assertEqual(configured().mail_delivery, "google_apps_script")
        for overrides in [{"google_mail_url": None}, {"google_mail_url": ""}, {"google_mail_secret": None},
                          {"google_mail_secret": ""}, {"google_mail_secret": "short"}, {"google_mail_secret": " " * 32}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                configured(**overrides)
        self.assertIsNone(Settings(**BASE, google_mail_url="", google_mail_secret="").google_mail_secret)

    def test_rejects_non_google_and_non_deployment_endpoints(self):
        for url in ["http://script.google.com/macros/s/test/exec", "https://127.0.0.1/macros/s/test/exec",
                    "https://script.google.com.evil.example/macros/s/test/exec", "https://script.google.com@evil.example/macros/s/test/exec",
                    "https://user:password@script.google.com/macros/s/test/exec", "https://script.google.com:444/macros/s/test/exec",
                    "https://script.google.com/macros/s/test/dev", "https://script.google.com/macros/s/test/exec?key=value",
                    "https://script.google.com/macros/s/test/exec#fragment", "https://script.google.com/macros/s/test%2fother/exec",
                    "https://script.google.com/macros/s/test/exec\n", " https://script.google.com/macros/s/test/exec"]:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                configured(google_mail_url=url)
        self.assertTrue(configured(google_mail_url="https://script.google.com:443/macros/s/valid_id-123/exec"))

    def test_production_keeps_legal_https_and_other_guards(self):
        self.assertEqual(configured(**PRODUCTION).mail_delivery, "google_apps_script")
        for overrides in [{"legal_ready": False}, {"cookie_secure": False}, {"auth_proxy_secret": None},
                          {"public_web_url": "http://shop.example.com"}, {"allowed_origins": ["http://shop.example.com"]},
                          {"local_test_access_enabled": True}, {"sber_sandbox_enabled": True}, {"sber_webhook_enabled": True}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                configured(**(PRODUCTION | overrides))


class GoogleMailTransportTests(unittest.TestCase):
    def setUp(self):
        self.message_id = str(uuid4())
        settings = patch.object(google_mail, "get_settings", return_value=configured())
        settings.start()
        self.addCleanup(settings.stop)
        self.opener = MagicMock()
        factory = patch.object(google_mail, "build_opener", return_value=self.opener)
        self.factory = factory.start()
        self.addCleanup(factory.stop)
        self.opener.open.return_value = self.response()

    def response(self, status=200, body=None):
        response = MagicMock()
        response.status = status
        response.read.return_value = body if body is not None else json.dumps({"ok": True, "id": self.message_id}).encode()
        response.__enter__.return_value = response
        return response

    def send(self, **overrides):
        google_mail.send_google_mail(**({"message_id": self.message_id, "to": "buyer@example.com",
            "subject": "Подтверждение", "text": "Ссылка: https://shop.example.com/verify?token=fixture"} | overrides))

    def test_signed_compact_utf8_payload_and_verified_https(self):
        with patch.object(google_mail.time, "time", return_value=1800000000.75):
            self.send()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, GOOGLE["google_mail_url"])
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(self.opener.open.call_args.kwargs["timeout"], 15)
        self.assertLessEqual(len(request.data), 16384)
        envelope = json.loads(request.data)
        self.assertEqual(set(envelope), {"payload", "signature"})
        payload = json.loads(envelope["payload"])
        self.assertEqual(payload["id"], self.message_id)
        self.assertEqual(payload["issued_at"], 1800000000)
        self.assertEqual(payload["op"], "send")
        self.assertIn("Подтверждение", envelope["payload"])
        self.assertEqual(envelope["payload"], json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self.assertEqual(envelope["signature"], hmac.new(GOOGLE["google_mail_secret"].encode(), envelope["payload"].encode(), hashlib.sha256).hexdigest())
        self.assertNotIn(GOOGLE["google_mail_secret"], request.data.decode())
        https_handler, redirects = self.factory.call_args.args
        self.assertTrue(https_handler._context.check_hostname)
        self.assertEqual(https_handler._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertIsInstance(redirects, google_mail.NoGoogleMailRedirects)
        self.assertIsNone(redirects.redirect_request(request, None, 302, "redirect", {}, "https://other.example"))

    def test_google_content_redirect_is_exactly_one_get_without_body_or_credentials(self):
        target = "https://script.googleusercontent.com/macros/echo?user_content_key=fixture&lib=fixture"
        for code in [302, 303]:
            self.opener.open.reset_mock()
            self.opener.open.side_effect = [HTTPError(GOOGLE["google_mail_url"], code, "redirect", {"Location": target}, None), self.response()]
            self.send()
            self.assertEqual(self.opener.open.call_count, 2)
            initial, followup = [call.args[0] for call in self.opener.open.call_args_list]
            self.assertEqual(initial.get_method(), "POST")
            self.assertEqual(followup.full_url, target)
            self.assertEqual(followup.get_method(), "GET")
            self.assertIsNone(followup.data)
            self.assertEqual(dict(followup.header_items()), {"Accept": "application/json"})

    def test_rejects_external_credentials_http_and_multiple_redirects(self):
        for target in ["http://script.googleusercontent.com/echo", "https://script.googleusercontent.com.evil.example/echo",
                       "https://user:password@script.googleusercontent.com/echo", "https://script.googleusercontent.com:444/echo",
                       "https://127.0.0.1/echo", "//script.googleusercontent.com/echo", "https://script.googleusercontent.com/echo#fragment",
                       "https://script.googleusercontent.com\\@evil.example/echo", "https://script.googleusercontent.com/echo\n", None]:
            self.opener.open.reset_mock()
            self.opener.open.side_effect = HTTPError(GOOGLE["google_mail_url"], 302, "redirect", {"Location": target}, None)
            with self.subTest(target=target), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                self.send()
            self.assertEqual(self.opener.open.call_count, 1)
        self.opener.open.reset_mock()
        self.opener.open.side_effect = [HTTPError(GOOGLE["google_mail_url"], 302, "redirect",
            {"Location": "https://script.googleusercontent.com/echo?key=fixture"}, None),
            HTTPError("https://script.googleusercontent.com/echo", 302, "redirect",
                {"Location": "https://script.googleusercontent.com/echo?key=again"}, None)]
        with self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
            self.send()
        self.assertEqual(self.opener.open.call_count, 2)

    def test_requires_200_true_and_matching_id_with_bounded_json(self):
        for status, body in [(201, None), (200, b"not-json"), (200, b"[]"), (200, b"{}"),
                             (200, json.dumps({"ok": False, "id": self.message_id}).encode()),
                             (200, json.dumps({"ok": 1, "id": self.message_id}).encode()),
                             (200, json.dumps({"ok": True, "id": str(uuid4())}).encode()), (200, b"x" * 8193)]:
            self.opener.open.return_value = self.response(status, body)
            with self.subTest(status=status, body=body), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                self.send()

    def test_network_errors_are_sanitized_without_retry(self):
        for error in [TimeoutError("private signed body"), URLError("fixture-secret"),
                      HTTPError(GOOGLE["google_mail_url"], 429, "private response", {}, None),
                      HTTPError(GOOGLE["google_mail_url"], 307, "unsupported redirect", {"Location": "https://script.googleusercontent.com/echo"}, None)]:
            self.opener.open.reset_mock()
            self.opener.open.side_effect = error
            with self.subTest(error=type(error).__name__), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                self.send()
            self.assertEqual(self.opener.open.call_count, 1)

    def test_payload_and_field_bounds_fail_before_a_request(self):
        for overrides in [{"message_id": "not-a-uuid"}, {"to": "x" * 255}, {"subject": "x" * 201},
                          {"text": "x" * 8001}, {"text": ""}, {"text": "🟣" * 8000}]:
            with self.subTest(overrides=list(overrides)), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                self.send(**overrides)
        self.opener.open.assert_not_called()

    def test_no_send_probe_is_signed_and_requires_matching_id_and_quota(self):
        def response_for_probe(request, **kwargs):
            payload = json.loads(json.loads(request.data)["payload"])
            self.assertEqual(set(payload), {"op", "id", "issued_at"})
            self.assertEqual(payload["op"], "check")
            return self.response(body=json.dumps({"ok": True, "id": payload["id"], "remainingDailyQuota": 100}).encode())

        self.opener.open.side_effect = response_for_probe
        result = google_mail.check_google_mail()
        self.assertEqual(result["remainingDailyQuota"], 100)
        self.assertTrue(result["ok"])

    def test_explicit_probe_does_not_load_app_settings_or_relax_production_guard(self):
        with patch.object(google_mail, "get_settings", side_effect=AssertionError("App settings must not be loaded")), \
                patch.object(google_mail, "uuid4", return_value=uuid4()) as make_id:
            identifier = str(make_id.return_value)
            self.opener.open.return_value = self.response(body=json.dumps({"ok": True, "id": identifier, "remainingDailyQuota": 100}).encode())
            result = google_mail.check_google_mail(url=GOOGLE["google_mail_url"], secret=SecretStr(GOOGLE["google_mail_secret"]))
            self.assertEqual(result["id"], identifier)
        with self.assertRaises(ValidationError):
            configured(**(PRODUCTION | {"legal_ready": False}))

    def test_probe_requires_valid_quota_and_complete_explicit_credentials(self):
        with patch.object(google_mail, "uuid4", return_value=uuid4()) as make_id:
            identifier = str(make_id.return_value)
            for quota in [None, True, -1, "100"]:
                self.opener.open.return_value = self.response(body=json.dumps({"ok": True, "id": identifier, "remainingDailyQuota": quota}).encode())
                with self.subTest(quota=quota), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                    google_mail.check_google_mail()
        self.opener.open.reset_mock()
        for explicit in [{"url": GOOGLE["google_mail_url"]}, {"secret": GOOGLE["google_mail_secret"]},
                         {"url": "https://other.example/exec", "secret": GOOGLE["google_mail_secret"]}]:
            with self.subTest(keys=list(explicit)), self.assertRaisesRegex(RuntimeError, "^Google mail delivery failed$"):
                google_mail.check_google_mail(**explicit)
        self.opener.open.assert_not_called()


class GoogleOutboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_dispatch_preserves_link_and_failed_payload(self):
        for fails in [False, True]:
            payload = {"email": "buyer@example.com", "subject": "Подтверждение", "text": "Откройте ссылку",
                       "link": "https://shop.example.com/verify?token=fixture"}
            encrypted = Fernet(MAIL_KEY.encode()).encrypt(json.dumps(payload).encode()).decode()
            item = SimpleNamespace(id=uuid4(), attempts=0, encrypted_payload=encrypted, delivered_at=None, last_error=None)
            db = MagicMock()
            db.__aenter__ = AsyncMock(return_value=db)
            db.__aexit__ = AsyncMock(return_value=False)
            db.begin.return_value = db
            db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [item]))

            async def run(sender, *args):
                sender(*args)

            with patch.object(mail, "get_settings", return_value=configured()), patch.object(mail, "SessionFactory", return_value=db), \
                    patch.object(mail, "run_in_threadpool", side_effect=run), \
                    patch.object(mail, "send_google_mail", side_effect=RuntimeError("private detail") if fails else None) as sender, \
                    patch.object(mail, "logger") as logger:
                await mail.deliver_mail()
            sender.assert_called_once_with(str(item.id), payload["email"], payload["subject"], mail.message_text(payload))
            self.assertEqual(item.attempts, 1)
            self.assertEqual(item.encrypted_payload, encrypted if fails else None)
            if fails:
                self.assertIsNone(item.delivered_at)
                self.assertEqual(item.last_error, "mail_delivery_failed")
                logger.warning.assert_called_once_with("Mail delivery failed; message remains queued")
            else:
                self.assertIsNotNone(item.delivered_at)
                self.assertIsNone(item.last_error)


if __name__ == "__main__":
    unittest.main()
