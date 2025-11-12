"""
MediaCrawler service wrapper
"""

import os
import sys
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from api.config import settings
from api.models.task import TaskStatus

logger = logging.getLogger(__name__)

# Add MediaCrawler to Python path
sys.path.insert(0, settings.MEDIACRAWLER_PATH)


class CrawlerService:
    """
    Service for managing MediaCrawler operations
    """

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.crawler_path = settings.MEDIACRAWLER_PATH

    async def execute_crawl(
        self,
        task_id: str,
        platform: str,
        keywords: List[str],
        max_results: int = 100,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
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
            self.tasks[task_id] = {
                "status": TaskStatus.RUNNING,
                "progress": 0,
                "message": f"Starting crawl for {platform}",
                "started_at": datetime.utcnow().isoformat(),
                "platform": platform,
                "keywords": keywords
            }

            # For MVP, we'll use a simplified approach
            # In production, this would integrate with MediaCrawler's actual API
            result = await self._run_crawler(
                platform=platform,
                keywords=keywords,
                max_results=max_results,
                config=config or {}
            )

            # Update task status
            self.tasks[task_id].update({
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "message": "Crawl completed successfully",
                "completed_at": datetime.utcnow().isoformat(),
                "result": result
            })

            return result

        except Exception as e:
            logger.error(f"Crawl task {task_id} failed: {str(e)}")
            self.tasks[task_id].update({
                "status": TaskStatus.FAILED,
                "error": str(e),
                "message": f"Crawl failed: {str(e)}",
                "completed_at": datetime.utcnow().isoformat()
            })
            raise

    async def _run_crawler(
        self,
        platform: str,
        keywords: List[str],
        max_results: int,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run MediaCrawler for specific platform

        This is a simplified implementation for MVP.
        In production, this would properly integrate with MediaCrawler.
        """
        try:
            # For MVP, return mock data
            # TODO: Integrate with actual MediaCrawler
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

    async def _crawl_xiaohongshu(
        self,
        keywords: List[str],
        max_results: int
    ) -> Dict[str, Any]:
        """
        Crawl XiaoHongShu (Little Red Book)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data = {
            "platform": "xiaohongshu",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": []
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append({
                "id": f"xhs_{i+1}",
                "title": f"Mock XiaoHongShu post about {keywords[0] if keywords else 'topic'}",
                "content": f"This is mock content for testing. Real content would be crawled from XiaoHongShu.",
                "author": f"user_{i+1}",
                "likes": 100 + i * 10,
                "comments": 5 + i,
                "created_at": datetime.utcnow().isoformat(),
                "url": f"https://www.xiaohongshu.com/discovery/item/{i+1}",
                "tags": keywords[:3] if len(keywords) > 3 else keywords
            })

        return mock_data

    async def _crawl_weibo(
        self,
        keywords: List[str],
        max_results: int
    ) -> Dict[str, Any]:
        """
        Crawl Weibo

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data = {
            "platform": "weibo",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": []
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append({
                "id": f"wb_{i+1}",
                "content": f"Mock Weibo post about {keywords[0] if keywords else 'topic'}",
                "author": f"weibo_user_{i+1}",
                "reposts": 50 + i * 5,
                "comments": 10 + i * 2,
                "likes": 200 + i * 20,
                "created_at": datetime.utcnow().isoformat(),
                "url": f"https://weibo.com/status/{i+1}",
                "hashtags": [f"#{kw}" for kw in keywords[:2]]
            })

        return mock_data

    async def _crawl_douyin(
        self,
        keywords: List[str],
        max_results: int
    ) -> Dict[str, Any]:
        """
        Crawl Douyin (TikTok China)

        For MVP, returns mock data. Will be replaced with actual MediaCrawler integration.
        """
        # Mock implementation for MVP
        mock_data = {
            "platform": "douyin",
            "keywords": keywords,
            "total_results": min(max_results, 50),
            "items": []
        }

        # Generate mock items
        for i in range(min(max_results, 10)):
            mock_data["items"].append({
                "id": f"dy_{i+1}",
                "title": f"Mock Douyin video about {keywords[0] if keywords else 'topic'}",
                "description": f"This is a mock video description for testing purposes.",
                "author": f"douyin_creator_{i+1}",
                "views": 10000 + i * 1000,
                "likes": 500 + i * 50,
                "shares": 20 + i * 2,
                "created_at": datetime.utcnow().isoformat(),
                "url": f"https://www.douyin.com/video/{i+1}",
                "music": f"trending_sound_{i+1}",
                "tags": keywords[:3] if len(keywords) > 3 else keywords
            })

        return mock_data

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status and results

        Args:
            task_id: Task identifier

        Returns:
            Task information dictionary or None if not found
        """
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task["status"] == TaskStatus.RUNNING:
                task["status"] = TaskStatus.CANCELLED
                task["message"] = "Task cancelled by user"
                task["completed_at"] = datetime.utcnow().isoformat()
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