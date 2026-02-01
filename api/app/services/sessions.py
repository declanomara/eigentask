from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.task_session import TaskSession, TaskSessionStatus
from app.schemas.session import SessionCreate, SessionUpdate


def _normalize_create_times(payload: SessionCreate) -> tuple[datetime, datetime]:
    """Return (scheduled_start_at, scheduled_end_at) from create payload. Handles start+duration."""
    if payload.scheduled_end_at is not None:
        return payload.scheduled_start_at, payload.scheduled_end_at
    if payload.duration_minutes is not None and payload.duration_minutes > 0:
        end = payload.scheduled_start_at + timedelta(minutes=payload.duration_minutes)
        return payload.scheduled_start_at, end
    raise ValueError("provide either scheduled_end_at or duration_minutes")


async def _sessions_overlap(
    session: AsyncSession,
    created_by_sub: str,
    start_at: datetime,
    end_at: datetime,
    *,
    exclude_session_id: int | None = None,
) -> bool:
    """Return True if [start_at, end_at] overlaps any other session for this user."""
    # Same-day sessions for this user (via task ownership)
    stmt = (
        select(TaskSession.id)
        .join(Task, TaskSession.task_id == Task.id)
        .where(
            Task.created_by_sub == created_by_sub,
            TaskSession.scheduled_start_at < end_at,
            TaskSession.scheduled_end_at > start_at,
        )
    )
    if exclude_session_id is not None:
        stmt = stmt.where(TaskSession.id != exclude_session_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_sessions_for_task(
    session: AsyncSession,
    task_id: int,
    created_by_sub: str,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: TaskSessionStatus | None = None,
) -> list[TaskSession]:
    """List sessions for a task owned by the user, optionally filtered by date/status."""
    stmt = (
        select(TaskSession)
        .join(Task, TaskSession.task_id == Task.id)
        .where(Task.id == task_id, Task.created_by_sub == created_by_sub)
    )
    if date_from is not None:
        stmt = stmt.where(TaskSession.scheduled_end_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(TaskSession.scheduled_start_at <= date_to)
    if status is not None:
        stmt = stmt.where(TaskSession.status == status)
    stmt = stmt.order_by(TaskSession.scheduled_start_at)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_sessions_in_range(
    session: AsyncSession,
    created_by_sub: str,
    from_at: datetime,
    to_at: datetime,
) -> list[tuple[TaskSession, str]]:
    """List sessions in [from_at, to_at] for the user, with task title. Returns [(session, task_title), ...]."""
    stmt = (
        select(TaskSession, Task.title)
        .join(Task, TaskSession.task_id == Task.id)
        .where(
            Task.created_by_sub == created_by_sub,
            TaskSession.scheduled_start_at < to_at,
            TaskSession.scheduled_end_at > from_at,
        )
        .order_by(TaskSession.scheduled_start_at)
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_session_for_user(
    session: AsyncSession,
    task_id: int,
    session_id: int,
    created_by_sub: str,
) -> TaskSession | None:
    """Fetch a single session by task_id and session_id if owned by the user."""
    stmt = (
        select(TaskSession)
        .join(Task, TaskSession.task_id == Task.id)
        .where(
            TaskSession.id == session_id,
            TaskSession.task_id == task_id,
            Task.created_by_sub == created_by_sub,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_session_for_task(
    session: AsyncSession,
    task_id: int,
    created_by_sub: str,
    payload: SessionCreate,
) -> TaskSession:
    """Create a session for the task; set task to PLANNED if first session. Overlap check required."""
    task = await session.get(Task, task_id)
    if task is None or task.created_by_sub != created_by_sub:
        raise LookupError("task not found")

    start_at, end_at = _normalize_create_times(payload)
    if await _sessions_overlap(session, created_by_sub, start_at, end_at):
        raise ValueError("session overlaps another scheduled session")

    count_stmt = select(func.count(TaskSession.id)).where(TaskSession.task_id == task_id)
    count_result = await session.execute(count_stmt)
    is_first_session = (count_result.scalar() or 0) == 0

    task_session = TaskSession(
        task_id=task_id,
        scheduled_start_at=start_at,
        scheduled_end_at=end_at,
        status=TaskSessionStatus.INCOMPLETE,
    )
    session.add(task_session)
    if is_first_session:
        task.status = TaskStatus.PLANNED
    await session.commit()
    await session.refresh(task_session)
    return task_session


async def update_session_for_user(
    session: AsyncSession,
    task_session: TaskSession,
    payload: SessionUpdate,
    created_by_sub: str,
) -> TaskSession:
    """Update a session; overlap check required for time changes."""
    data = payload.model_dump(exclude_unset=True)
    new_start = data.get("scheduled_start_at", task_session.scheduled_start_at)
    new_end = data.get("scheduled_end_at", task_session.scheduled_end_at)
    if "scheduled_start_at" in data or "scheduled_end_at" in data:
        if new_end <= new_start:
            raise ValueError("scheduled_end_at must be after scheduled_start_at")
        if await _sessions_overlap(
            session,
            created_by_sub,
            new_start,
            new_end,
            exclude_session_id=task_session.id,
        ):
            raise ValueError("session overlaps another scheduled session")
        task_session.scheduled_start_at = new_start
        task_session.scheduled_end_at = new_end
    if "status" in data:
        task_session.status = data["status"]
    await session.commit()
    await session.refresh(task_session)
    return task_session


async def delete_session_for_user(
    session: AsyncSession,
    task_session: TaskSession,
) -> None:
    """Hard delete the session."""
    await session.delete(task_session)
    await session.commit()


async def get_session_counts_for_tasks(
    session: AsyncSession,
    task_ids: list[int],
) -> dict[int, tuple[int, int]]:
    """Return task_id -> (sessions_count, completed_sessions_count) for the given task ids."""
    if not task_ids:
        return {}
    stmt = (
        select(
            TaskSession.task_id,
            func.count(TaskSession.id).label("total"),
            func.count(TaskSession.id).filter(
                TaskSession.status == TaskSessionStatus.COMPLETED
            ).label("completed"),
        )
        .where(TaskSession.task_id.in_(task_ids))
        .group_by(TaskSession.task_id)
    )
    result = await session.execute(stmt)
    rows = result.all()
    out: dict[int, tuple[int, int]] = {}
    for task_id, total, completed in rows:
        out[task_id] = (total, completed or 0)
    for tid in task_ids:
        if tid not in out:
            out[tid] = (0, 0)
    return out
