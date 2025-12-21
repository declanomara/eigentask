from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


def _coerce_planned_duration(
    planned_start_at: datetime | None,
    planned_end_at: datetime | None,
    planned_duration: int | None,
) -> int | None:
    """Ensure duration aligns with start/end if both are present."""
    if planned_start_at and planned_end_at:
        minutes = int((planned_end_at - planned_start_at) / timedelta(minutes=1))
        if planned_duration is None:
            return minutes
        if planned_duration != minutes:
            message = (
                "planned_duration must equal the difference between planned_start_at and planned_end_at"
            )
            raise ValueError(message)
    return planned_duration


async def list_tasks_for_user(
    session: AsyncSession,
    created_by_sub: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Task]:
    """Return tasks for a user ordered by newest first."""
    stmt = (
        select(Task)
        .where(Task.created_by_sub == created_by_sub)
        .order_by(Task.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_task_for_user(
    session: AsyncSession,
    created_by_sub: str,
    payload: TaskCreate,
) -> Task:
    """Create a task for the given user."""
    data = payload.model_dump()
    duration = _coerce_planned_duration(
        data.get("planned_start_at"),
        data.get("planned_end_at"),
        data.get("planned_duration"),
    )
    task = Task(
        title=data["title"],
        description=data.get("description"),
        status=data.get("status", TaskStatus.BACKLOG),
        due_at=data.get("due_at"),
        planned_start_at=data.get("planned_start_at"),
        planned_end_at=data.get("planned_end_at"),
        planned_duration=duration,
        created_by_sub=created_by_sub,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task_for_user(session: AsyncSession, task_id: int, created_by_sub: str) -> Task | None:
    """Fetch a single task for a user by id."""
    stmt = select(Task).where(Task.id == task_id, Task.created_by_sub == created_by_sub)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_task_for_user(
    session: AsyncSession,
    task: Task,
    payload: TaskUpdate,
) -> Task:
    """Update an existing task owned by the user."""
    data = payload.model_dump(exclude_unset=True)
    # Apply simple fields
    for field in ("title", "description", "status", "due_at", "planned_start_at", "planned_end_at", "planned_duration"):
        if field in data:
            setattr(task, field, data[field])

    task.planned_duration = _coerce_planned_duration(
        task.planned_start_at,
        task.planned_end_at,
        task.planned_duration,
    )

    await session.commit()
    await session.refresh(task)
    return task


async def delete_task_for_user(session: AsyncSession, task: Task) -> None:
    """Delete a task and commit the change."""
    await session.delete(task)
    await session.commit()

