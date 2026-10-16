"""Sandbox Sber acquiring preparation; no live gateway."""
from alembic import op
import sqlalchemy as sa
revision="0007_payment_preparation"
down_revision="0006_orders"
branch_labels=None
depends_on=None
def upgrade():
    op.drop_constraint("ck_order_status","orders",type_="check")
    op.create_check_constraint("ck_order_status","orders","status IN ('pending','test_granted','sandbox_paid')")
    op.create_table("payments",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("order_id",sa.Uuid(),sa.ForeignKey("orders.id"),nullable=False,unique=True),sa.Column("bank_order_id",sa.String(36),unique=True,nullable=True),sa.Column("form_url",sa.Text(),nullable=True),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    raise RuntimeError("Payment history must be preserved; use a forward migration")
