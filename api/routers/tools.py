"""
Dify tools API endpoints
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from api.services.dify_service import DifyService
from api.models.platform import PlatformType

router = APIRouter()

# Initialize services
dify_service = DifyService()


class DifyCrawlRequest(BaseModel):
    """Dify crawl tool request format"""
    platform: str = Field(..., description="Platform to crawl (weibo, xiaohongshu, douyin)")
    keywords: str = Field(..., description="Keywords to search (comma-separated)")
    max_results: int = Field(default=100, description="Maximum results to fetch")
    async_mode: bool = Field(default=False, description="Run in async mode")


class DifyCrawlResponse(BaseModel):
    """Dify crawl tool response format"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task_id: Optional[str] = None


class DifyToolSchema(BaseModel):
    """Dify tool schema definition"""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    response: Dict[str, Any]


@router.post("/dify/crawl", response_model=DifyCrawlResponse)
async def dify_crawl_tool(
    request: DifyCrawlRequest,
    authorization: Optional[str] = Header(None)
) -> DifyCrawlResponse:
    """
    Dify-compatible crawl tool endpoint

    This endpoint is designed to be called from Dify workflows.
    It accepts parameters in Dify's expected format and returns
    structured responses that Dify can process.
    """
    try:
        # Validate authorization if required
        if not dify_service.validate_auth(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Parse keywords
        keywords = [k.strip() for k in request.keywords.split(",") if k.strip()]

        # Validate platform
        if request.platform not in [p.value for p in PlatformType]:
            return DifyCrawlResponse(
                success=False,
                error=f"Unsupported platform: {request.platform}"
            )

        # Execute crawl
        if request.async_mode:
            # Async mode - return task ID immediately
            task_id = await dify_service.start_crawl_task(
                platform=request.platform,
                keywords=keywords,
                max_results=request.max_results
            )

            return DifyCrawlResponse(
                success=True,
                task_id=task_id,
                data={"status": "processing", "task_id": task_id}
            )
        else:
            # Sync mode - wait for results
            result = await dify_service.crawl_sync(
                platform=request.platform,
                keywords=keywords,
                max_results=request.max_results
            )

            return DifyCrawlResponse(
                success=True,
                data=result
            )

    except HTTPException:
        raise
    except Exception as e:
        return DifyCrawlResponse(
            success=False,
            error=str(e)
        )


@router.get("/dify/schema", response_model=DifyToolSchema)
async def get_dify_tool_schema() -> DifyToolSchema:
    """
    Get Dify tool schema

    Returns the schema definition for the KeyPick crawler tool
    that can be imported into Dify.
    """
    return DifyToolSchema(
        name="keypick_crawler",
        description="Crawl social media content from various platforms",
        parameters=[
            {
                "name": "platform",
                "type": "string",
                "description": "Platform to crawl",
                "required": True,
                "enum": ["weibo", "xiaohongshu", "douyin"]
            },
            {
                "name": "keywords",
                "type": "string",
                "description": "Comma-separated keywords to search",
                "required": True
            },
            {
                "name": "max_results",
                "type": "integer",
                "description": "Maximum number of results",
                "required": False,
                "default": 100,
                "minimum": 1,
                "maximum": 1000
            },
            {
                "name": "async_mode",
                "type": "boolean",
                "description": "Run in async mode",
                "required": False,
                "default": False
            }
        ],
        response={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object"},
                "error": {"type": "string"},
                "task_id": {"type": "string"}
            }
        }
    )


@router.get("/dify/task/{task_id}")
async def get_dify_task_status(
    task_id: str,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get Dify task status

    Check the status of an async crawl task initiated from Dify.
    """
    try:
        # Validate authorization
        if not dify_service.validate_auth(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Get task status
        status = await dify_service.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "success": True,
            "task_id": task_id,
            "status": status.get("status"),
            "progress": status.get("progress"),
            "result": status.get("result"),
            "error": status.get("error")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.post("/dify/webhook")
async def dify_webhook(
    event: Dict[str, Any],
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dify webhook endpoint

    Receives webhook events from Dify workflows for task completion,
    errors, or other events.
    """
    try:
        # Validate authorization
        if not dify_service.validate_auth(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Process webhook event
        result = await dify_service.process_webhook(event)

        return {
            "success": True,
            "message": "Webhook processed successfully",
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")