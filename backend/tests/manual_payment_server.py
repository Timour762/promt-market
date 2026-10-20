"""Browser-test API: disposable PostgreSQL schema, fictional cards and test sessions."""
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import secrets
import sys
from cryptography.fernet import Fernet
import uvicorn

os.environ.update(APP_ENV="test", COOKIE_SECURE="false", MAIL_DELIVERY="local",
                  PUBLIC_WEB_URL="http://127.0.0.1:3117",
                  ALLOWED_ORIGINS='["http://127.0.0.1:3117"]',
                  PAYMENT_DETAILS_ENCRYPTION_KEY=Fernet.generate_key().decode(),
                  PLATEGA_ENABLED="true", PLATEGA_MERCHANT_ID="11111111-1111-4111-8111-111111111111",
                  PLATEGA_SECRET="browser-fixture-platega-secret")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.main import app
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.auth.models import Role, Session, User
from app.auth.security import password_hasher, token_hash
from app.catalog.models import Category, Prompt, PromptVersion
from app.payments.recipient import PaymentRecipient
from app.orders.models import Order
from app.payments.manual_models import ManualPayment
from app.payments import platega, platega_router
from fastapi import HTTPException
from uuid import uuid4

fixture_transactions = {}


async def fixture_provider(method, path, data=None):
    if method == "POST" and path == "/transaction/process":
        transaction_id = str(uuid4())
        fixture_transactions[transaction_id] = {"id": transaction_id,
            "mechantId": str(get_settings().platega_merchant_id), "status": "PENDING",
            "paymentDetails": data["paymentDetails"], "payload": data["payload"],
            "amountUsdt": "5.5", "comissionUsdt": "0.2", "return": data["return"]}
        return {"transactionId": transaction_id, "merchantId": str(get_settings().platega_merchant_id),
                "redirect": "https://pay.platega.io/?id=" + transaction_id, "status": "PENDING"}
    transaction = fixture_transactions.get(path.rsplit("/", 1)[-1])
    if transaction is None:
        raise HTTPException(404, "Fixture transaction not found")
    return transaction


platega.call = fixture_provider
platega_router.call = fixture_provider

schema_file = Path(__file__).resolve().parents[2] / ".local" / "manual-e2e-schema.txt"


async def cleanup():
    if not schema_file.exists():
        return
    schema = schema_file.read_text().strip()
    if not re.fullmatch(r"pm_manual_e2e_[0-9a-f]{16}", schema):
        raise RuntimeError("Unexpected test schema identifier")
    control = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with control.begin() as db:
        await db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    await control.dispose()
    schema_file.unlink()


@asynccontextmanager
async def lifespan(application):
    schema = "pm_manual_e2e_" + secrets.token_hex(8)
    control = create_async_engine(get_settings().database_url, poolclass=NullPool)
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool,
                                connect_args={"server_settings": {"search_path": schema}})
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with control.begin() as db:
        await db.execute(text(f'CREATE SCHEMA "{schema}"'))
    schema_file.parent.mkdir(exist_ok=True)
    schema_file.write_text(schema)
    try:
        async with engine.begin() as db:
            await db.run_sync(Base.metadata.create_all)
        async with factory() as db:
            customer, admin = Role(code="customer"), Role(code="admin")
            db.add_all([customer, admin]); await db.flush()
            fixture_users = {}
            for name, role in [("desktop", customer), ("mobile", customer), ("admin", admin)]:
                user = User(name="Fixture " + name, username="fixture" + name, role_id=role.id,
                            password_hash=password_hasher.hash(secrets.token_urlsafe(24)), status="active")
                db.add(user); await db.flush()
                fixture_users[name] = user
                db.add(Session(user_id=user.id, token_hash=token_hash("manual-e2e-" + name),
                               expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
            category = Category(slug="fixture", name="Fixture category")
            db.add(category); await db.flush()
            db.add(Prompt(id="fixture-prompt", category_id=category.id, title="Fixture payment prompt",
                          description="Browser payment fixture", result="Fixture result", symbol="F",
                          price_minor=50000, currency="RUB", status="published"))
            await db.flush()
            version = PromptVersion(prompt_id="fixture-prompt", version=1, content="PRIVATE_BROWSER_FIXTURE_CONTENT")
            db.add(version)
            await db.flush()
            key = get_settings().payment_details_encryption_key.get_secret_value().encode()
            db.add(PaymentRecipient(id=1, recipient_name="Fixture Recipient", bank_name="Fixture Bank",
                                    encrypted_card=Fernet(key).encrypt(b"4242424242424242").decode(),
                                    card_last4="4242", revision=1))
            # Desktop covers the old administrator-waiting order from the screenshot;
            # mobile covers a newly created unpaid order.
            old_order = Order(user_id=fixture_users['desktop'].id, prompt_id='fixture-prompt', version_id=version.id,
                              title='Fixture payment prompt', price_minor=50000, currency='RUB', status='awaiting_confirmation')
            db.add(old_order)
            await db.flush()
            db.add(ManualPayment(order_id=old_order.id, recipient_name='Fixture Recipient', bank_name='Fixture Bank',
                                 encrypted_card=Fernet(key).encrypt(b'4242424242424242').decode(), card_last4='4242', recipient_revision=1))
            await db.commit()

        async def database():
            async with factory() as db:
                yield db
        application.dependency_overrides[get_session] = database
        yield
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()
        async with control.begin() as db:
            await db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await control.dispose()
        schema_file.unlink(missing_ok=True)


app.router.lifespan_context = lifespan


@app.get("/__test_ready")
async def ready():
    return {"status": "ready"}


@app.post("/__test_confirm/{transaction_id}")
async def confirm_fixture(transaction_id: str):
    if transaction_id not in fixture_transactions:
        raise HTTPException(404, "Fixture transaction not found")
    fixture_transactions[transaction_id]["status"] = "CONFIRMED"
    return {"return": fixture_transactions[transaction_id]["return"]}


@app.post("/__test_shutdown")
async def shutdown_fixture():
    import signal
    asyncio.get_running_loop().call_later(.2, os.kill, os.getpid(), signal.SIGINT)
    return {"status": "stopping"}


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        asyncio.run(cleanup())
    else:
        uvicorn.run(app, host="127.0.0.1", port=8117)
