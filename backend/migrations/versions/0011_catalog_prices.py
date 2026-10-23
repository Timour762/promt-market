"""Set the current catalog price to 500 RUB without repricing existing orders."""
from alembic import op
import sqlalchemy as sa

revision = "0011_catalog_prices"
down_revision = "0010_platega_payments"
branch_labels = None
depends_on = None


def upgrade():
    # A revision change invalidates an administrator's stale catalog edit.
    # Order prices and version content are independent historical snapshots.
    op.execute(sa.text("""
        UPDATE prompts
        SET price_minor = 50000, currency = 'RUB', revision = revision + 1
        WHERE price_minor IS DISTINCT FROM 50000
           OR currency IS DISTINCT FROM 'RUB'
    """))


def downgrade():
    raise RuntimeError("Previous catalog prices are unknown; use a forward migration")
