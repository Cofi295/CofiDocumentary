from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TaskType(StrEnum):
    IMAGE_GENERATION = 'image_generation'
    IMAGE_TO_VIDEO = 'image_to_video'


class SceneStatus(StrEnum):
    IDLE = 'idle'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class JobStatus(StrEnum):
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class WorkerState(StrEnum):
    READY = 'ready'
    RUNNING = 'running'
    COOLDOWN = 'cooldown'
    QUOTA_EXHAUSTED = 'quota_exhausted'


class SceneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    task_type: TaskType
    prompt: str = Field(min_length=1, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=12000)
    reference_image: str | None = None
    reference_images: list[str] = Field(default_factory=list, max_length=14)
    model: str = Field(min_length=1, max_length=120)
    aspect_ratio: str = Field(min_length=1, max_length=32)
    duration_seconds: int | None = Field(default=None, ge=1, le=300)

    @model_validator(mode='after')
    def default_video_duration(self):
        if self.reference_images:
            self.reference_image = self.reference_images[0]
        elif self.reference_image:
            self.reference_images = [self.reference_image]
        if self.task_type == TaskType.IMAGE_TO_VIDEO and self.duration_seconds is None:
            self.duration_seconds = 8
        return self


class SceneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    task_type: TaskType | None = None
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=12000)
    reference_image: str | None = None
    reference_images: list[str] | None = Field(default=None, max_length=14)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    aspect_ratio: str | None = Field(default=None, min_length=1, max_length=32)
    duration_seconds: int | None = Field(default=None, ge=1, le=300)


class SceneOut(SceneCreate):
    id: str
    status: SceneStatus
    progress: int = Field(ge=0, le=100)
    output_path: str | None
    created_at: str
    updated_at: str


class JobOut(BaseModel):
    id: str
    scene_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    worker_id: str | None
    error: str | None
    output_path: str | None
    created_at: str
    updated_at: str


class RetryScenesRequest(BaseModel):
    scene_ids: list[str] = Field(min_length=1, max_length=1000)


class WorkerOut(BaseModel):
    id: str
    name: str
    state: WorkerState
    progress: int = Field(ge=0, le=100)
    job_id: str | None
    concurrency: int = Field(ge=1, le=10)
    account_email: str | None = None
