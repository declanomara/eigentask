from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TaskSessionStatus(str, Enum):
    """Task session status."""

    INCOMPLETE = "INCOMPLETE"
    COMPLETED = "COMPLETED"


class TaskSession(Base):
    """Scheduled work block for a task; can be completed independently of the task."""

    __tablename__ = "task_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskSessionStatus] = mapped_column(
        SQLEnum(TaskSessionStatus, name="task_session_status"),
        nullable=False,
        default=TaskSessionStatus.INCOMPLETE,
        server_default=TaskSessionStatus.INCOMPLETE.value,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    task: Mapped["Task"] = relationship("Task", back_populates="sessions")
