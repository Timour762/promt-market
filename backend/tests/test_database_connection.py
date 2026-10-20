import ssl
import unittest
import warnings
from unittest.mock import patch

from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.pool import NullPool

from app.db.connection import create_database_engine, database_connection_options


class DatabaseConnectionTests(unittest.TestCase):
    def test_local_asyncpg_url_is_unchanged(self):
        raw = "postgresql+asyncpg://user:secret@localhost:5438/market"
        url, connect_args = database_connection_options(raw)
        self.assertEqual(url.render_as_string(hide_password=False), raw)
        self.assertEqual(connect_args, {})

    def test_console_url_uses_asyncpg_and_verified_tls(self):
        for mode in ["require", "verify-ca", "verify-full"]:
            with self.subTest(mode=mode), warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                url, connect_args = database_connection_options(
                    "postgresql://owner:p%40ss%2Fword@ep-preview.us-east-1.aws.neon.tech/neondb"
                    f"?sslmode={mode}&channel_binding=require"
                )
                self.assertEqual(url.drivername, "postgresql+asyncpg")
                self.assertEqual(url.password, "p@ss/word")
                self.assertEqual(url.query, {})
                tls = connect_args["ssl"]
                self.assertIsInstance(tls, ssl.SSLContext)
                self.assertEqual(tls.verify_mode, ssl.CERT_REQUIRED)
                self.assertTrue(tls.check_hostname)
                self.assertEqual(len(captured), 1)
                self.assertIn("does not enforce channel_binding", str(captured[0].message))
                self.assertNotIn("p@ss", str(captured[0].message))
                _, driver_args = PGDialect_asyncpg().create_connect_args(url)
                self.assertEqual(driver_args["host"], "ep-preview.us-east-1.aws.neon.tech")
                self.assertNotIn("sslmode", driver_args)
                self.assertNotIn("channel_binding", driver_args)

    def test_neon_requires_verified_tls_even_when_mode_is_omitted(self):
        url, args = database_connection_options("postgres://owner:secret@ep-preview.neon.tech/neondb")
        self.assertEqual(url.drivername, "postgresql+asyncpg")
        self.assertTrue(args["ssl"].check_hostname)
        self.assertEqual(args["ssl"].verify_mode, ssl.CERT_REQUIRED)

    def test_disable_binding_is_removed_without_a_warning(self):
        with warnings.catch_warnings(record=True) as captured:
            url, _ = database_connection_options(
                "postgresql://owner:secret@ep-preview.neon.tech/neondb?channel_binding=disable"
            )
        self.assertEqual(url.query, {})
        self.assertEqual(captured, [])

    def test_non_neon_explicit_local_ssl_modes_are_translated(self):
        for mode in ["disable", "allow", "prefer"]:
            url, args = database_connection_options(
                f"postgresql+asyncpg://user:secret@localhost/db?sslmode={mode}"
            )
            self.assertEqual(url.query, {})
            self.assertEqual(args, {"ssl": mode})

    def test_invalid_or_weakening_options_fail_without_exposing_credentials(self):
        invalid_urls = [
            "not-a-url:secret-do-not-print",
            "sqlite://owner:secret-do-not-print@localhost/db",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=disable",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=prefer",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=allow",
            "postgresql://owner:secret-do-not-print@localhost/db?channel_binding=require",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=bad-secret-do-not-print",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?channel_binding=bad-secret-do-not-print",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=require&sslmode=disable",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?channel_binding=require&channel_binding=disable",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslmode=require&ssl=disable",
            "postgresql://owner:secret-do-not-print@ep-preview.neon.tech/db?sslrootcert=secret-do-not-print",
        ]
        for raw in invalid_urls:
            with self.subTest(raw=raw), self.assertRaises(ValueError) as raised:
                database_connection_options(raw)
            self.assertNotIn("secret-do-not-print", str(raised.exception))
            self.assertNotIn("postgresql://", str(raised.exception))

    def test_engine_preserves_pool_and_server_settings(self):
        with patch("app.db.connection.create_async_engine") as create:
            create_database_engine(
                "postgresql://owner:secret@ep-preview.neon.tech/neondb?sslmode=require",
                poolclass=NullPool,
                connect_args={"server_settings": {"search_path": "fixture"}},
            )
        options = create.call_args.kwargs
        self.assertIs(options["poolclass"], NullPool)
        self.assertEqual(options["connect_args"]["server_settings"], {"search_path": "fixture"})
        self.assertTrue(options["connect_args"]["ssl"].check_hostname)

    def test_engine_rejects_override_of_verified_tls(self):
        with self.assertRaises(ValueError):
            create_database_engine(
                "postgresql://owner:secret@ep-preview.neon.tech/neondb?sslmode=require",
                connect_args={"ssl": False},
            )


if __name__ == "__main__":
    unittest.main()
