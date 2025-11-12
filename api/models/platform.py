"""
Platform models and enums
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Supported platform types"""

    WEIBO = "weibo"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    # Future platforms
    # BILIBILI = "bilibili"
    # ZHIHU = "zhihu"
    # TWITTER = "twitter"


class Platform(BaseModel):
    """Platform information model"""

    id: str = Field(..., description="Platform identifier")
    name: str = Field(..., description="Platform display name")
    enabled: bool = Field(default=True, description="Whether platform is enabled")
    config: dict[str, Any] = Field(default={}, description="Platform-specific configuration")
    description: str | None = Field(default=None, description="Platform description")


class PlatformConfig(BaseModel):
    """Platform-specific configuration"""

    max_results_limit: int = Field(default=1000, description="Maximum results per request")
    rate_limit: int = Field(default=10, description="Requests per minute")
    requires_auth: bool = Field(default=False, description="Whether authentication is required")
    auth_type: str | None = Field(
        default=None, description="Authentication type (cookie, token, oauth)"
    )
    proxy_required: bool = Field(default=False, description="Whether proxy is required")
    headers: dict[str, str] = Field(default={}, description="Custom headers for requests")
