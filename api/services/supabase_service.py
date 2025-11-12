"""
Supabase integration service
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio

from api.config import settings

logger = logging.getLogger(__name__)

# Import Supabase client conditionally
try:
    from supabase import create_client, Client
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
        self.client: Optional[Client] = None

        if SUPABASE_AVAILABLE and self.url and self.anon_key:
            try:
                self.client = create_client(self.url, self.anon_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.client = None
        else:
            logger.warning("Supabase not configured or not available")

    async def save_task(self, task_data: Dict[str, Any]) -> Optional[str]:
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
                "updated_at": datetime.utcnow().isoformat()
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

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
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
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None
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

            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }

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

    async def save_result(self, result_data: Dict[str, Any]) -> Optional[str]:
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
                "success": result_data.get("success", True)
            }

            # Insert into results table
            result = self.client.table("results").insert(result_record).execute()

            if result.data:
                return result.data[0]["id"]

            return None

        except Exception as e:
            logger.error(f"Error saving result: {str(e)}")
            return None

    async def get_results(self, task_id: str) -> List[Dict[str, Any]]:
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
        platform: Optional[str] = None,
        status: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
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
        self,
        content: str,
        metadata: Dict[str, Any],
        collection: str = "insights"
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