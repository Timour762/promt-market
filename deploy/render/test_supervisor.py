"""Process-level checks that do not need Docker, a database, or secrets."""
from pathlib import Path
import signal
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from supervisor import Service, Supervisor, prepare_environment


class OriginTests(unittest.TestCase):
    def test_derives_origin_and_csrf_allowlists_from_render(self):
        environ = {"RENDER_EXTERNAL_URL": "https://promt-market.onrender.com"}
        prepare_environment(environ)
        self.assertEqual(environ["PUBLIC_WEB_URL"], "https://promt-market.onrender.com")
        self.assertEqual(environ["ALLOWED_ORIGINS"], '["https://promt-market.onrender.com"]')
        self.assertEqual(environ["AUTH_ALLOWED_ORIGINS"], "https://promt-market.onrender.com")

    def test_preserves_explicit_custom_origin_and_allowlists(self):
        environ = {
            "RENDER_EXTERNAL_URL": "https://promt-market.onrender.com",
            "PUBLIC_WEB_URL": "https://shop.example/",
            "ALLOWED_ORIGINS": '["https://shop.example", "https://www.shop.example"]',
            "AUTH_ALLOWED_ORIGINS": "https://shop.example,https://www.shop.example",
        }
        original = environ.copy()
        prepare_environment(environ)
        self.assertEqual(environ, original)

    def test_invalid_or_missing_origins_fail_without_echoing_value(self):
        for value in (
            "", "http://shop.example", "https://shop.example/path", "https://shop.example?secret=x",
            "https://shop.example#fragment", "https://user:secret@shop.example", "https://bad host.example",
            "https://shop.example:invalid", "https://shop.example:", "https://shop.example\\evil",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "valid HTTPS origin") as error:
                    prepare_environment({"RENDER_EXTERNAL_URL": value})
                self.assertNotIn("secret", str(error.exception))

    def test_empty_allowlists_derive_from_custom_origin(self):
        environ = {"PUBLIC_WEB_URL": "https://shop.example/", "ALLOWED_ORIGINS": "", "AUTH_ALLOWED_ORIGINS": ""}
        prepare_environment(environ)
        self.assertEqual(environ["ALLOWED_ORIGINS"], '["https://shop.example"]')
        self.assertEqual(environ["AUTH_ALLOWED_ORIGINS"], "https://shop.example")



class SupervisorTests(unittest.TestCase):
    def service(self, name: str, script: str) -> Service:
        return Service(name, (sys.executable, "-c", script), Path.cwd())

    def assert_stopped(self, supervisor: Supervisor) -> None:
        self.assertTrue(all(process.poll() is not None for _, process in supervisor.children))

    def test_failed_migration_does_not_start_services(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "started"
            supervisor = Supervisor()
            result = supervisor.run(
                self.service("migrations", "raise SystemExit(2)"),
                (self.service("web", f"from pathlib import Path; Path({str(marker)!r}).touch()"),),
            )
            self.assertEqual(result, 1)
            self.assertFalse(marker.exists())
            self.assert_stopped(supervisor)

    def test_unexpected_clean_exit_stops_other_processes(self):
        supervisor = Supervisor()
        result = supervisor.run(
            self.service("migrations", "pass"),
            (
                self.service("API", "import time; time.sleep(60)"),
                self.service("mail worker", "pass"),
            ),
        )
        self.assertEqual(result, 1)
        self.assert_stopped(supervisor)

    def test_shutdown_during_migration_prevents_application_start(self):
        supervisor = Supervisor()
        timer = threading.Timer(0.3, supervisor.request_stop, args=(signal.SIGTERM,))
        timer.start()
        try:
            result = supervisor.run(self.service("migrations", "import time; time.sleep(60)"), ())
        finally:
            timer.cancel()
            timer.join()
        self.assertEqual(result, 128 + signal.SIGTERM)
        self.assert_stopped(supervisor)

    def test_process_start_failure_stops_started_siblings(self):
        supervisor = Supervisor()
        result = supervisor.run(
            self.service("migrations", "pass"),
            (
                self.service("API", "import time; time.sleep(60)"),
                Service("web", ("nonexistent-promt-market-test-command",), Path.cwd()),
            ),
        )
        self.assertEqual(result, 1)
        self.assert_stopped(supervisor)

    def test_shutdown_request_stops_all_running_services(self):
        supervisor = Supervisor()
        original_start = supervisor.start

        def start_and_stop_after_web(service):
            process = original_start(service)
            if service.name == "web":
                supervisor.request_stop(signal.SIGTERM)
            return process

        with patch.object(supervisor, "start", side_effect=start_and_stop_after_web):
            result = supervisor.run(
                self.service("migrations", "pass"),
                tuple(self.service(name, "import time; time.sleep(60)") for name in ("API", "mail worker", "web")),
            )
        self.assertEqual(result, 128 + signal.SIGTERM)
        self.assertEqual(len(supervisor.children), 3)
        self.assert_stopped(supervisor)

    @unittest.skipUnless(sys.platform != "win32", "POSIX process-group termination")
    def test_unresponsive_process_is_killed_after_grace_period(self):
        supervisor = Supervisor()
        timer = threading.Timer(0.4, supervisor.request_stop, args=(signal.SIGTERM,))
        timer.start()
        try:
            with patch("supervisor.SHUTDOWN_SECONDS", 0.1):
                result = supervisor.run(
                    self.service("migrations", "pass"),
                    (self.service("API", "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"),),
                )
        finally:
            timer.cancel()
            timer.join()
        self.assertEqual(result, 128 + signal.SIGTERM)
        self.assertEqual(supervisor.children[0][1].returncode, -signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
