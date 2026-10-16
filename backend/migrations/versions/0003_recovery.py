"""One-use account tokens and encrypted local email outbox."""
from alembic import op
import sqlalchemy as sa
revision = "0003_recovery"
down_revision = "0002_auth"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("auth_tokens",sa.Column("token_hash",sa.String(64),primary_key=True),sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("purpose",sa.String(30),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.CheckConstraint("purpose IN ('verify_email','reset_password')",name="ck_auth_token_purpose"))
    op.create_index("ix_auth_tokens_user_id","auth_tokens",["user_id"])
    op.create_index("ix_auth_tokens_expires_at","auth_tokens",["expires_at"])
    op.create_table("email_outbox",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("encrypted_payload",sa.Text(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("delivered_at",sa.DateTime(timezone=True),nullable=True),sa.Column("attempts",sa.Integer(),nullable=False),sa.Column("last_error",sa.String(60),nullable=True))

def downgrade():
    op.drop_table("email_outbox")
    op.drop_table("auth_tokens")
