"""test: autogenerate

Revision ID: 1cf81a1539c0
Revises: 
Create Date: 2025-11-10 21:52:12.838866

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1cf81a1539c0"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tasks table if it does not exist (baseline)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tasks" in inspector.get_table_names():
        return

    op.create_table(
        "tasks",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("created_by_sub", sa.VARCHAR(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("tasks_pkey")),
    )
    op.create_index(op.f("ix_tasks_created_by_sub"), "tasks", ["created_by_sub"], unique=False)


def downgrade() -> None:
    """No-op downgrade to avoid destructive drops."""
    pass
