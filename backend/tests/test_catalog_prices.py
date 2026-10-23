"""Exercise catalog repricing and first-boot seeding in disposable local schemas."""
import importlib.util
import json
from pathlib import Path
import secrets
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.models import Role, User
from app.catalog.models import Category, Prompt, PromptVersion
from app.core.config import get_settings
from app.orders.models import Order


BACKEND = Path(__file__).resolve().parents[1]


def migration(path):
    spec = importlib.util.spec_from_file_location("catalog_test_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalogPriceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = get_settings().database_url
        if make_url(url).host not in ("localhost", "127.0.0.1", "::1"):
            self.skipTest("Catalog migration tests require a local PostgreSQL database")
        self.schema = "pm_price_test_" + secrets.token_hex(8)
        self.control = create_async_engine(url, poolclass=NullPool)
        async with self.control.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.engine = create_async_engine(
            url, poolclass=NullPool,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        self.addAsyncCleanup(self.drop_schema)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.price_migration = migration(BACKEND / "migrations/versions/0011_catalog_prices.py")
        # Use the actual migration chain, including role bootstrap and constraints.
        for path in sorted((BACKEND / "migrations/versions").glob("*.py")):
            if path.name < "0011_":
                await self.apply_migration(migration(path))

    async def drop_schema(self):
        await self.engine.dispose()
        async with self.control.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.control.dispose()

    async def apply_migration(self, module):
        def run(connection):
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade()
        async with self.engine.begin() as connection:
            await connection.run_sync(run)

    async def test_reprices_only_catalog_and_changed_revisions(self):
        async with self.factory() as database:
            category = Category(slug="fixture", name="Fixture")
            database.add(category)
            await database.flush()
            for prompt_id, price, currency, revision, status in (
                ("unchanged", 50000, "RUB", 7, "published"),
                ("unpriced", None, "RUB", 2, "published"),
                ("foreign", 59900, "USD", 3, "archived"),
                ("free", 0, "RUB", 4, "draft"),
            ):
                database.add(Prompt(
                    id=prompt_id, category_id=category.id, title=prompt_id,
                    description="Public description", result="Public result", symbol="X",
                    price_minor=price, currency=currency, revision=revision, status=status,
                ))
            await database.flush()
            version = PromptVersion(prompt_id="unpriced", version=1, content="PRIVATE_FIXTURE_CONTENT")
            role_id = await database.scalar(select(Role.id).where(Role.code == "customer"))
            user = User(name="Fixture", username="fixture", password_hash="not-a-login-hash", role_id=role_id)
            database.add_all([version, user])
            await database.flush()
            order = Order(
                user_id=user.id, prompt_id="unpriced", version_id=version.id,
                title="Historical title", price_minor=29900, currency="USD", status="paid",
            )
            database.add(order)
            await database.commit()
            history = (await database.execute(select(Order.__table__))).all()
            content = (await database.execute(select(PromptVersion.__table__))).all()

        # Also prove that accidentally re-executing this UPDATE does not bump revisions.
        await self.apply_migration(self.price_migration)
        await self.apply_migration(self.price_migration)
        async with self.factory() as database:
            prompts = {prompt.id: prompt for prompt in await database.scalars(select(Prompt))}
            self.assertEqual({p.price_minor for p in prompts.values()}, {50000})
            self.assertEqual({p.currency for p in prompts.values()}, {"RUB"})
            self.assertEqual({key: p.revision for key, p in prompts.items()}, {
                "unchanged": 7, "unpriced": 3, "foreign": 4, "free": 5,
            })
            self.assertEqual(prompts["foreign"].status, "archived")
            self.assertEqual(prompts["free"].status, "draft")
            self.assertEqual((await database.execute(select(Order.__table__))).all(), history)
            self.assertEqual((await database.execute(select(PromptVersion.__table__))).all(), content)

    async def test_empty_database_seed_has_six_prices_and_preserves_edits(self):
        from app import seed as seed_module

        await self.apply_migration(self.price_migration)
        with patch.object(seed_module, "SessionFactory", self.factory), patch.object(seed_module, "engine", self.engine):
            await seed_module.seed(None)
            async with self.factory() as database:
                prompts = list(await database.scalars(select(Prompt)))
                self.assertEqual(len(prompts), 6)
                self.assertTrue(all(p.price_minor == 50000 and p.currency == "RUB" for p in prompts))
                self.assertTrue(all(p.status == "published" and p.revision == 1 for p in prompts))
                prompts[0].title = "Edited public title"
                edited_id = prompts[0].id
                await database.commit()
            await seed_module.seed(None)
        async with self.factory() as database:
            self.assertEqual(await database.scalar(select(func.count()).select_from(Prompt)), 6)
            self.assertEqual(await database.scalar(select(func.count()).select_from(Category)), 6)
            self.assertEqual((await database.get(Prompt, edited_id)).title, "Edited public title")
            self.assertEqual(await database.scalar(select(func.count()).select_from(User)), 0)
            self.assertEqual(await database.scalar(select(func.count()).select_from(PromptVersion)), 0)
            self.assertEqual(await database.scalar(select(func.count()).select_from(Order)), 0)


class CatalogSnapshotTests(unittest.TestCase):
    def test_seed_and_preview_prices_agree(self):
        seed_catalog = json.loads((BACKEND / "app/catalog/data.json").read_text(encoding="utf-8-sig"))
        preview_catalog = json.loads((BACKEND.parent / "frontend/src/lib/preview-catalog.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(len(seed_catalog), 6)
        self.assertEqual(len(preview_catalog), 6)
        self.assertEqual({p["id"] for p in seed_catalog}, {p["id"] for p in preview_catalog})
        for product in seed_catalog + preview_catalog:
            self.assertEqual((product["price_minor"], product["currency"]), (50000, "RUB"))
