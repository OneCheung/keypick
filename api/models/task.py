"""
Task models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from .crawler_config import CrawlConfig


class TaskStatus(str, Enum):
    """Task status enum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Task(BaseModel):
    """Task model"""

    id: str = Field(..., description="Task UUID")
    name: str = Field(..., description="Task name")
    description: str | None = Field(default=None, description="Task description")
    platforms: list[str] = Field(..., description="List of enabled platforms")
    keywords: list[str] = Field(..., description="Search keywords")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    config: dict[str, Any] = Field(default={}, description="Additional configuration")
    crawl_config: Optional[CrawlConfig] = Field(default=None, description="Crawl configuration with time range, sorting, and fields")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    progress: int = Field(default=0, ge=0, le=100, description="Task progress percentage")
    error: str | None = Field(default=None, description="Error message if failed")


class TaskResult(BaseModel):
    """Task result model"""

    task_id: str = Field(..., description="Task ID reference")
    platform: str = Field(..., description="Platform name")
    raw_data: dict[str, Any] = Field(..., description="Raw crawled data")
    processed_data: dict[str, Any] | None = Field(default=None, description="Processed data")
    insights: dict[str, Any] | None = Field(default=None, description="Extracted insights")
    report: str | None = Field(default=None, description="Generated report")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    item_count: int = Field(default=0, description="Number of items collected")
    success: bool = Field(default=True, description="Whether the task succeeded")
