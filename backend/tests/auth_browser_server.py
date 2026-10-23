"""Loopback-only registration fixture; no real mail or persistent account data."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import re
import secrets
import sys

from cryptography.fernet import Fernet
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import NullPool
import uvicorn

# These are fresh/test-only settings, never deployment secrets or Google mail.
os.environ.update(
    APP_ENV="test", COOKIE_SECURE="false", MAIL_DELIVERY="local",
    PUBLIC_WEB_URL="http://127.0.0.1:3137",
    ALLOWED_ORIGINS='["http://127.0.0.1:3137"]',
    AUTH_PROXY_SECRET="auth-browser-fixture-secret-at-least-32-characters",
    CSRF_SECRET=secrets.token_urlsafe(48),
    MAIL_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    PLATEGA_ENABLED="false", SBER_SANDBOX_ENABLED="false",
    SBER_WEBHOOK_ENABLED="false", LOCAL_TEST_ACCESS_ENABLED="false",
)

from app.main import app
from app.core.config import get_settings
from app.db.base import Base
from app.db.connection import create_database_engine
from app.db.session import get_session
from app.auth import recovery_router, router
from app.auth.models import Role, Session, User
from app.auth.recovery_models import AuthToken, EmailOutbox

schema_file = Path(__file__).resolve().parents[2] / ".local" / "auth-e2e-schema.txt"
database_url = get_settings().database_url
if make_url(database_url).host not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Auth browser tests require a loopback PostgreSQL database")

delivery_calls = 0
fixture_factory = None
server = None


async def fake_delivery():
    """Keep the encrypted outbox for assertions; never invoke a mail provider."""
    global delivery_calls
    delivery_calls += 1


router.deliver_local_mail = fake_delivery
recovery_router.deliver_local_mail = fake_delivery


async def cleanup():
    if not schema_file.exists():
        return
    schema = schema_file.read_text().strip()
    if not re.fullmatch(r"pm_auth_e2e_[0-9a-f]{16}", schema):
        raise RuntimeError("Unexpected auth test schema identifier")
    control = create_database_engine(database_url, poolclass=NullPool)
    try:
        async with control.begin() as db:
            await db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        schema_file.unlink(missing_ok=True)
    finally:
        await control.dispose()


@asynccontextmanager
async def lifespan(application):
    global fixture_factory
    # Clean up an interrupted previous test run before creating a new schema.
    await cleanup()
    schema = "pm_auth_e2e_" + secrets.token_hex(8)
    control = create_database_engine(database_url, poolclass=NullPool)
    engine = create_database_engine(database_url, poolclass=NullPool,
        connect_args={"server_settings": {"search_path": schema}})
    fixture_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with control.begin() as db:
            await db.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_file.parent.mkdir(exist_ok=True)
        schema_file.write_text(schema)
        async with engine.begin() as db:
            await db.run_sync(Base.metadata.create_all)
        async with fixture_factory() as db:
            db.add_all([Role(code="customer"), Role(code="admin")])
            await db.commit()

        async def database():
            async with fixture_factory() as db:
                yield db

        application.dependency_overrides[get_session] = database
        yield
    finally:
        application.dependency_overrides.clear()
        fixture_factory = None
        await engine.dispose()
        await control.dispose()
        await cleanup()


app.router.lifespan_context = lifespan


@app.get("/__auth_test_ready")
async def ready():
    return {"status": "ready", "mail": "mocked"}


@app.get("/__auth_test_state")
async def state(email: str):
    async with fixture_factory() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            return {"exists": False}
        role = await db.get(Role, user.role_id)
        jobs = (await db.scalars(select(EmailOutbox))).all()
        return {
            "exists": True,
            "role": role.code,
            "password_hashed": user.password_hash.startswith("$argon2id$"),
            "sessions": await db.scalar(select(func.count()).select_from(Session).where(Session.user_id == user.id)),
            "verification_tokens": await db.scalar(select(func.count()).select_from(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "verify_email")),
            "queued_messages": len(jobs),
            "outbox_encrypted": all(job.encrypted_payload and not job.encrypted_payload.startswith("{") for job in jobs),
            "delivered_messages": sum(job.delivered_at is not None for job in jobs),
            "delivery_calls": delivery_calls,
        }


@app.post("/__auth_test_shutdown")
async def shutdown():
    # A Windows SIGINT via os.kill terminates the process before lifespan cleanup.
    # Let Uvicorn drain the request and close the disposable schema on all OSes.
    server.should_exit = True
    return {"status": "stopping"}


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        asyncio.run(cleanup())
    else:
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8137, access_log=False))
        server.run()
