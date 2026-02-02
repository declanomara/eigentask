from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.task_session import TaskSession


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

    # Task Planning
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Owner's OIDC subject claim
    created_by_sub: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    sessions: Mapped[list[TaskSession]] = relationship(
        "TaskSession",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
