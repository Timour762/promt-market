"""Users, roles and opaque server sessions."""
from alembic import op
import sqlalchemy as sa
revision = "0002_auth"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None

def upgrade():
    roles = op.create_table("roles", sa.Column("id",sa.Integer(),primary_key=True),sa.Column("code",sa.String(30),nullable=False,unique=True))
    op.bulk_insert(roles,[{"code":"customer"},{"code":"admin"}])
    op.create_table("users",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("role_id",sa.Integer(),sa.ForeignKey("roles.id"),nullable=False),sa.Column("email",sa.String(254),nullable=False,unique=True),sa.Column("name",sa.String(80),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("email_verified_at",sa.DateTime(timezone=True),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.CheckConstraint("status IN ('active','blocked')",name="ck_user_status"))
    op.create_index("ix_users_role_id","users",["role_id"])
    op.create_table("sessions",sa.Column("token_hash",sa.String(64),primary_key=True),sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_sessions_user_id","sessions",["user_id"])
    op.create_index("ix_sessions_expires_at","sessions",["expires_at"])

def downgrade():
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("roles")
