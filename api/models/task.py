"""
Task models
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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
    description: Optional[str] = Field(default=None, description="Task description")
    platforms: List[str] = Field(..., description="List of enabled platforms")
    keywords: List[str] = Field(..., description="Search keywords")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    config: Dict[str, Any] = Field(default={}, description="Additional configuration")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    progress: int = Field(default=0, ge=0, le=100, description="Task progress percentage")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class TaskResult(BaseModel):
    """Task result model"""
    task_id: str = Field(..., description="Task ID reference")
    platform: str = Field(..., description="Platform name")
    raw_data: Dict[str, Any] = Field(..., description="Raw crawled data")
    processed_data: Optional[Dict[str, Any]] = Field(default=None, description="Processed data")
    insights: Optional[Dict[str, Any]] = Field(default=None, description="Extracted insights")
    report: Optional[str] = Field(default=None, description="Generated report")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    item_count: int = Field(default=0, description="Number of items collected")
    success: bool = Field(default=True, description="Whether the task succeeded")