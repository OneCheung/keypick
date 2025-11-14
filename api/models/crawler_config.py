"""
Crawler configuration models for time range, sorting, and field selection
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
import re


class TimeRange(str, Enum):
    """Predefined time range options"""

    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    ALL = "all"
    CUSTOM = "custom"


class SortBy(str, Enum):
    """Sorting options for crawled data"""

    HOT = "hot"  # Sort by engagement metrics (likes + comments + shares)
    RECENT = "recent"  # Sort by publish time (newest first)
    TRENDING = "trending"  # Sort by recent engagement velocity
    POPULAR = "popular"  # Sort by total views/impressions
    RELEVANT = "relevant"  # Sort by keyword relevance
    COMMENTS = "comments"  # Sort by comment count
    LIKES = "likes"  # Sort by like count
    SHARES = "shares"  # Sort by share/repost count


class CrawlerFields(str, Enum):
    """Standardized field names across platforms"""

    # Basic content fields
    ID = "id"
    TITLE = "title"
    CONTENT = "content"
    DESCRIPTION = "description"
    URL = "url"

    # Author information
    AUTHOR = "author"
    AUTHOR_ID = "author_id"
    AUTHOR_NAME = "author_name"
    AUTHOR_AVATAR = "author_avatar"
    AUTHOR_URL = "author_url"

    # Engagement metrics
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    VIEWS = "views"
    COLLECTS = "collects"
    BOOKMARKS = "bookmarks"

    # Time information
    PUBLISH_TIME = "publish_time"
    UPDATE_TIME = "update_time"
    CRAWL_TIME = "crawl_time"

    # Content metadata
    TAGS = "tags"
    HASHTAGS = "hashtags"
    MENTIONS = "mentions"
    LOCATION = "location"
    LANGUAGE = "language"

    # Media information
    IMAGES = "images"
    VIDEOS = "videos"
    MEDIA_COUNT = "media_count"

    # Platform specific
    PLATFORM = "platform"
    POST_TYPE = "post_type"
    IS_ORIGINAL = "is_original"

    # Additional metadata
    SENTIMENT = "sentiment"
    KEYWORDS = "keywords"
    CATEGORIES = "categories"


class TimeRangeConfig(BaseModel):
    """Configuration for time-based data filtering"""

    range_type: TimeRange = Field(default=TimeRange.SEVEN_DAYS, description="Time range type")
    start_date: Optional[datetime] = Field(default=None, description="Custom start date (for CUSTOM range)")
    end_date: Optional[datetime] = Field(default=None, description="Custom end date (for CUSTOM range)")
    timezone: str = Field(default="UTC", description="Timezone for date calculations")

    @field_validator('start_date', 'end_date')
    def validate_dates(cls, v, values):
        """Validate custom date range"""
        if values.get('range_type') == TimeRange.CUSTOM and v is None:
            raise ValueError("start_date and end_date are required for CUSTOM range")
        return v

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Calculate actual date range based on configuration"""
        if self.range_type == TimeRange.ALL:
            return None, None

        if self.range_type == TimeRange.CUSTOM:
            return self.start_date, self.end_date

        end = datetime.utcnow()
        range_map = {
            TimeRange.ONE_DAY: timedelta(days=1),
            TimeRange.THREE_DAYS: timedelta(days=3),
            TimeRange.SEVEN_DAYS: timedelta(days=7),
            TimeRange.THIRTY_DAYS: timedelta(days=30),
            TimeRange.NINETY_DAYS: timedelta(days=90),
            TimeRange.SIX_MONTHS: timedelta(days=180),
            TimeRange.ONE_YEAR: timedelta(days=365),
        }

        delta = range_map.get(self.range_type)
        if delta:
            start = end - delta
            return start, end

        return None, None

    @classmethod
    def parse_range_string(cls, range_string: str) -> "TimeRangeConfig":
        """Parse a range string like '7d' or '2024-01-01,2024-12-31' """
        # Check if it's a predefined range
        for time_range in TimeRange:
            if range_string.lower() == time_range.value:
                return cls(range_type=time_range)

        # Check if it's a date range (start,end)
        if ',' in range_string:
            parts = range_string.split(',')
            if len(parts) == 2:
                try:
                    start = datetime.fromisoformat(parts[0].strip())
                    end = datetime.fromisoformat(parts[1].strip())
                    return cls(
                        range_type=TimeRange.CUSTOM,
                        start_date=start,
                        end_date=end
                    )
                except ValueError:
                    pass

        # Check if it's a relative range like "7d", "30d"
        match = re.match(r'^(\d+)([dwmy])$', range_string.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            unit_map = {
                'd': TimeRange.ONE_DAY if value == 1 else TimeRange.SEVEN_DAYS if value == 7 else TimeRange.THIRTY_DAYS if value == 30 else TimeRange.NINETY_DAYS if value == 90 else None,
                'w': TimeRange.SEVEN_DAYS if value == 1 else None,
                'm': TimeRange.THIRTY_DAYS if value == 1 else TimeRange.SIX_MONTHS if value == 6 else None,
                'y': TimeRange.ONE_YEAR if value == 1 else None
            }

            mapped_range = unit_map.get(unit)
            if mapped_range:
                return cls(range_type=mapped_range)

        # Default to 7 days if parsing fails
        return cls(range_type=TimeRange.SEVEN_DAYS)


class CrawlConfig(BaseModel):
    """
    Complete crawl configuration with all parameters

    Note: Basic fields (title, content, likes, collects, comments, publish_time,
    author, tags, url) are ALWAYS crawled and stored as database columns.
    """

    # Time range configuration
    time_range: Optional[str] = Field(default="7d", description="Time range string (e.g., '7d', '30d', '2024-01-01,2024-12-31')")

    # Sorting configuration
    sort_by: SortBy = Field(default=SortBy.HOT, description="How to sort the results")
    sort_desc: bool = Field(default=True, description="Sort in descending order")

    # Extended crawling options (these control additional data collection)
    include_comments: bool = Field(
        default=False,
        description="Crawl comment details (comment_details field)"
    )
    crawl_author_details: bool = Field(
        default=False,
        description="Crawl author statistics (author_stats, share_count fields)"
    )

    # Comment crawling options (only used when include_comments=True)
    max_comments_per_post: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum comments to crawl per post"
    )
    include_comment_replies: bool = Field(
        default=False,
        description="Include nested comment replies"
    )

    # Pagination
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")

    # Filters
    min_likes: Optional[int] = Field(default=None, ge=0, description="Minimum number of likes")
    min_comments: Optional[int] = Field(default=None, ge=0, description="Minimum number of comments")
    author_ids: Optional[List[str]] = Field(default=None, description="Filter by specific author IDs")
    exclude_keywords: Optional[List[str]] = Field(default=None, description="Keywords to exclude")

    # Platform-specific options
    platform_config: Dict[str, Any] = Field(default={}, description="Platform-specific configuration")

    def get_time_range_config(self) -> TimeRangeConfig:
        """Get TimeRangeConfig from time_range string"""
        if self.time_range:
            return TimeRangeConfig.parse_range_string(self.time_range)
        return TimeRangeConfig()


    def to_query_params(self) -> dict:
        """Convert config to query parameters for API calls"""
        params = {
            "time_range": self.time_range,
            "sort_by": self.sort_by.value,
            "sort_desc": self.sort_desc,
            "limit": self.limit,
            "offset": self.offset,
            "include_comments": self.include_comments,
            "crawl_author_details": self.crawl_author_details,
        }

        if self.include_comments:
            params["max_comments_per_post"] = self.max_comments_per_post
            params["include_comment_replies"] = self.include_comment_replies

        if self.min_likes is not None:
            params["min_likes"] = self.min_likes

        if self.min_comments is not None:
            params["min_comments"] = self.min_comments

        if self.author_ids:
            params["author_ids"] = ",".join(self.author_ids)

        if self.exclude_keywords:
            params["exclude_keywords"] = ",".join(self.exclude_keywords)

        return params


