from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.routers import sessions as sessions_router
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.sessions import get_session_counts_for_tasks
from app.services.tasks import (
    create_task_for_user,
    delete_task_for_user,
    get_task_for_user,
    list_tasks_for_user,
    update_task_for_user,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
router.include_router(sessions_router.task_sessions_router, prefix="/{task_id}/sessions")


@router.get("/")
async def get_tasks(
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskRead]:
    """List tasks owned by the current user."""
    tasks = await list_tasks_for_user(db_session, current_user["sub"], limit=limit, offset=offset)
    task_ids = [t.id for t in tasks]
    counts = await get_session_counts_for_tasks(db_session, task_ids)
    result = []
    for task in tasks:
        read = TaskRead.model_validate(task)
        total, completed = counts.get(task.id, (0, 0))
        result.append(read.model_copy(update={"sessions_count": total, "completed_sessions_count": completed}))
    return result


@router.post("/", status_code=201)
async def create_task(
    payload: TaskCreate,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRead:
    """Create a new task for the current user."""
    try:
        task = await create_task_for_user(db_session, current_user["sub"], payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    counts = await get_session_counts_for_tasks(db_session, [task.id])
    total, completed = counts.get(task.id, (0, 0))
    read = TaskRead.model_validate(task)
    return read.model_copy(update={"sessions_count": total, "completed_sessions_count": completed})


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a task owned by the current user."""
    task = await get_task_for_user(db_session, task_id, current_user["sub"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await delete_task_for_user(db_session, task)


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRead:
    """Update a task owned by the current user."""
    task = await get_task_for_user(db_session, task_id, current_user["sub"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        updated = await update_task_for_user(db_session, task, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    counts = await get_session_counts_for_tasks(db_session, [updated.id])
    total, completed = counts.get(updated.id, (0, 0))
    read = TaskRead.model_validate(updated)
    return read.model_copy(update={"sessions_count": total, "completed_sessions_count": completed})


# Support PUT for clients that use full updates
@router.put("/{task_id}")
async def update_task_put(
    task_id: int,
    payload: TaskUpdate,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRead:
    """Full update variant for clients that use PUT semantics."""
    return await update_task(task_id, payload, current_user, db_session)


# Single-task get (for consistency; optional - not in plan but useful for edit drawer)
@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRead:
    """Get a single task by id."""
    task = await get_task_for_user(db_session, task_id, current_user["sub"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    counts = await get_session_counts_for_tasks(db_session, [task.id])
    total, completed = counts.get(task.id, (0, 0))
    read = TaskRead.model_validate(task)
    return read.model_copy(update={"sessions_count": total, "completed_sessions_count": completed})
