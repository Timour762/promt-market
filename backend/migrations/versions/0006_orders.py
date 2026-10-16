"""Local orders and explicitly educational access; no payment records."""
from alembic import op
import sqlalchemy as sa
revision="0006_orders"
down_revision="0005_admin_catalog"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("orders",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id"),nullable=False),sa.Column("prompt_id",sa.String(80),sa.ForeignKey("prompts.id"),nullable=False),sa.Column("version_id",sa.Integer(),sa.ForeignKey("prompt_versions.id"),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("price_minor",sa.Integer(),nullable=False),sa.Column("currency",sa.String(3),nullable=False),sa.Column("status",sa.String(20),server_default="pending",nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.UniqueConstraint("user_id","prompt_id",name="uq_order_user_prompt"),sa.CheckConstraint("status IN ('pending','test_granted')",name="ck_order_status"),sa.CheckConstraint("price_minor >= 0",name="ck_order_price"))
    op.create_index("ix_orders_user_id","orders",["user_id"])
def downgrade():
    op.drop_table("orders")
