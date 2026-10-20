"""Encrypted merchant card settings; admin-only API."""
from alembic import op
import sqlalchemy as sa
revision="0008_payment_recipient"
down_revision="0007_payment_preparation"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("payment_recipient",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("recipient_name",sa.String(100),nullable=False),sa.Column("bank_name",sa.String(100),nullable=False),sa.Column("encrypted_card",sa.Text(),nullable=False),sa.Column("card_last4",sa.String(4),nullable=False),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.CheckConstraint("id = 1",name="ck_recipient_singleton"),sa.CheckConstraint("revision > 0",name="ck_recipient_revision"))
def downgrade():
    raise RuntimeError("Payment settings must be preserved; use a forward migration")
