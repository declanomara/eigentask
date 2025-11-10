from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TaskStatus(str, Enum):
    """Task status."""

    BACKLOG = "BACKLOG"
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    REMOVED = "REMOVED"


class Task(Base):
    """Application task owned by a user identified by OIDC subject (sub)."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.BACKLOG,
        server_default=TaskStatus.BACKLOG.value,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Owner's OIDC subject claim
    created_by_sub: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
