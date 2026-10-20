import importlib.util
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values

MODULE_PATH = Path(__file__).resolve().parents[1] / "prepare_render.py"
spec = importlib.util.spec_from_file_location("prepare_render", MODULE_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class PrivateRenderConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "neon.env"
        self.url = "postgresql://owner:test%24%27secret@ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
        self.source.write_text("NEON_DATABASE_URL='" + self.url + "'\n", encoding="utf-8")
        self.target = self.root / ".local" / "render.env"

    def test_roundtrip_keeps_credentials_literal_and_payments_disabled(self):
        helper.prepare(self.source, self.target, self.root / ".local")
        values = dotenv_values(self.target, interpolate=False)
        self.assertEqual(values["DATABASE_URL"], self.url)
        self.assertEqual(values["APP_ENV"], "production")
        self.assertEqual(values["LEGAL_READY"], "false")
        self.assertEqual(values["PLATEGA_ENABLED"], "false")
        self.assertEqual(values["MAIL_DELIVERY"], "google_apps_script")
        self.assertEqual(values["GOOGLE_MAIL_URL"], "")
        self.assertGreaterEqual(len(values["GOOGLE_MAIL_SECRET"]), 32)
        self.assertNotIn("PUBLIC_WEB_URL", values)
        self.assertGreaterEqual(len(values["AUTH_PROXY_SECRET"]), 32)
        Fernet(values["MAIL_ENCRYPTION_KEY"].encode())

    def test_never_overwrites_or_rotates_existing_keys(self):
        helper.prepare(self.source, self.target, self.root / ".local")
        before = self.target.read_bytes()
        with self.assertRaises(ValueError):
            helper.prepare(self.source, self.target, self.root / ".local")
        self.assertEqual(self.target.read_bytes(), before)

    def test_rejects_unignored_output(self):
        with self.assertRaises(ValueError):
            helper.prepare(self.source, self.root / "public.env", self.root / ".local")
        self.assertFalse((self.root / "public.env").exists())

    def test_rejects_unsafe_urls_without_disclosing_secret(self):
        for value in (self.url.replace("sslmode=require", "sslmode=disable"), self.url.replace(".neon.tech", ".example.com"), self.url + "\nnot-a-url", "psql '" + self.url + "'"):
            with self.subTest(value_type="malformed"):
                self.source.write_text("NEON_DATABASE_URL='" + value.replace("'", "\\'") + "'\n", encoding="utf-8")
                with self.assertRaises(ValueError) as error:
                    helper.read_neon_url(self.source)
                self.assertNotIn("secret", str(error.exception))

    def test_new_installations_have_different_signing_keys(self):
        a = helper.env_text(self.url)
        b = helper.env_text(self.url)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
