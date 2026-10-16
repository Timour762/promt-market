"""Catalog revisions and safe audit metadata."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0005_admin_catalog"
down_revision = "0004_username"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("prompts",sa.Column("revision",sa.Integer(),server_default="1",nullable=False))
    op.create_check_constraint("ck_prompt_revision","prompts","revision > 0")
    op.create_table("audit_logs",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("actor_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="SET NULL"),nullable=True),sa.Column("action",sa.String(60),nullable=False),sa.Column("entity_id",sa.String(80),nullable=False),sa.Column("details",postgresql.JSONB(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_audit_logs_actor_id","audit_logs",["actor_id"])
    op.create_index("ix_audit_logs_created_at","audit_logs",["created_at"])

def downgrade():
    op.drop_table("audit_logs")
    op.drop_constraint("ck_prompt_revision","prompts",type_="check")
    op.drop_column("prompts","revision")
