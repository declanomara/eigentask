"""Add task_sessions table and migrate existing planned tasks to one session each

Revision ID: 20260201_task_sessions
Revises: 20251206_tasks_baseline
Create Date: 2026-02-01 00:00:00.000000

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260201_task_sessions"
down_revision: str | Sequence[str] | None = "20251206_tasks_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


task_session_status_enum = postgresql.ENUM(
    "INCOMPLETE",
    "COMPLETED",
    name="task_session_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    task_session_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "task_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            task_session_status_enum,
            nullable=False,
            server_default="INCOMPLETE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_task_sessions_task_id"), "task_sessions", ["task_id"], unique=False)
    op.create_index("ix_task_sessions_status", "task_sessions", ["status"], unique=False)

    # Data migration: for each task that has planned_start_at (and planned_end_at or planned_duration), insert one session
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        conn.execute(
            sa.text("""
                INSERT INTO task_sessions (task_id, scheduled_start_at, scheduled_end_at, status, created_at, updated_at)
                SELECT id,
                       planned_start_at,
                       COALESCE(planned_end_at, datetime(planned_start_at, '+' || COALESCE(planned_duration, 60) || ' minutes')),
                       'INCOMPLETE',
                       datetime('now'),
                       datetime('now')
                FROM tasks
                WHERE planned_start_at IS NOT NULL
                  AND (planned_end_at IS NOT NULL OR planned_duration IS NOT NULL)
            """)
        )
    else:
        # PostgreSQL: add minutes via interval
        conn.execute(
            sa.text("""
                INSERT INTO task_sessions (task_id, scheduled_start_at, scheduled_end_at, status, created_at, updated_at)
                SELECT id,
                       planned_start_at,
                       COALESCE(planned_end_at, planned_start_at + (COALESCE(planned_duration, 60) || ' minutes')::interval),
                       'INCOMPLETE',
                       now(),
                       now()
                FROM tasks
                WHERE planned_start_at IS NOT NULL
                  AND (planned_end_at IS NOT NULL OR planned_duration IS NOT NULL)
            """)
        )


def downgrade() -> None:
    op.drop_index("ix_task_sessions_status", table_name="task_sessions")
    op.drop_index(op.f("ix_task_sessions_task_id"), table_name="task_sessions")
    op.drop_table("task_sessions")
    task_session_status_enum.drop(op.get_bind(), checkfirst=True)
