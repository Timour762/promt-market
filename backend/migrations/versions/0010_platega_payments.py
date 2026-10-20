"""Platega checkout attempts and verified payment status."""
from alembic import op
import sqlalchemy as sa

revision = "0010_platega_payments"
down_revision = "0009_manual_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platega_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), unique=True, nullable=True),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount_usdt", sa.Numeric(24, 8), nullable=True),
        sa.Column("commission_usdt", sa.Numeric(24, 8), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_platega_payments_order_id", "platega_payments", ["order_id"])


def downgrade():
    raise RuntimeError("Payment history must be preserved; use a forward migration")
