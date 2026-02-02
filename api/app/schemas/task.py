from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Task creation payload including planning fields."""

    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    due_at: datetime
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    planned_duration: int | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            message = "title cannot be blank"
            raise ValueError(message)
        return value

    @field_validator("planned_duration")
    @classmethod
    def _planned_duration_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            message = "planned_duration must be positive when provided"
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def _validate_schedule(self) -> "TaskCreate":
        if self.planned_start_at and self.planned_end_at and self.planned_end_at < self.planned_start_at:
            message = "planned_end_at must be after planned_start_at"
            raise ValueError(message)
        return self


class TaskUpdate(BaseModel):
    """Task update payload; all fields optional."""

    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    status: TaskStatus | None = Field(default=None)
    due_at: datetime | None = Field(default=None)
    planned_start_at: datetime | None = Field(default=None)
    planned_end_at: datetime | None = Field(default=None)
    planned_duration: int | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            message = "title cannot be blank"
            raise ValueError(message)
        return value

    @field_validator("planned_duration")
    @classmethod
    def _planned_duration_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            message = "planned_duration must be positive when provided"
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def _validate_schedule(self) -> "TaskUpdate":
        if self.planned_start_at and self.planned_end_at and self.planned_end_at < self.planned_start_at:
            message = "planned_end_at must be after planned_start_at"
            raise ValueError(message)
        return self


class TaskRead(BaseModel):
    """Task response schema."""

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_at: datetime | None
    planned_start_at: datetime | None
    planned_end_at: datetime | None
    planned_duration: int | None
    created_at: datetime
    updated_at: datetime
    sessions_count: int = 0
    completed_sessions_count: int = 0

    model_config = ConfigDict(from_attributes=True)

