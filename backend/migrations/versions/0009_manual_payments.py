"""Manual transfers and administrator confirmation."""
from alembic import op
import sqlalchemy as sa

revision = "0009_manual_payments"
down_revision = "0008_payment_recipient"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_order_status", "orders", type_="check")
    op.alter_column("orders", "status", existing_type=sa.String(20), type_=sa.String(32), existing_nullable=False)
    op.create_check_constraint("ck_order_status", "orders", "status IN ('pending','awaiting_confirmation','paid','test_granted','sandbox_paid')")
    op.create_table(
        "manual_payments",
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id"), primary_key=True),
        sa.Column("recipient_name", sa.String(100), nullable=False),
        sa.Column("bank_name", sa.String(100), nullable=False),
        sa.Column("encrypted_card", sa.Text(), nullable=False),
        sa.Column("card_last4", sa.String(4), nullable=False),
        sa.Column("recipient_revision", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_manual_payments_requested_at", "manual_payments", ["requested_at"])


def downgrade():
    raise RuntimeError("Payment history must be preserved; use a forward migration")
