from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task_session import TaskSessionStatus


class SessionCreate(BaseModel):
    """Session creation payload; accepts start+end or start+duration. API normalizes to start+end."""

    scheduled_start_at: datetime
    scheduled_end_at: datetime | None = None
    duration_minutes: int | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("duration_minutes")
    @classmethod
    def _duration_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("duration_minutes must be positive when provided")
        return v

    @model_validator(mode="after")
    def _require_end_or_duration(self) -> "SessionCreate":
        if self.scheduled_end_at is None and self.duration_minutes is None:
            raise ValueError("provide either scheduled_end_at or duration_minutes")
        if self.scheduled_end_at is not None and self.scheduled_end_at <= self.scheduled_start_at:
            raise ValueError("scheduled_end_at must be after scheduled_start_at")
        return self


class SessionUpdate(BaseModel):
    """Session update payload; all fields optional."""

    status: TaskSessionStatus | None = Field(default=None)
    scheduled_start_at: datetime | None = Field(default=None)
    scheduled_end_at: datetime | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _end_after_start(self) -> "SessionUpdate":
        start = self.scheduled_start_at
        end = self.scheduled_end_at
        if start is not None and end is not None and end <= start:
            raise ValueError("scheduled_end_at must be after scheduled_start_at")
        return self


class SessionRead(BaseModel):
    """Session response schema (nested under task)."""

    id: int
    task_id: int
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    status: TaskSessionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionReadWithTask(BaseModel):
    """Session response with task info for timeline (GET /sessions)."""

    id: int
    task_id: int
    task_title: str
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    status: TaskSessionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
