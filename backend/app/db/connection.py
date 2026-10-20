"""Build asyncpg engines from local or Neon PostgreSQL connection URLs.

Neon's console uses libpq's ``sslmode`` and ``channel_binding`` options.
SQLAlchemy forwards query parameters as asyncpg keyword arguments, so those
options need translating rather than passing through to the driver.
"""

import ssl
import warnings
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def database_connection_options(database_url: str | URL) -> tuple[URL, dict[str, Any]]:
    """Return an asyncpg URL and connection arguments without exposing secrets.

    TLS requests use the system CA store and hostname verification, including
    when the supplied libpq mode only says ``require``. The original DNS host
    stays in the URL so asyncpg can send SNI and verify the Neon certificate.
    asyncpg cannot enforce libpq's channel-binding requirement: an explicit
    warning documents that limitation, and binding requests are accepted only
    alongside verified TLS.
    """
    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError):
        raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
    if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        raise ValueError("DATABASE_URL must use PostgreSQL with asyncpg")
    url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)

    def take_option(name: str) -> str | None:
        value = query.pop(name, None)
        if isinstance(value, tuple):
            raise ValueError("DATABASE_URL has a duplicate connection option")
        return value

    sslmode = take_option("sslmode")
    channel_binding = take_option("channel_binding")
    if sslmode is not None and sslmode not in {
        "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
    }:
        raise ValueError("DATABASE_URL has an unsupported sslmode")
    if channel_binding is not None and channel_binding not in {"disable", "prefer", "require"}:
        raise ValueError("DATABASE_URL has an unsupported channel_binding mode")

    is_neon = bool(url.host and url.host.lower().endswith(".neon.tech"))
    if is_neon and sslmode in {"disable", "allow", "prefer"}:
        raise ValueError("Neon connections require verified TLS")
    verified_tls = is_neon or sslmode in {"require", "verify-ca", "verify-full"}
    if (sslmode is not None or verified_tls) and "ssl" in query:
        raise ValueError("DATABASE_URL has conflicting TLS options")
    if verified_tls and any(name in query for name in {
        "sslcert", "sslkey", "sslrootcert", "sslcrl", "sslpassword",
        "ssl_min_protocol_version", "ssl_max_protocol_version", "sslsni",
    }):
        raise ValueError("DATABASE_URL contains unsupported custom TLS options")

    connect_args: dict[str, Any] = {}
    if verified_tls:
        connect_args["ssl"] = ssl.create_default_context()
    elif sslmode is not None:
        connect_args["ssl"] = sslmode
    if channel_binding in {"require", "prefer"}:
        if not verified_tls:
            raise ValueError("Channel-binding options require verified TLS with asyncpg")
        warnings.warn(
            "asyncpg does not enforce channel_binding; the database connection "
            "uses certificate and hostname verified TLS instead",
            RuntimeWarning,
            stacklevel=2,
        )
    return url.set(query=query), connect_args


def create_database_engine(database_url: str | URL, **options: Any) -> AsyncEngine:
    """Apply the same connection policy to the application and migrations."""
    url, connect_args = database_connection_options(database_url)
    supplied_args = dict(options.pop("connect_args", {}))
    if "ssl" in connect_args and "ssl" in supplied_args:
        raise ValueError("Database engine TLS options must not override DATABASE_URL")
    return create_async_engine(url, connect_args={**supplied_args, **connect_args}, **options)
