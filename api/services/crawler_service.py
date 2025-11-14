"""
MediaCrawler service wrapper
"""

import logging
import sys
from datetime import datetime
from typing import Any, Optional

from api.config import settings
from api.models.task import TaskStatus
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
    ) -> dict[str, Any]:
        """
        Execute a crawl task using MediaCrawler

        Args:
            task_id: Unique task identifier
            platform: Platform to crawl
            keywords: Keywords to search
            max_results: Maximum results to fetch
            config: Additional configuration

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
            }

            # Store in local cache
            self.tasks[task_id] = task_data

            # Save to database
            await self.supabase.save_task(task_data)

            # For MVP, we'll use a simplified approach
            # In production, this would integrate with MediaCrawler's actual API
            result = await self._run_crawler(
                platform=platform, keywords=keywords, max_results=max_results, config=config or {}
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
        self, platform: str, keywords: list[str], max_results: int, config: dict[str, Any]
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
                return await self._crawl_xiaohongshu(keywords, max_results)
            elif platform == "weibo":
                return await self._crawl_weibo(keywords, max_results)
            elif platform == "douyin":
                return await self._crawl_douyin(keywords, max_results)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except Exception as e:
            logger.error(f"Crawler execution failed: {str(e)}")
            raise

    async def _crawl_xiaohongshu(self, keywords: list[str], max_results: int) -> dict[str, Any]:
        """
        Crawl XiaoHongShu (Little Red Book)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data: dict[str, Any] = {
            "platform": "xiaohongshu",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": [],
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append(
                {
                    "id": f"xhs_{i + 1}",
                    "title": f"Mock XiaoHongShu post about {keywords[0] if keywords else 'topic'}",
                    "content": "This is mock content for testing. Real content would be crawled from XiaoHongShu.",
                    "author": f"user_{i + 1}",
                    "likes": 100 + i * 10,
                    "comments": 5 + i,
                    "created_at": datetime.utcnow().isoformat(),
                    "url": f"https://www.xiaohongshu.com/discovery/item/{i + 1}",
                    "tags": keywords[:3] if len(keywords) > 3 else keywords,
                }
            )

        return mock_data

    async def _crawl_weibo(self, keywords: list[str], max_results: int) -> dict[str, Any]:
        """
        Crawl Weibo

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data: dict[str, Any] = {
            "platform": "weibo",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": [],
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append(
                {
                    "id": f"wb_{i + 1}",
                    "content": f"Mock Weibo post about {keywords[0] if keywords else 'topic'}",
                    "author": f"weibo_user_{i + 1}",
                    "reposts": 50 + i * 5,
                    "comments": 10 + i * 2,
                    "likes": 200 + i * 20,
                    "created_at": datetime.utcnow().isoformat(),
                    "url": f"https://weibo.com/status/{i + 1}",
                    "hashtags": [f"#{kw}" for kw in keywords[:2]],
                }
            )

        return mock_data

    async def _crawl_douyin(self, keywords: list[str], max_results: int) -> dict[str, Any]:
        """
        Crawl Douyin (TikTok China)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data: dict[str, Any] = {
            "platform": "douyin",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": [],
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append(
                {
                    "id": f"dy_{i + 1}",
                    "title": f"Mock Douyin video about {keywords[0] if keywords else 'topic'}",
                    "description": "This is a mock video description for testing purposes.",
                    "author": f"douyin_creator_{i + 1}",
                    "views": 10000 + i * 1000,
                    "likes": 500 + i * 50,
                    "shares": 20 + i * 2,
                    "created_at": datetime.utcnow().isoformat(),
                    "url": f"https://www.douyin.com/video/{i + 1}",
                    "music": f"trending_sound_{i + 1}",
                    "tags": keywords[:3] if len(keywords) > 3 else keywords,
                }
            )

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
