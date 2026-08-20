"""Initial users and tickets schema."""

from alembic import op
import sqlalchemy as sa

revision = "20260820_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("complaint", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(), nullable=False),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("category_confidence", sa.Float(), nullable=True),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("priority_confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(20), nullable=True),
        sa.Column("classified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tickets_user_id", "tickets", ["user_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_department", "tickets", ["department"])


def downgrade():
    op.drop_index("ix_tickets_department", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_user_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
