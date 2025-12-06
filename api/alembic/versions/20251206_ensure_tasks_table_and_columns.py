"""Ensure tasks table and required columns exist

Revision ID: 20251206_tasks_baseline
Revises: ae807134c28e
Create Date: 2025-12-06 00:00:00.000000
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251206_tasks_baseline"
down_revision: str | Sequence[str] | None = "ae807134c28e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


task_status_enum = sa.Enum("BACKLOG", "PLANNED", "COMPLETED", "REMOVED", name="task_status")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    task_status_enum.create(bind, checkfirst=True)

    table_exists = "tasks" in inspector.get_table_names()
    if not table_exists:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", task_status_enum, nullable=False, server_default="BACKLOG"),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("planned_duration", sa.Integer(), nullable=True),
            sa.Column("created_by_sub", sa.String(length=255), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_tasks_created_by_sub"), "tasks", ["created_by_sub"], unique=False)
        op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
        return

    existing_columns = {col["name"] for col in inspector.get_columns("tasks")}

    if "status" not in existing_columns:
        op.add_column("tasks", sa.Column("status", task_status_enum, nullable=False, server_default="BACKLOG"))
    if "due_at" not in existing_columns:
        op.add_column("tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    if "planned_start_at" not in existing_columns:
        op.add_column("tasks", sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True))
    if "planned_end_at" not in existing_columns:
        op.add_column("tasks", sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True))
    if "planned_duration" not in existing_columns:
        op.add_column("tasks", sa.Column("planned_duration", sa.Integer(), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("tasks")}
    if op.f("ix_tasks_created_by_sub") not in existing_indexes and "created_by_sub" in existing_columns:
        op.create_index(op.f("ix_tasks_created_by_sub"), "tasks", ["created_by_sub"], unique=False)
    if op.f("ix_tasks_status") not in existing_indexes and "status" in existing_columns:
        op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)


def downgrade() -> None:
    # Intentionally left as a no-op to avoid destructive drops.
    pass

