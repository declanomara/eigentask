"""Test data factories for creating model instances."""

from datetime import UTC, datetime, timedelta

from app.models.task import Task, TaskStatus


def create_task(
    *,
    title: str = "Test Task",
    description: str | None = "Test task description",
    status: TaskStatus = TaskStatus.BACKLOG,
    created_by_sub: str = "test-user-123",
    due_at: datetime | None = None,
    planned_start_at: datetime | None = None,
    planned_end_at: datetime | None = None,
    planned_duration: int | None = None,
) -> Task:
    """Create a Task instance for testing.

    Args:
        title: Task title
        description: Task description
        status: Task status
        created_by_sub: User's OIDC subject
        due_at: Due date
        planned_start_at: Planned start time
        planned_end_at: Planned end time
        planned_duration: Planned duration in minutes

    Returns:
        Task instance (not yet persisted to database)

    """
    return Task(
        title=title,
        description=description,
        status=status,
        created_by_sub=created_by_sub,
        due_at=due_at,
        planned_start_at=planned_start_at,
        planned_end_at=planned_end_at,
        planned_duration=planned_duration,
    )


def create_sample_tasks(user_sub: str = "test-user-123") -> list[Task]:
    """Create a list of sample tasks for testing.

    Args:
        user_sub: User's OIDC subject to assign tasks to

    Returns:
        List of Task instances (not yet persisted)

    """
    now = datetime.now(UTC)
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)

    return [
        create_task(
            title="Complete project documentation",
            description="Write comprehensive docs",
            status=TaskStatus.BACKLOG,
            created_by_sub=user_sub,
        ),
        create_task(
            title="Review pull requests",
            description="Review and merge PRs",
            status=TaskStatus.PLANNED,
            created_by_sub=user_sub,
            planned_start_at=tomorrow,
            planned_end_at=tomorrow + timedelta(hours=2),
            planned_duration=120,
        ),
        create_task(
            title="Deploy to production",
            description="Release v1.0",
            status=TaskStatus.COMPLETED,
            created_by_sub=user_sub,
            due_at=next_week,
        ),
        create_task(
            title="Refactor legacy code",
            description=None,
            status=TaskStatus.BACKLOG,
            created_by_sub=user_sub,
        ),
    ]
