"""Optional username and email for explicitly provisioned local accounts."""
from alembic import op
import sqlalchemy as sa
revision = "0004_username"
down_revision = "0003_recovery"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users",sa.Column("username",sa.String(80),nullable=True))
    op.create_unique_constraint("uq_users_username","users",["username"])
    op.alter_column("users","email",existing_type=sa.String(254),nullable=True)

def downgrade():
    # Will refuse if email-less accounts still exist; never delete their data.
    op.alter_column("users","email",existing_type=sa.String(254),nullable=False)
    op.drop_constraint("uq_users_username","users",type_="unique")
    op.drop_column("users","username")
