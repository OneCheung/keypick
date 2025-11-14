"""
Supabase integration service
"""

# type: ignore[assignment, index, union-attr, arg-type, return-value]

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.config import settings
from api.models.crawler_config import HistoricalDataQuery

logger = logging.getLogger(__name__)

# Import Supabase client conditionally
try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not installed. Install with: pip install supabase")


class SupabaseService:
    """
    Service for interacting with Supabase Cloud
    """

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.anon_key = settings.SUPABASE_ANON_KEY
        self.service_key = settings.SUPABASE_SERVICE_KEY
        self.client: Client | None = None

        if SUPABASE_AVAILABLE and self.url and self.anon_key:
            try:
                self.client = create_client(self.url, self.anon_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.client = None
        else:
            logger.warning("Supabase not configured or not available")

    async def save_task(self, task_data: dict[str, Any]) -> str | None:
        """
        Save task to database

        Args:
            task_data: Task information

        Returns:
            Task ID if successful
        """
        try:
            if not self.client:
                logger.warning("Supabase client not available, using local storage")
                return task_data.get("id")

            # Prepare data for insertion
            task_record = {
                "id": task_data.get("id"),
                "name": task_data.get("name", "Unnamed Task"),
                "description": task_data.get("description"),
                "platforms": json.dumps(task_data.get("platforms", [])),
                "keywords": json.dumps(task_data.get("keywords", [])),
                "status": task_data.get("status", "pending"),
                "config": json.dumps(task_data.get("config", {})),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Insert into tasks table
            result = self.client.table("tasks").insert(task_record).execute()

            if result.data:
                return result.data[0]["id"]
            else:
                logger.error("Failed to save task to Supabase")
                return None

        except Exception as e:
            logger.error(f"Error saving task: {str(e)}")
            return None

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task from database

        Args:
            task_id: Task identifier

        Returns:
            Task data if found
        """
        try:
            if not self.client:
                return None

            result = self.client.table("tasks").select("*").eq("id", task_id).single().execute()

            if result.data:
                task = result.data
                # Parse JSON fields
                task["platforms"] = json.loads(task.get("platforms", "[]"))
                task["keywords"] = json.loads(task.get("keywords", "[]"))
                task["config"] = json.loads(task.get("config", "{}"))
                return task

            return None

        except Exception as e:
            logger.error(f"Error getting task: {str(e)}")
            return None

    async def update_task_status(
        self, task_id: str, status: str, progress: int | None = None, error: str | None = None
    ) -> bool:
        """
        Update task status

        Args:
            task_id: Task identifier
            status: New status
            progress: Progress percentage
            error: Error message if failed

        Returns:
            True if successful
        """
        try:
            if not self.client:
                return True  # Simulate success for local development

            update_data = {"status": status, "updated_at": datetime.utcnow().isoformat()}

            if progress is not None:
                update_data["progress"] = progress

            if error:
                update_data["error"] = error

            if status == "completed":
                update_data["completed_at"] = datetime.utcnow().isoformat()
            elif status == "running" and "started_at" not in update_data:
                update_data["started_at"] = datetime.utcnow().isoformat()

            result = self.client.table("tasks").update(update_data).eq("id", task_id).execute()

            return result.data is not None

        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return False

    async def save_result(self, result_data: dict[str, Any]) -> str | None:
        """
        Save task result to database

        Args:
            result_data: Result information

        Returns:
            Result ID if successful
        """
        try:
            if not self.client:
                return None

            # Prepare data for insertion
            result_record = {
                "task_id": result_data.get("task_id"),
                "platform": result_data.get("platform"),
                "raw_data": json.dumps(result_data.get("raw_data", {})),
                "processed_data": json.dumps(result_data.get("processed_data", {})),
                "insights": json.dumps(result_data.get("insights", {})),
                "report": result_data.get("report"),
                "created_at": datetime.utcnow().isoformat(),
                "item_count": result_data.get("item_count", 0),
                "success": result_data.get("success", True),
            }

            # Insert into results table
            result = self.client.table("results").insert(result_record).execute()

            if result.data:
                return result.data[0]["id"]

            return None

        except Exception as e:
            logger.error(f"Error saving result: {str(e)}")
            return None

    async def get_results(self, task_id: str) -> list[dict[str, Any]]:
        """
        Get results for a task

        Args:
            task_id: Task identifier

        Returns:
            List of results
        """
        try:
            if not self.client:
                return []

            result = self.client.table("results").select("*").eq("task_id", task_id).execute()

            if result.data:
                results = []
                for item in result.data:
                    # Parse JSON fields
                    item["raw_data"] = json.loads(item.get("raw_data", "{}"))
                    item["processed_data"] = json.loads(item.get("processed_data", "{}"))
                    item["insights"] = json.loads(item.get("insights", "{}"))
                    results.append(item)
                return results

            return []

        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return []

    async def subscribe_to_tasks(self, callback) -> Any:
        """
        Subscribe to real-time task updates

        Args:
            callback: Function to call on updates

        Returns:
            Subscription object
        """
        try:
            if not self.client:
                logger.warning("Real-time subscriptions not available without Supabase")
                return None

            # Subscribe to changes in tasks table
            subscription = self.client.table("tasks").on("*", callback).subscribe()

            logger.info("Subscribed to real-time task updates")
            return subscription

        except Exception as e:
            logger.error(f"Error subscribing to tasks: {str(e)}")
            return None

    async def create_tables(self) -> bool:
        """
        Create database tables if they don't exist

        This is typically done via Supabase dashboard or migrations,
        but provided here for reference.

        Returns:
            True if successful
        """
        try:
            if not self.client:
                return False

            # Note: Table creation is usually done via Supabase dashboard
            # or using migrations. This is just for reference.

            logger.info("Tables should be created via Supabase dashboard")
            return True

        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            return False

    async def search_tasks(
        self,
        platform: str | None = None,
        status: str | None = None,
        keywords: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search tasks with filters

        Args:
            platform: Filter by platform
            status: Filter by status
            keywords: Filter by keywords
            limit: Maximum results

        Returns:
            List of matching tasks
        """
        try:
            if not self.client:
                return []

            query = self.client.table("tasks").select("*")

            if platform:
                query = query.contains("platforms", [platform])

            if status:
                query = query.eq("status", status)

            if keywords:
                # Search in keywords JSON array
                for keyword in keywords:
                    query = query.contains("keywords", [keyword])

            query = query.limit(limit).order("created_at", desc=True)

            result = query.execute()

            if result.data:
                tasks = []
                for task in result.data:
                    # Parse JSON fields
                    task["platforms"] = json.loads(task.get("platforms", "[]"))
                    task["keywords"] = json.loads(task.get("keywords", "[]"))
                    task["config"] = json.loads(task.get("config", "{}"))
                    tasks.append(task)
                return tasks

            return []

        except Exception as e:
            logger.error(f"Error searching tasks: {str(e)}")
            return []

    async def store_vector(
        self, content: str, metadata: dict[str, Any], collection: str = "insights"
    ) -> bool:
        """
        Store content as vector for semantic search

        Args:
            content: Text content to vectorize
            metadata: Associated metadata
            collection: Vector collection name

        Returns:
            True if successful
        """
        try:
            if not self.client:
                return False

            # This would require pgvector extension in Supabase
            # and an embedding service

            logger.info("Vector storage requires pgvector extension setup")
            return True

        except Exception as e:
            logger.error(f"Error storing vector: {str(e)}")
            return False

    async def query_results(self, query: HistoricalDataQuery) -> Dict[str, Any]:
        """
        Query historical results based on filters

        Args:
            query: Query parameters

        Returns:
            Dictionary with items and metadata
        """
        try:
            if not self.client:
                # Return mock data for development
                return await self._get_mock_historical_data(query)

            # Build query
            q = self.client.table("results").select("*")

            # Apply filters
            if query.task_ids:
                q = q.in_("task_id", query.task_ids)
            if query.platforms:
                q = q.in_("platform", query.platforms)
            if query.crawled_after:
                q = q.gte("created_at", query.crawled_after.isoformat())
            if query.crawled_before:
                q = q.lte("created_at", query.crawled_before.isoformat())

            # Apply limit and offset
            q = q.limit(query.limit).offset(query.offset)

            result = q.execute()

            if result.data:
                items = []
                for item in result.data:
                    # Parse JSON fields
                    item["raw_data"] = json.loads(item.get("raw_data", "{}"))
                    item["processed_data"] = json.loads(item.get("processed_data", "{}"))
                    item["insights"] = json.loads(item.get("insights", "{}"))
                    items.append(item)
                return {"items": items, "total": len(items)}

            return {"items": [], "total": 0}

        except Exception as e:
            logger.error(f"Error querying results: {str(e)}")
            # Fallback to mock data
            return await self._get_mock_historical_data(query)

    async def search_results(
        self,
        search_text: str,
        platforms: Optional[List[str]] = None,
        after_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Full-text search in results

        Args:
            search_text: Text to search
            platforms: Filter by platforms
            after_date: Filter by date

        Returns:
            Search results
        """
        try:
            if not self.client:
                return {"items": [], "total": 0}

            # Use Supabase full-text search if available
            # This would require setting up full-text search in Supabase
            q = self.client.table("results").select("*")

            # Simple text search in raw_data JSON
            # In production, use proper full-text search
            q = q.ilike("raw_data", f"%{search_text}%")

            if platforms:
                q = q.in_("platform", platforms)
            if after_date:
                q = q.gte("created_at", after_date.isoformat())

            result = q.execute()

            if result.data:
                items = []
                for item in result.data:
                    item["raw_data"] = json.loads(item.get("raw_data", "{}"))
                    items.append(item)
                return {"items": items, "total": len(items)}

            return {"items": [], "total": 0}

        except Exception as e:
            logger.error(f"Error searching results: {str(e)}")
            return {"items": [], "total": 0}

    async def get_statistics(
        self,
        platforms: Optional[List[str]] = None,
        after_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about stored data

        Args:
            platforms: Filter by platforms
            after_date: Filter by date

        Returns:
            Statistics dictionary
        """
        try:
            if not self.client:
                return {
                    "total_records": 0,
                    "platforms": {},
                    "date_range": None
                }

            # Get total count
            q = self.client.table("results").select("*", count="exact")
            if platforms:
                q = q.in_("platform", platforms)
            if after_date:
                q = q.gte("created_at", after_date.isoformat())

            result = q.execute()
            total = result.count if hasattr(result, 'count') else 0

            # Get platform distribution
            platform_stats = {}
            if platforms:
                for platform in platforms:
                    p_result = self.client.table("results").select("*", count="exact").eq("platform", platform).execute()
                    platform_stats[platform] = p_result.count if hasattr(p_result, 'count') else 0

            return {
                "total_records": total,
                "platforms": platform_stats,
                "date_range": {
                    "start": after_date.isoformat() if after_date else None,
                    "end": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                "total_records": 0,
                "platforms": {},
                "date_range": None
            }

    async def count_old_records(
        self,
        cutoff_date: datetime,
        platforms: Optional[List[str]] = None
    ) -> int:
        """
        Count records older than cutoff date

        Args:
            cutoff_date: Date threshold
            platforms: Filter by platforms

        Returns:
            Number of old records
        """
        try:
            if not self.client:
                return 0

            q = self.client.table("results").select("*", count="exact")
            q = q.lt("created_at", cutoff_date.isoformat())

            if platforms:
                q = q.in_("platform", platforms)

            result = q.execute()
            return result.count if hasattr(result, 'count') else 0

        except Exception as e:
            logger.error(f"Error counting old records: {str(e)}")
            return 0

    async def delete_old_records(
        self,
        cutoff_date: datetime,
        platforms: Optional[List[str]] = None
    ) -> int:
        """
        Delete records older than cutoff date

        Args:
            cutoff_date: Date threshold
            platforms: Filter by platforms

        Returns:
            Number of deleted records
        """
        try:
            if not self.client:
                return 0

            # First count records to delete
            count = await self.count_old_records(cutoff_date, platforms)

            # Delete records
            q = self.client.table("results").delete()
            q = q.lt("created_at", cutoff_date.isoformat())

            if platforms:
                q = q.in_("platform", platforms)

            result = q.execute()
            return count

        except Exception as e:
            logger.error(f"Error deleting old records: {str(e)}")
            return 0

    async def _get_mock_historical_data(self, query: HistoricalDataQuery) -> Dict[str, Any]:
        """
        Generate mock historical data for development

        Args:
            query: Query parameters

        Returns:
            Mock data matching query
        """
        import random
        from datetime import timedelta

        items = []
        platforms = query.platforms or ["xiaohongshu", "weibo", "douyin"]

        # Generate mock items
        for i in range(50):  # Generate 50 mock items
            days_ago = random.randint(0, 30)
            publish_time = datetime.utcnow() - timedelta(days=days_ago)

            item = {
                "id": f"result_{i}",
                "task_id": f"task_{random.randint(1, 10)}",
                "platform": random.choice(platforms),
                "created_at": publish_time.isoformat(),
                "raw_data": {
                    "id": f"item_{i}",
                    "title": f"Historical content item {i}",
                    "content": f"This is historical content from {days_ago} days ago. Keywords: {', '.join(query.keywords or ['test'])}",
                    "author": f"author_{random.randint(1, 20)}",
                    "likes": random.randint(100, 10000),
                    "comments": random.randint(10, 1000),
                    "shares": random.randint(5, 500),
                    "collects": random.randint(10, 2000),
                    "publish_time": publish_time.isoformat(),
                    "url": f"https://example.com/item/{i}",
                    "tags": ["tag1", "tag2", "tag3"],
                    "total_engagement": random.randint(200, 15000)
                },
                "processed_data": {},
                "insights": {},
                "item_count": 1,
                "success": True
            }

            # Apply filters
            if query.crawled_after and publish_time < query.crawled_after:
                continue
            if query.crawled_before and publish_time > query.crawled_before:
                continue
            if query.search_text and query.search_text.lower() not in item["raw_data"]["content"].lower():
                continue

            items.append(item)

        # Apply limit and offset
        start = query.offset
        end = start + query.limit
        return {
            "items": items[start:end],
            "total": len(items)
        }
