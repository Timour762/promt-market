import importlib.util
import tempfile
import unittest
from pathlib import Path

from dotenv import dotenv_values

MODULE_PATH = Path(__file__).resolve().parents[1] / "prepare_google_mail.py"
spec = importlib.util.spec_from_file_location("prepare_google_mail", MODULE_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class GoogleMailPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / ".local"
        self.root.mkdir()
        self.path = self.root / "render.env"
        self.original = {
            "DATABASE_URL": "postgresql://owner:fixture%24pass@example.neon.tech/db?sslmode=require",
            "CSRF_SECRET": "fixture-csrf-key",
            "AUTH_PROXY_SECRET": "fixture-proxy-key",
            "MAIL_ENCRYPTION_KEY": "fixture-encryption-key",
            "MAIL_DELIVERY": "brevo",
            "LEGAL_READY": "false",
            "BREVO_API_KEY": "fixture-old-api-key",
        }
        self.path.write_text("\n".join(f"{key}='{value}'" for key, value in self.original.items()) + "\n", encoding="utf-8")

    def test_switch_preserves_existing_keys_and_legal_flag(self):
        helper.configure(self.path, self.root)
        values = dotenv_values(self.path, interpolate=False)
        for key, value in self.original.items():
            if key != "MAIL_DELIVERY":
                self.assertEqual(values[key], value)
        self.assertEqual(values["MAIL_DELIVERY"], "google_apps_script")
        self.assertEqual(values["GOOGLE_MAIL_URL"], "")
        self.assertGreaterEqual(len(values["GOOGLE_MAIL_SECRET"]), 32)

    def test_repeated_run_does_not_rotate_mail_secret_or_rewrite_file(self):
        helper.configure(self.path, self.root)
        before = self.path.read_bytes()
        helper.configure(self.path, self.root)
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_endpoint_and_valid_secret_are_preserved(self):
        with self.path.open("a", encoding="utf-8") as target:
            target.write("GOOGLE_MAIL_URL='https://script.google.com/macros/s/example/exec'\nGOOGLE_MAIL_SECRET='fixture-secret-that-is-at-least-32-characters'\n")
        helper.configure(self.path, self.root)
        values = dotenv_values(self.path, interpolate=False)
        self.assertEqual(values["GOOGLE_MAIL_URL"], "https://script.google.com/macros/s/example/exec")
        self.assertEqual(values["GOOGLE_MAIL_SECRET"], "fixture-secret-that-is-at-least-32-characters")

    def test_invalid_existing_secret_and_unignored_output_are_not_overwritten(self):
        with self.path.open("a", encoding="utf-8") as target:
            target.write("GOOGLE_MAIL_SECRET='short'\n")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            helper.configure(self.path, self.root)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(ValueError):
            helper.configure(self.path, self.root / "different")


if __name__ == "__main__":
    unittest.main()
