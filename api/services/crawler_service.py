"""
MediaCrawler service wrapper
"""

import logging
import sys
from datetime import datetime, timedelta
import random
from typing import Any, Optional

from api.config import settings
from api.models.task import TaskStatus
from api.models.crawler_config import CrawlConfig, SortBy
from api.services.mediacrawler_adapter import get_mediacrawler_adapter
from api.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

# Add MediaCrawler to Python path
sys.path.insert(0, settings.MEDIACRAWLER_PATH)


class CrawlerService:
    """
    Service for managing MediaCrawler operations
    """

    def __init__(self):
        self.tasks: dict[str, dict[str, Any]] = {}  # Local cache
        self.crawler_path = settings.MEDIACRAWLER_PATH
        self.use_real_crawler = settings.USE_REAL_CRAWLER or settings.is_production
        self.adapter: Optional[Any] = None

        # Initialize Supabase service
        self.supabase = SupabaseService()

        # Initialize MediaCrawler adapter if enabled
        if self.use_real_crawler:
            try:
                self.adapter = get_mediacrawler_adapter()
                logger.info("MediaCrawler adapter initialized for real crawling")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaCrawler adapter: {e}")
                self.use_real_crawler = False

    async def execute_crawl(
        self,
        task_id: str,
        platform: str,
        keywords: list[str],
        max_results: int = 100,
        config: dict[str, Any] | None = None,
        crawl_config: CrawlConfig | None = None,
    ) -> dict[str, Any]:
        """
        Execute a crawl task using MediaCrawler

        Args:
            task_id: Unique task identifier
            platform: Platform to crawl
            keywords: Keywords to search
            max_results: Maximum results to fetch
            config: Additional configuration
            crawl_config: Crawl configuration with time range, sorting, and fields

        Returns:
            Task result dictionary
        """
        try:
            # Initialize task info
            task_data = {
                "id": task_id,
                "status": TaskStatus.RUNNING,
                "progress": 0,
                "message": f"Starting crawl for {platform}",
                "started_at": datetime.utcnow().isoformat(),
                "platform": platform,
                "platforms": [platform],  # For Supabase compatibility
                "keywords": keywords,
                "config": config or {},
                "crawl_config": crawl_config.model_dump() if crawl_config else None,
            }

            # Store in local cache
            self.tasks[task_id] = task_data

            # Save to database
            await self.supabase.save_task(task_data)

            # For MVP, we'll use a simplified approach
            # In production, this would integrate with MediaCrawler's actual API
            result = await self._run_crawler(
                platform=platform,
                keywords=keywords,
                max_results=crawl_config.limit if crawl_config else max_results,
                config=config or {},
                crawl_config=crawl_config
            )

            # Update task status
            self.tasks[task_id].update(
                {
                    "status": TaskStatus.COMPLETED,
                    "progress": 100,
                    "message": "Crawl completed successfully",
                    "completed_at": datetime.utcnow().isoformat(),
                    "result": result,
                }
            )

            # Update in database
            await self.supabase.update_task_status(
                task_id, TaskStatus.COMPLETED, progress=100, error=None
            )

            # Save results to database
            await self.supabase.save_result({
                "task_id": task_id,
                "platform": platform,
                "raw_data": result,
                "processed_data": {},
                "insights": {},
                "item_count": result.get("total_results", len(result.get("items", []))),
                "success": True,
            })

            return result

        except Exception as e:
            logger.error(f"Crawl task {task_id} failed: {str(e)}")
            self.tasks[task_id].update(
                {
                    "status": TaskStatus.FAILED,
                    "error": str(e),
                    "message": f"Crawl failed: {str(e)}",
                    "completed_at": datetime.utcnow().isoformat(),
                }
            )

            # Update in database
            await self.supabase.update_task_status(
                task_id, TaskStatus.FAILED, progress=None, error=f"Crawl failed: {str(e)}"
            )

            raise

    async def _run_crawler(
        self,
        platform: str,
        keywords: list[str],
        max_results: int,
        config: dict[str, Any],
        crawl_config: CrawlConfig | None = None
    ) -> dict[str, Any]:
        """
        Run MediaCrawler for specific platform

        Uses real MediaCrawler in production, mock data in development.
        """
        try:
            # Use real MediaCrawler adapter if available and in production
            if self.use_real_crawler and self.adapter:
                logger.info(f"Using real MediaCrawler for {platform}")
                try:
                    result = await self.adapter.crawl_by_keyword(
                        platform=platform,
                        keywords=keywords,
                        max_results=max_results,
                        config=config,
                    )
                    return result
                except Exception as e:
                    logger.error(f"Real crawler failed, falling back to mock: {e}")
                    # Fall back to mock data if real crawler fails

            # Use mock data for development or if real crawler fails
            logger.info(f"Using mock data for {platform}")
            if platform == "xiaohongshu":
                return await self._crawl_xiaohongshu(keywords, max_results, crawl_config)
            elif platform == "weibo":
                return await self._crawl_weibo(keywords, max_results, crawl_config)
            elif platform == "douyin":
                return await self._crawl_douyin(keywords, max_results, crawl_config)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except Exception as e:
            logger.error(f"Crawler execution failed: {str(e)}")
            raise

    def _generate_mock_publish_time(self, days_ago: int) -> datetime:
        """Generate a publish time for mock data"""
        base_time = datetime.utcnow()
        # Add some randomness within the day
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        return base_time - timedelta(days=days_ago, hours=hours_offset, minutes=minutes_offset)

    def _filter_by_time_range(self, items: list[dict], crawl_config: CrawlConfig | None) -> list[dict]:
        """Filter items by time range configuration"""
        if not crawl_config or not crawl_config.time_range:
            return items

        time_config = crawl_config.get_time_range_config()
        start_date, end_date = time_config.get_date_range()

        if start_date is None and end_date is None:
            return items

        filtered = []
        for item in items:
            publish_time = datetime.fromisoformat(item.get("publish_time", item.get("created_at")))
            if start_date and publish_time < start_date:
                continue
            if end_date and publish_time > end_date:
                continue
            filtered.append(item)

        return filtered

    def _sort_items(self, items: list[dict], crawl_config: CrawlConfig | None) -> list[dict]:
        """Sort items according to crawl configuration"""
        if not crawl_config:
            return items

        sort_by = crawl_config.sort_by
        reverse = crawl_config.sort_desc

        if sort_by == SortBy.HOT:
            # Sort by total engagement (likes + comments + shares)
            return sorted(
                items,
                key=lambda x: x.get("likes", 0) + x.get("comments", 0) + x.get("shares", 0) + x.get("collects", 0),
                reverse=reverse
            )
        elif sort_by == SortBy.RECENT:
            # Sort by publish time
            return sorted(
                items,
                key=lambda x: datetime.fromisoformat(x.get("publish_time", x.get("created_at"))),
                reverse=reverse
            )
        elif sort_by == SortBy.TRENDING:
            # Sort by engagement velocity (engagement per day since published)
            now = datetime.utcnow()
            return sorted(
                items,
                key=lambda x: (x.get("likes", 0) + x.get("comments", 0)) / max(
                    1, (now - datetime.fromisoformat(x.get("publish_time", x.get("created_at")))).days + 1
                ),
                reverse=reverse
            )
        elif sort_by == SortBy.LIKES:
            return sorted(items, key=lambda x: x.get("likes", 0), reverse=reverse)
        elif sort_by == SortBy.COMMENTS:
            return sorted(items, key=lambda x: x.get("comments", 0), reverse=reverse)
        elif sort_by == SortBy.SHARES:
            return sorted(items, key=lambda x: x.get("shares", 0) + x.get("reposts", 0), reverse=reverse)
        else:
            return items

    def _add_extended_data(self, item: dict, crawl_config: CrawlConfig | None) -> dict:
        """Add extended data to item based on crawl configuration"""
        if not crawl_config:
            return item

        # Add comment details if requested
        if crawl_config.include_comments:
            item["comment_details"] = self._generate_mock_comments(
                item.get("id"),
                min(crawl_config.max_comments_per_post, item.get("comments", 0))
            )

        # Add author statistics if requested
        if crawl_config.crawl_author_details:
            item["author_stats"] = self._generate_mock_author_stats(
                item.get("author_id", item.get("author"))
            )
            # Add detailed share count
            item["share_count"] = item.get("shares", 0) + random.randint(10, 100)

        return item

    def _generate_mock_comments(self, content_id: str, count: int) -> list[dict]:
        """Generate mock comment details"""
        comments = []
        for i in range(min(count, 50)):  # Limit to 50 comments
            comment = {
                "comment_id": f"comment_{content_id}_{i}",
                "author": f"commenter_{random.randint(1, 100)}",
                "author_id": f"user_{random.randint(1, 100)}",
                "content": f"This is comment {i+1} on the post. Great content!",
                "likes": random.randint(0, 100),
                "publish_time": (datetime.utcnow() - timedelta(hours=random.randint(1, 72))).isoformat(),
                "reply_to": None if i == 0 else f"comment_{content_id}_{random.randint(0, i-1)}" if random.random() > 0.7 else None,
                "replies": []
            }
            comments.append(comment)
        return comments

    def _generate_mock_author_stats(self, author_id: str) -> dict:
        """Generate mock author statistics"""
        return {
            "author_id": author_id,
            "followers": random.randint(100, 1000000),
            "following": random.randint(10, 5000),
            "total_posts": random.randint(10, 1000),
            "total_likes": random.randint(1000, 10000000),
            "verified": random.random() > 0.8,
            "bio": f"Content creator specializing in lifestyle and technology",
            "location": random.choice(["北京", "上海", "深圳", "广州", "成都", "杭州"]),
            "join_date": (datetime.utcnow() - timedelta(days=random.randint(30, 1000))).isoformat(),
            "platform_stats": {
                "avg_engagement": random.randint(100, 10000),
                "post_frequency": f"{random.randint(1, 10)} posts/week"
            }
        }

    async def _crawl_xiaohongshu(self, keywords: list[str], max_results: int, crawl_config: CrawlConfig | None = None) -> dict[str, Any]:
        """
        Crawl XiaoHongShu (Little Red Book)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Generate more mock items than needed for filtering
        num_items = min(max_results * 3, 150)  # Generate extra for filtering

        items = []
        for i in range(num_items):
            # Distribute publish times across different ranges
            days_ago = random.randint(0, 90)  # Posts from last 90 days
            publish_time = self._generate_mock_publish_time(days_ago)

            # Vary engagement based on age (newer posts might have less engagement)
            age_factor = max(0.3, 1 - (days_ago / 90))

            item = {
                "id": f"xhs_{i + 1}",
                "title": f"Mock XiaoHongShu post about {keywords[0] if keywords else 'topic'} #{i+1}",
                "content": f"This is mock content for testing. Real content would be crawled from XiaoHongShu. Keywords: {', '.join(keywords)}",
                "author": f"user_{random.randint(1, 20)}",
                "author_id": f"xhs_user_{random.randint(1, 20)}",
                "likes": int(random.randint(50, 5000) * age_factor),
                "comments": int(random.randint(1, 500) * age_factor),
                "collects": int(random.randint(10, 1000) * age_factor),
                "shares": int(random.randint(1, 100) * age_factor),
                "views": random.randint(1000, 50000),
                "publish_time": publish_time.isoformat(),
                "created_at": publish_time.isoformat(),  # Fallback
                "url": f"https://www.xiaohongshu.com/discovery/item/{i + 1}",
                "tags": keywords[:3] if len(keywords) > 3 else keywords,
                "platform": "xiaohongshu"
            }
            items.append(item)

        # Apply filters and sorting
        items = self._filter_by_time_range(items, crawl_config)
        items = self._sort_items(items, crawl_config)

        # Apply pagination
        if crawl_config:
            offset = crawl_config.offset
            limit = crawl_config.limit
            items = items[offset:offset + limit]
        else:
            items = items[:max_results]

        # Add extended data if requested
        if crawl_config:
            items = [self._add_extended_data(item, crawl_config) for item in items]

        mock_data: dict[str, Any] = {
            "platform": "xiaohongshu",
            "keywords": keywords,
            "total_results": len(items),
            "items": items,
            "config": crawl_config.model_dump() if crawl_config else None
        }

        return mock_data

    async def _crawl_weibo(self, keywords: list[str], max_results: int, crawl_config: CrawlConfig | None = None) -> dict[str, Any]:
        """
        Crawl Weibo

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Generate more mock items than needed for filtering
        num_items = min(max_results * 3, 150)

        items = []
        for i in range(num_items):
            days_ago = random.randint(0, 90)
            publish_time = self._generate_mock_publish_time(days_ago)
            age_factor = max(0.3, 1 - (days_ago / 90))

            item = {
                "id": f"wb_{i + 1}",
                "content": f"Mock Weibo post about {keywords[0] if keywords else 'topic'} #{i+1}. Keywords: {', '.join(keywords)}",
                "title": f"Weibo: {keywords[0] if keywords else 'topic'}",  # Weibo doesn't have titles, but add for consistency
                "author": f"weibo_user_{random.randint(1, 20)}",
                "author_id": f"wb_user_{random.randint(1, 20)}",
                "reposts": int(random.randint(10, 2000) * age_factor),
                "shares": int(random.randint(10, 2000) * age_factor),  # Same as reposts for Weibo
                "comments": int(random.randint(5, 1000) * age_factor),
                "likes": int(random.randint(50, 10000) * age_factor),
                "views": random.randint(5000, 100000),
                "publish_time": publish_time.isoformat(),
                "created_at": publish_time.isoformat(),
                "url": f"https://weibo.com/status/{i + 1}",
                "hashtags": [f"#{kw}" for kw in keywords[:2]],
                "tags": keywords[:3] if len(keywords) > 3 else keywords,
                "platform": "weibo"
            }
            items.append(item)

        # Apply filters and sorting
        items = self._filter_by_time_range(items, crawl_config)
        items = self._sort_items(items, crawl_config)

        # Apply pagination
        if crawl_config:
            offset = crawl_config.offset
            limit = crawl_config.limit
            items = items[offset:offset + limit]
        else:
            items = items[:max_results]

        # Add extended data if requested
        if crawl_config:
            items = [self._add_extended_data(item, crawl_config) for item in items]

        mock_data: dict[str, Any] = {
            "platform": "weibo",
            "keywords": keywords,
            "total_results": len(items),
            "items": items,
            "config": crawl_config.model_dump() if crawl_config else None
        }

        return mock_data

    async def _crawl_douyin(self, keywords: list[str], max_results: int, crawl_config: CrawlConfig | None = None) -> dict[str, Any]:
        """
        Crawl Douyin (TikTok China)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Generate more mock items than needed for filtering
        num_items = min(max_results * 3, 150)

        items = []
        for i in range(num_items):
            days_ago = random.randint(0, 90)
            publish_time = self._generate_mock_publish_time(days_ago)
            age_factor = max(0.3, 1 - (days_ago / 90))

            item = {
                "id": f"dy_{i + 1}",
                "title": f"Mock Douyin video about {keywords[0] if keywords else 'topic'} #{i+1}",
                "content": f"This is a mock video description for testing. Keywords: {', '.join(keywords)}",
                "description": f"Video description with keywords: {', '.join(keywords)}",
                "author": f"douyin_creator_{random.randint(1, 20)}",
                "author_id": f"dy_creator_{random.randint(1, 20)}",
                "views": int(random.randint(1000, 500000) * age_factor),
                "likes": int(random.randint(100, 50000) * age_factor),
                "shares": int(random.randint(10, 5000) * age_factor),
                "comments": int(random.randint(5, 2000) * age_factor),
                "collects": int(random.randint(10, 3000) * age_factor),
                "publish_time": publish_time.isoformat(),
                "created_at": publish_time.isoformat(),
                "url": f"https://www.douyin.com/video/{i + 1}",
                "music": f"trending_sound_{random.randint(1, 10)}",
                "tags": keywords[:3] if len(keywords) > 3 else keywords,
                "platform": "douyin"
            }
            items.append(item)

        # Apply filters and sorting
        items = self._filter_by_time_range(items, crawl_config)
        items = self._sort_items(items, crawl_config)

        # Apply pagination
        if crawl_config:
            offset = crawl_config.offset
            limit = crawl_config.limit
            items = items[offset:offset + limit]
        else:
            items = items[:max_results]

        # Add extended data if requested
        if crawl_config:
            items = [self._add_extended_data(item, crawl_config) for item in items]

        mock_data: dict[str, Any] = {
            "platform": "douyin",
            "keywords": keywords,
            "total_results": len(items),
            "items": items,
            "config": crawl_config.model_dump() if crawl_config else None
        }

        return mock_data

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task status and results

        Args:
            task_id: Task identifier

        Returns:
            Task information dictionary or None if not found
        """
        # Try to get from local cache first
        if task_id in self.tasks:
            return self.tasks[task_id]

        # Try to get from database
        task_data = await self.supabase.get_task(task_id)
        if task_data:
            # Store in local cache
            self.tasks[task_id] = task_data
            return task_data

        return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        # Get task from cache or database
        task = await self.get_task_status(task_id)
        if task and task.get("status") == TaskStatus.RUNNING:
            # Update local cache
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = TaskStatus.CANCELLED
                self.tasks[task_id]["message"] = "Task cancelled by user"
                self.tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()

            # Update database
            await self.supabase.update_task_status(
                task_id, TaskStatus.CANCELLED, progress=None, error="Task cancelled by user"
            )
            return True
        return False

    def is_platform_enabled(self, platform: str) -> bool:
        """
        Check if a platform is enabled

        Args:
            platform: Platform name

        Returns:
            True if platform is enabled
        """
        # For MVP, only XiaoHongShu is fully enabled
        return platform in ["xiaohongshu", "weibo", "douyin"]
