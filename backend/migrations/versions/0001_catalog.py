"""Create public catalog and separate protected versions."""
from alembic import op
import sqlalchemy as sa
revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("categories", sa.Column("id",sa.Integer(),primary_key=True),sa.Column("slug",sa.String(80),nullable=False,unique=True),sa.Column("name",sa.String(120),nullable=False))
    op.create_table("prompts",sa.Column("id",sa.String(80),primary_key=True),sa.Column("category_id",sa.Integer(),sa.ForeignKey("categories.id"),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("symbol",sa.String(20),nullable=False),sa.Column("result",sa.Text(),nullable=False),sa.Column("price_minor",sa.Integer(),nullable=True),sa.Column("currency",sa.String(3),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.CheckConstraint("price_minor IS NULL OR price_minor >= 0",name="ck_prompt_price"),sa.CheckConstraint("status IN ('draft','published','archived')",name="ck_prompt_status"))
    op.create_index("ix_prompts_category_id","prompts",["category_id"])
    op.create_index("ix_prompts_status","prompts",["status"])
    op.create_table("prompt_versions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("prompt_id",sa.String(80),sa.ForeignKey("prompts.id"),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("content",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.UniqueConstraint("prompt_id","version",name="uq_prompt_version"),sa.CheckConstraint("version > 0",name="ck_prompt_version_positive"))
    op.create_index("ix_prompt_versions_prompt_id","prompt_versions",["prompt_id"])

def downgrade():
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
    op.drop_table("categories")
