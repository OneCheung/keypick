"""
Content data models - defines the standard structure for crawled content
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BaseContent(BaseModel):
    """
    Base content model with standard fields that are always crawled
    These fields correspond to database columns and are always included
    """

    # Primary identification
    id: str = Field(..., description="Unique content ID from platform")
    platform: str = Field(..., description="Platform name (xiaohongshu/weibo/douyin)")

    # Core content fields (always crawled)
    title: Optional[str] = Field(None, description="Content title")
    content: str = Field(..., description="Main content text")
    url: str = Field(..., description="Content URL")

    # Engagement metrics (always crawled)
    likes: int = Field(0, description="Number of likes")
    collects: int = Field(0, description="Number of collects/bookmarks")
    comments: int = Field(0, description="Number of comments")
    shares: int = Field(0, description="Number of shares/reposts")
    views: Optional[int] = Field(None, description="Number of views")

    # Author information (basic, always crawled)
    author: str = Field(..., description="Author name")
    author_id: str = Field(..., description="Author ID")
    author_avatar: Optional[str] = Field(None, description="Author avatar URL")

    # Metadata (always crawled)
    publish_time: datetime = Field(..., description="Content publish time")
    tags: List[str] = Field(default_factory=list, description="Content tags/hashtags")

    # Media information
    images: List[str] = Field(default_factory=list, description="Image URLs")
    videos: List[str] = Field(default_factory=list, description="Video URLs")

    # Crawl metadata
    crawl_time: datetime = Field(default_factory=datetime.utcnow, description="When content was crawled")
    task_id: Optional[str] = Field(None, description="Associated task ID")


class CommentDetail(BaseModel):
    """Comment details - only crawled when include_comments=True"""

    comment_id: str = Field(..., description="Comment ID")
    author: str = Field(..., description="Comment author")
    author_id: str = Field(..., description="Comment author ID")
    content: str = Field(..., description="Comment content")
    likes: int = Field(0, description="Comment likes")
    publish_time: datetime = Field(..., description="Comment publish time")
    reply_to: Optional[str] = Field(None, description="Parent comment ID if reply")
    replies: List[Dict[str, Any]] = Field(default_factory=list, description="Nested replies")


class AuthorStats(BaseModel):
    """Author statistics - only crawled when crawl_author_details=True"""

    author_id: str = Field(..., description="Author ID")
    followers: int = Field(0, description="Number of followers")
    following: int = Field(0, description="Number of following")
    total_posts: int = Field(0, description="Total number of posts")
    total_likes: int = Field(0, description="Total likes received")
    verified: bool = Field(False, description="Is verified account")
    bio: Optional[str] = Field(None, description="Author bio/description")
    location: Optional[str] = Field(None, description="Author location")
    join_date: Optional[datetime] = Field(None, description="Account creation date")

    # Platform-specific stats
    platform_stats: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific statistics")


class ExtendedContent(BaseContent):
    """
    Extended content model with optional fields
    These fields are only populated when specific flags are set
    """

    # Optional detailed information
    comment_details: Optional[List[CommentDetail]] = Field(
        None,
        description="Detailed comments - only when include_comments=True"
    )

    author_stats: Optional[AuthorStats] = Field(
        None,
        description="Author statistics - only when crawl_author_details=True"
    )

    # Additional engagement details (when available)
    share_count: Optional[int] = Field(
        None,
        description="Detailed share statistics - only when crawl_author_details=True"
    )

    # Platform-specific extended data
    platform_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific additional data"
    )


class ContentResult(BaseModel):
    """Result wrapper for content crawling"""

    platform: str
    task_id: str
    total_items: int
    success: bool
    items: List[ExtendedContent]
    error: Optional[str] = None
    crawl_config: Dict[str, Any] = Field(default_factory=dict)

    # Statistics summary
    stats: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_engagement": 0,
            "crawl_duration": 0
        }
    )


# Database table schema mapping
CONTENT_TABLE_COLUMNS = [
    "id",
    "platform",
    "title",
    "content",
    "url",
    "likes",
    "collects",
    "comments",
    "shares",
    "views",
    "author",
    "author_id",
    "author_avatar",
    "publish_time",
    "tags",
    "images",
    "videos",
    "crawl_time",
    "task_id"
]

# Optional columns (stored in separate tables or JSONB)
COMMENT_TABLE_COLUMNS = [
    "content_id",
    "comment_id",
    "author",
    "author_id",
    "content",
    "likes",
    "publish_time",
    "reply_to"
]

AUTHOR_STATS_TABLE_COLUMNS = [
    "author_id",
    "platform",
    "followers",
    "following",
    "total_posts",
    "total_likes",
    "verified",
    "bio",
    "location",
    "join_date",
    "updated_at"
]