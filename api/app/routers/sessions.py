"""Session routes: nested under tasks and GET /sessions for timeline."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.task_session import TaskSessionStatus
from app.schemas.session import SessionCreate, SessionRead, SessionReadWithTask, SessionUpdate
from app.services.sessions import (
    create_session_for_task,
    delete_session_for_user,
    get_session_for_user,
    list_sessions_for_task,
    list_sessions_in_range,
    update_session_for_user,
)

task_sessions_router = APIRouter(tags=["task-sessions"])


@task_sessions_router.get("")
async def get_sessions_for_task(
    task_id: int,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
    date_from: Annotated[
        datetime | None,
        Query(alias="date_from", description="Filter sessions ending on/after"),
    ] = None,
    date_to: Annotated[
        datetime | None,
        Query(alias="date_to", description="Filter sessions starting on/before"),
    ] = None,
    session_status: Annotated[
        str | None,
        Query(description="INCOMPLETE or COMPLETED"),
    ] = None,
) -> list[SessionRead]:
    """List sessions for a task owned by the current user."""
    status_filter = None
    if session_status is not None:
        try:
            status_filter = TaskSessionStatus(session_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status must be INCOMPLETE or COMPLETED",
            ) from None
    sessions = await list_sessions_for_task(
        db_session,
        task_id,
        current_user["sub"],
        date_from=date_from,
        date_to=date_to,
        status=status_filter,
    )
    return [SessionRead.model_validate(s) for s in sessions]


@task_sessions_router.post("", status_code=201)
async def create_session(
    task_id: int,
    payload: SessionCreate,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionRead:
    """Create a session for the task. Overlap check required."""
    try:
        session_obj = await create_session_for_task(db_session, task_id, current_user["sub"], payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SessionRead.model_validate(session_obj)


@task_sessions_router.patch("/{session_id}")
async def update_session(
    task_id: int,
    session_id: int,
    payload: SessionUpdate,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionRead:
    """Update a session. Overlap check required for time changes."""
    session_obj = await get_session_for_user(db_session, task_id, session_id, current_user["sub"])
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    try:
        updated = await update_session_for_user(db_session, session_obj, payload, current_user["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SessionRead.model_validate(updated)


@task_sessions_router.delete("/{session_id}", status_code=204)
async def delete_session(
    task_id: int,
    session_id: int,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Hard delete a session."""
    session_obj = await get_session_for_user(db_session, task_id, session_id, current_user["sub"])
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    await delete_session_for_user(db_session, session_obj)


# Timeline: list sessions in range with task info
sessions_range_router = APIRouter(prefix="/sessions", tags=["sessions"])


@sessions_range_router.get("")
async def get_sessions_in_range_endpoint(
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
    from_at: Annotated[datetime, Query(..., alias="from", description="Start of range (ISO datetime)")],
    to_at: Annotated[datetime, Query(..., alias="to", description="End of range (ISO datetime)")],
) -> list[SessionReadWithTask]:
    """List sessions in [from, to] for the current user, with task title for timeline."""
    if from_at >= to_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from must be before to")
    pairs = await list_sessions_in_range(db_session, current_user["sub"], from_at, to_at)
    return [
        SessionReadWithTask(
            id=s.id,
            task_id=s.task_id,
            task_title=title,
            scheduled_start_at=s.scheduled_start_at,
            scheduled_end_at=s.scheduled_end_at,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s, title in pairs
    ]