class HistoricalDataQuery(BaseModel):
    """Query parameters for historical data retrieval"""

    # Task filters
    task_ids: Optional[List[str]] = Field(default=None, description="Filter by specific task IDs")
    platforms: Optional[List[str]] = Field(default=None, description="Filter by platforms")
    keywords: Optional[List[str]] = Field(default=None, description="Filter by keywords used in tasks")

    # Time filters
    crawled_after: Optional[datetime] = Field(default=None, description="Only data crawled after this date")
    crawled_before: Optional[datetime] = Field(default=None, description="Only data crawled before this date")
    published_after: Optional[datetime] = Field(default=None, description="Only content published after this date")
    published_before: Optional[datetime] = Field(default=None, description="Only content published before this date")

    # Content filters
    search_text: Optional[str] = Field(default=None, description="Full-text search in content")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    authors: Optional[List[str]] = Field(default=None, description="Filter by author names")

    # Engagement filters
    min_engagement: Optional[int] = Field(default=None, description="Minimum total engagement")
    max_engagement: Optional[int] = Field(default=None, description="Maximum total engagement")

    # Sorting and pagination
    sort_by: SortBy = Field(default=SortBy.RECENT, description="Sort order")
    sort_desc: bool = Field(default=True, description="Sort descending")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    # Aggregation options
    aggregate_by: Optional[str] = Field(default=None, description="Aggregate by: day, week, month, platform, author")
    include_stats: bool = Field(default=False, description="Include statistical summary")

    def to_sql_conditions(self) -> tuple[str, dict]:
        """Convert to SQL WHERE conditions and parameters"""
        conditions = []
        params = {}

        if self.task_ids:
            conditions.append("task_id = ANY(:task_ids)")
            params["task_ids"] = self.task_ids

        if self.platforms:
            conditions.append("platform = ANY(:platforms)")
            params["platforms"] = self.platforms

        if self.crawled_after:
            conditions.append("created_at >= :crawled_after")
            params["crawled_after"] = self.crawled_after

        if self.crawled_before:
            conditions.append("created_at <= :crawled_before")
            params["crawled_before"] = self.crawled_before

        if self.search_text:
            conditions.append("(raw_data->>'content' ILIKE :search_text OR raw_data->>'title' ILIKE :search_text)")
            params["search_text"] = f"%{self.search_text}%"

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params