"""Integration tests for tasks router."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from tests.factories import create_sample_tasks, create_task


@pytest.mark.integration
class TestTasksList:
    """Tests for GET /tasks/."""

    async def test_list_tasks_returns_user_tasks(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that listing tasks returns only the authenticated user's tasks."""
        # Create tasks for authenticated user
        user_tasks = create_sample_tasks("test-user-123")
        for task in user_tasks:
            db_session.add(task)

        # Create tasks for another user (should not appear)
        other_tasks = create_sample_tasks("another-user-456")
        for task in other_tasks:
            db_session.add(task)

        await db_session.commit()

        # Request tasks
        response = await authenticated_client.get("/tasks/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(user_tasks)

        # Verify all returned tasks belong to the authenticated user
        for task_data in data:
            assert "id" in task_data
            assert "title" in task_data
            assert "status" in task_data

    async def test_list_tasks_empty_when_no_tasks(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that listing tasks returns empty array when user has no tasks."""
        response = await authenticated_client.get("/tasks/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_tasks_respects_limit(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that the limit parameter restricts the number of results."""
        # Create 10 tasks
        for i in range(10):
            task = create_task(title=f"Task {i}", created_by_sub="test-user-123")
            db_session.add(task)
        await db_session.commit()

        # Request with limit=5
        response = await authenticated_client.get("/tasks/?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    async def test_list_tasks_respects_offset(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that the offset parameter skips results correctly."""
        # Create tasks with distinct titles
        for i in range(5):
            task = create_task(title=f"Task {i}", created_by_sub="test-user-123")
            db_session.add(task)
        await db_session.commit()

        # Get all tasks first
        all_response = await authenticated_client.get("/tasks/")
        all_tasks = all_response.json()

        # Request with offset=2
        offset_response = await authenticated_client.get("/tasks/?offset=2")
        offset_tasks = offset_response.json()

        assert offset_response.status_code == 200
        assert len(offset_tasks) == 3
        # Verify offset worked by comparing IDs
        assert offset_tasks[0]["id"] == all_tasks[2]["id"]

    async def test_list_tasks_unauthorized_without_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that listing tasks requires authentication."""
        response = await client.get("/tasks/")

        assert response.status_code == 401


@pytest.mark.integration
class TestTasksCreate:
    """Tests for POST /tasks/."""

    async def test_create_task_successfully(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test creating a task with valid data."""
        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        payload = {
            "title": "New Test Task",
            "description": "Test description",
            "status": "BACKLOG",
            "due_at": due,
        }

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["status"] == payload["status"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify task was saved to database
        result = await db_session.execute(select(Task).where(Task.id == data["id"]))
        db_task = result.scalar_one_or_none()
        assert db_task is not None
        assert db_task.title == payload["title"]
        assert db_task.created_by_sub == "test-user-123"

    async def test_create_task_with_planning_fields(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test creating a task with planning fields."""
        now = datetime.now(UTC)
        start = now + timedelta(hours=1)
        end = start + timedelta(hours=2)
        due = (now + timedelta(days=1)).isoformat()

        payload = {
            "title": "Planned Task",
            "description": "Task with planning",
            "status": "PLANNED",
            "due_at": due,
            "planned_start_at": start.isoformat(),
            "planned_end_at": end.isoformat(),
            "planned_duration": 120,
        }

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["planned_duration"] == 120
        assert data["planned_start_at"] is not None
        assert data["planned_end_at"] is not None

    async def test_create_task_minimal_payload(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating a task with only required fields."""
        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        payload = {"title": "Minimal Task", "due_at": due}

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Task"
        assert data["description"] is None
        assert data["status"] == "BACKLOG"  # Default status

    async def test_create_task_blank_title_fails(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that creating a task with blank title fails validation."""
        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        payload = {"title": "   ", "due_at": due}  # Blank/whitespace only title

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 422  # Pydantic validation error
        detail = response.json()["detail"]
        assert any("title cannot be blank" in str(err) for err in detail)

    async def test_create_task_invalid_schedule_fails(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that invalid planning schedule fails validation."""
        now = datetime.now(UTC)
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=1)  # End before start
        due = (now + timedelta(days=1)).isoformat()

        payload = {
            "title": "Invalid Schedule",
            "due_at": due,
            "planned_start_at": start.isoformat(),
            "planned_end_at": end.isoformat(),
        }

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 422  # Pydantic validation error
        detail = response.json()["detail"]
        assert any("planned_end_at must be after planned_start_at" in str(err) for err in detail)

    async def test_create_task_negative_duration_fails(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that negative planned duration fails validation."""
        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        payload = {
            "title": "Task",
            "due_at": due,
            "planned_duration": -10,
        }

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 422  # Pydantic validation error
        detail = response.json()["detail"]
        assert any("planned_duration must be positive" in str(err) for err in detail)

    async def test_create_task_unauthorized_without_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that creating a task requires authentication."""
        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        payload = {"title": "Test Task", "due_at": due}

        response = await client.post("/tasks/", json=payload)

        assert response.status_code == 401

    async def test_create_task_missing_due_at_fails(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that creating a task without due_at fails validation."""
        payload = {"title": "Task without due date"}

        response = await authenticated_client.post("/tasks/", json=payload)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("due_at" in str(err).lower() for err in detail)


@pytest.mark.integration
class TestTasksUpdate:
    """Tests for PATCH /tasks/{task_id}."""

    async def test_update_task_successfully(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test updating a task with valid data."""
        # Create a task
        task = create_task(title="Original Title", created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Update the task
        payload = {
            "title": "Updated Title",
            "status": "COMPLETED",
        }

        response = await authenticated_client.patch(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "COMPLETED"

        # Verify in database
        await db_session.refresh(task)
        assert task.title == "Updated Title"
        assert task.status == TaskStatus.COMPLETED

    async def test_update_task_partial_fields(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test updating only some fields leaves others unchanged."""
        # Create a task
        task = create_task(
            title="Original Title",
            description="Original Description",
            created_by_sub="test-user-123",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Update only title
        payload = {"title": "New Title"}

        response = await authenticated_client.patch(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["description"] == "Original Description"  # Unchanged

    async def test_update_task_not_found(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test updating a non-existent task returns 404."""
        payload = {"title": "Updated"}

        response = await authenticated_client.patch("/tasks/99999", json=payload)

        assert response.status_code == 404

    async def test_update_task_forbidden_for_other_user(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that users cannot update tasks owned by others."""
        # Create a task owned by another user
        task = create_task(title="Other User Task", created_by_sub="another-user-456")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Try to update as authenticated user
        payload = {"title": "Hacked"}

        response = await authenticated_client.patch(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 404  # Treated as not found for security

    async def test_update_task_blank_title_fails(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that updating with blank title fails validation."""
        task = create_task(created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        payload = {"title": "   "}

        response = await authenticated_client.patch(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 422  # Pydantic validation error
        detail = response.json()["detail"]
        assert any("title cannot be blank" in str(err) for err in detail)

    async def test_update_task_unauthorized_without_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that updating a task requires authentication."""
        # Create a task
        task = create_task(created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        payload = {"title": "Updated"}

        response = await client.patch(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 401


@pytest.mark.integration
class TestTasksDelete:
    """Tests for DELETE /tasks/{task_id}."""

    async def test_delete_task_successfully(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting a task successfully."""
        # Create a task
        task = create_task(created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        task_id = task.id

        # Delete the task
        response = await authenticated_client.delete(f"/tasks/{task_id}")

        assert response.status_code == 204

        # Verify task is deleted
        result = await db_session.execute(select(Task).where(Task.id == task_id))
        assert result.scalar_one_or_none() is None

    async def test_delete_task_not_found(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test deleting a non-existent task returns 404."""
        response = await authenticated_client.delete("/tasks/99999")

        assert response.status_code == 404

    async def test_delete_task_forbidden_for_other_user(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that users cannot delete tasks owned by others."""
        # Create a task owned by another user
        task = create_task(title="Other User Task", created_by_sub="another-user-456")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Try to delete as authenticated user
        response = await authenticated_client.delete(f"/tasks/{task.id}")

        assert response.status_code == 404  # Treated as not found for security

        # Verify task still exists
        result = await db_session.execute(select(Task).where(Task.id == task.id))
        assert result.scalar_one_or_none() is not None

    async def test_delete_task_unauthorized_without_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that deleting a task requires authentication."""
        # Create a task
        task = create_task(created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.delete(f"/tasks/{task.id}")

        assert response.status_code == 401


@pytest.mark.integration
class TestTasksPut:
    """Tests for PUT /tasks/{task_id}."""

    async def test_put_update_works_like_patch(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that PUT works the same as PATCH."""
        # Create a task
        task = create_task(title="Original Title", created_by_sub="test-user-123")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Update via PUT
        payload = {"title": "Updated via PUT"}

        response = await authenticated_client.put(f"/tasks/{task.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated via PUT"
