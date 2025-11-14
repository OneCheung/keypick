"""
Crawler API endpoints
"""

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from api.models.platform import Platform, PlatformType
from api.models.task import TaskStatus
from api.models.crawler_config import CrawlConfig, SortBy
from api.services.crawler_service import CrawlerService

router = APIRouter()

# Initialize services
crawler_service = CrawlerService()


class CrawlRequest(BaseModel):
    """
    Crawl request model with enhanced configuration

    Note: Basic fields (title, content, likes, collects, comments, publish_time,
    author, tags, url) are ALWAYS crawled by default.
    """

    platform: PlatformType = Field(..., description="Platform to crawl")
    keywords: list[str] = Field(..., description="Keywords to search")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results to fetch")
    config: dict = Field(default={}, description="Additional platform-specific configuration")

    # Enhanced configuration options
    time_range: Optional[str] = Field(default="7d", description="Time range (e.g., '7d', '30d', '2024-01-01,2024-12-31')")
    sort_by: Optional[SortBy] = Field(default=SortBy.HOT, description="How to sort results")

    # Extended data collection options
    include_comments: bool = Field(default=False, description="Crawl comment details")
    crawl_author_details: bool = Field(default=False, description="Crawl author statistics and share_count")
    max_comments_per_post: Optional[int] = Field(default=50, ge=1, le=500, description="Max comments to crawl per post (when include_comments=True)")

    # Pagination and filters
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Max items to return")
    offset: Optional[int] = Field(default=0, ge=0, description="Number of items to skip")
    min_likes: Optional[int] = Field(default=None, ge=0, description="Minimum number of likes")
    min_comments: Optional[int] = Field(default=None, ge=0, description="Minimum number of comments")


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

    Basic fields are always crawled: title, content, likes, collects, comments,
    publish_time, author, tags, url

    Extended options:
    - include_comments: Crawl comment details
    - crawl_author_details: Crawl author statistics and share_count
    - time_range: "7d", "30d", or custom date range
    - sort_by: "hot", "recent", "trending", etc.
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Validate platform
        if request.platform not in [p.value for p in PlatformType]:
            raise ValueError(f"Unsupported platform: {request.platform}")

        # Create CrawlConfig from request parameters
        crawl_config = CrawlConfig(
            time_range=request.time_range,
            sort_by=request.sort_by,
            include_comments=request.include_comments,
            crawl_author_details=request.crawl_author_details,
            max_comments_per_post=request.max_comments_per_post if request.max_comments_per_post else 50,
            limit=request.limit or request.max_results,
            offset=request.offset,
            min_likes=request.min_likes,
            min_comments=request.min_comments,
            platform_config=request.config
        )

        # Start crawl task in background
        background_tasks.add_task(
            crawler_service.execute_crawl,
            task_id=task_id,
            platform=request.platform,
            keywords=request.keywords,
            max_results=request.max_results,
            config=request.config,
            crawl_config=crawl_config,
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
                "time_range": request.time_range,
                "sort_by": request.sort_by.value if request.sort_by else "hot",
                "include_comments": request.include_comments,
                "crawl_author_details": request.crawl_author_details,
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
