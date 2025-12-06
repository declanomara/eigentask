from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.task import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    """Task creation request payload."""

    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    """Task update request."""

    title: str | None = None
    description: str | None = None


def _to_dict(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
    }


@router.get("/")
async def get_tasks(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, Any]]:
    """List tasks owned by the current user."""
    q = select(Task).where(Task.created_by_sub == current_user["sub"]).order_by(Task.id.desc())
    res = await db_session.execute(q)
    tasks = res.scalars().all()
    return [_to_dict(t) for t in tasks]


@router.post("/", status_code=201)
async def create_task(
    payload: TaskCreate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Create a new task for the current user."""
    t = Task(title=payload.title, description=payload.description, created_by_sub=current_user["sub"])
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return _to_dict(t)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a task owned by the current user."""
    q = select(Task).where(Task.id == task_id, Task.created_by_sub == current_user["sub"])
    res = await db_session.execute(q)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db_session.delete(t)
    await db_session.commit()


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Update a task owned by the current user."""
    q = select(Task).where(Task.id == task_id, Task.created_by_sub == current_user["sub"])
    res = await db_session.execute(q)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.title is not None:
        t.title = payload.title
    if payload.description is not None:
        t.description = payload.description
    await db_session.commit()
    await db_session.refresh(t)
    return _to_dict(t)


# Support PUT for clients that use full updates
@router.put("/{task_id}")
async def update_task_put(
    task_id: int,
    payload: TaskUpdate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    return await update_task(task_id, payload, current_user, db_session)
