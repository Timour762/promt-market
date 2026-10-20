from app.payments.recipient import PaymentRecipient
from app.payments.manual_models import ManualPayment
from app.payments.platega_models import PlategaPayment
from app.payments.models import Payment
from app.orders.models import Order
import asyncio
from alembic import context
from sqlalchemy import pool
from app.core.config import get_settings
from app.db.base import Base
from app.db.connection import create_database_engine, database_connection_options
from app.catalog import models
from app.auth import models as auth_models
from app.auth import recovery_models
from app.admin import models as admin_models

config = context.config
target_metadata = Base.metadata

def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def online():
    engine = create_database_engine(get_settings().database_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()

if context.is_offline_mode():
    url, _ = database_connection_options(get_settings().database_url)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
