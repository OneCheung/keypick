"""
Crawler API endpoints
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from api.models.platform import Platform, PlatformType
from api.models.task import TaskStatus
from api.services.crawler_service import CrawlerService

router = APIRouter()

# Initialize services
crawler_service = CrawlerService()


class CrawlRequest(BaseModel):
    """Crawl request model"""

    platform: PlatformType = Field(..., description="Platform to crawl")
    keywords: list[str] = Field(..., description="Keywords to search")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results to fetch")
    config: dict = Field(default={}, description="Additional platform-specific configuration")


class CrawlResponse(BaseModel):
    """Crawl response model"""

    success: bool
    task_id: str
    status: TaskStatus
    message: str
    data: dict | None = None


class TaskStatusResponse(BaseModel):
    """Task status response"""

    task_id: str
    status: TaskStatus
    progress: int = 0
    message: str = ""
    result: dict | None = None
    error: str | None = None


@router.post("/", response_model=CrawlResponse)
async def execute_crawl(request: CrawlRequest, background_tasks: BackgroundTasks) -> CrawlResponse:
    """
    Execute a crawl task

    This endpoint initiates a crawling task for the specified platform
    and keywords. The task runs asynchronously in the background.
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Validate platform
        if request.platform not in [p.value for p in PlatformType]:
            raise ValueError(f"Unsupported platform: {request.platform}")

        # Start crawl task in background
        background_tasks.add_task(
            crawler_service.execute_crawl,
            task_id=task_id,
            platform=request.platform,
            keywords=request.keywords,
            max_results=request.max_results,
            config=request.config,
        )

        return CrawlResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Crawl task started for {request.platform}",
            data={
                "platform": request.platform,
                "keywords": request.keywords,
                "max_results": request.max_results,
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start crawl task: {str(e)}")


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_crawl_status(task_id: str) -> TaskStatusResponse:
    """
    Get the status of a crawl task

    Returns the current status, progress, and results (if completed)
    of a crawling task.
    """
    try:
        task_info = await crawler_service.get_task_status(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return TaskStatusResponse(
            task_id=task_id,
            status=task_info.get("status", TaskStatus.UNKNOWN),
            progress=task_info.get("progress", 0),
            message=task_info.get("message", ""),
            result=task_info.get("result"),
            error=task_info.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/platforms", response_model=list[Platform])
async def get_supported_platforms() -> list[Platform]:
    """
    Get list of supported platforms

    Returns information about all platforms that the crawler supports.
    """
    platforms = []

    for platform_type in PlatformType:
        platform = Platform(
            id=platform_type.value,
            name=platform_type.value.capitalize(),
            enabled=crawler_service.is_platform_enabled(platform_type.value),
            config={
                "max_results_limit": 1000,
                "rate_limit": 10,  # requests per minute
                "requires_auth": platform_type in [PlatformType.WEIBO],
            },
        )
        platforms.append(platform)

    return platforms


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str) -> dict:
    """
    Cancel a running crawl task

    Attempts to cancel a running task. Returns success status.
    """
    try:
        success = await crawler_service.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found or already completed"
            )

        return {"success": True, "message": f"Task {task_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")
