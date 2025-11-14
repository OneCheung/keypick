"""
Cookie management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from api.services.cookie_manager import get_cookie_manager

router = APIRouter(prefix="/api/cookies", tags=["Cookies"])


class SetCookieRequest(BaseModel):
    """Set cookie request model"""
    platform: str
    cookie_string: str
    login_type: str = "cookie"


class CookieResponse(BaseModel):
    """Cookie response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.get("/", response_model=CookieResponse)
async def list_cookies():
    """
    List all platform cookies and their status
    """
    cookie_manager = get_cookie_manager()
    cookies = cookie_manager.list_cookies()

    return CookieResponse(
        success=True,
        message="Cookies retrieved successfully",
        data=cookies
    )


@router.post("/set", response_model=CookieResponse)
async def set_cookie(request: SetCookieRequest):
    """
    Set cookie for a platform

    Args:
        request: Cookie data including platform and cookie string
    """
    cookie_manager = get_cookie_manager()

    success = cookie_manager.set_cookie(
        platform=request.platform,
        cookie_string=request.cookie_string,
        login_type=request.login_type
    )

    if success:
        return CookieResponse(
            success=True,
            message=f"Cookie set for {request.platform}",
            data={"platform": request.platform}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set cookie for {request.platform}"
        )


@router.get("/{platform}", response_model=CookieResponse)
async def get_cookie(platform: str):
    """
    Get cookie for a specific platform

    Args:
        platform: Platform name (xiaohongshu, weibo, douyin)
    """
    cookie_manager = get_cookie_manager()
    cookie_data = cookie_manager.get_cookie(platform)

    if cookie_data:
        # Don't expose the actual cookie string for security
        safe_data = {
            "platform": platform,
            "has_cookie": True,
            "login_type": cookie_data.get("login_type"),
            "is_valid": cookie_manager.is_cookie_valid(platform),
            "updated_at": cookie_data.get("updated_at"),
            "expire_at": cookie_data.get("expire_at")
        }
        return CookieResponse(
            success=True,
            message=f"Cookie found for {platform}",
            data=safe_data
        )
    else:
        return CookieResponse(
            success=False,
            message=f"No cookie found for {platform}",
            data={"platform": platform, "has_cookie": False}
        )


@router.delete("/{platform}", response_model=CookieResponse)
async def clear_cookie(platform: str):
    """
    Clear cookie for a specific platform

    Args:
        platform: Platform name
    """
    cookie_manager = get_cookie_manager()
    success = cookie_manager.clear_cookie(platform)

    if success:
        return CookieResponse(
            success=True,
            message=f"Cookie cleared for {platform}",
            data={"platform": platform}
        )
    else:
        return CookieResponse(
            success=False,
            message=f"No cookie found for {platform}",
            data={"platform": platform}
        )


@router.post("/refresh", response_model=CookieResponse)
async def refresh_cookies():
    """
    Refresh cookies from environment variables
    """
    cookie_manager = get_cookie_manager()
    cookie_manager.update_from_env()

    cookies = cookie_manager.list_cookies()
    return CookieResponse(
        success=True,
        message="Cookies refreshed from environment",
        data=cookies
    )


@router.get("/platforms/urls", response_model=CookieResponse)
async def get_platform_urls():
    """
    Get platform URLs for manual login
    """
    cookie_manager = get_cookie_manager()
    urls = {}

    for platform in ["xiaohongshu", "weibo", "douyin"]:
        url = cookie_manager.get_platform_url(platform)
        if url:
            urls[platform] = url

    return CookieResponse(
        success=True,
        message="Platform URLs retrieved",
        data=urls
    )