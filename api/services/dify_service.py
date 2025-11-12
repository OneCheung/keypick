"""
Dify integration service
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx

from api.config import settings
from api.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)


class DifyService:
    """
    Service for integrating with Dify Cloud
    """

    def __init__(self):
        # KeyPick 自己的 API Keys 用于验证
        self.keypick_api_keys = settings.get_keypick_api_keys()

        # Dify 应用的 Keys（如果需要主动调用）
        self.dify_api_url = settings.DIFY_API_URL
        self.dify_crawler_key = settings.DIFY_CRAWLER_APP_KEY
        self.dify_report_key = settings.DIFY_REPORT_APP_KEY

        self.crawler_service = CrawlerService()
        self.tasks = {}

    def validate_auth(self, authorization: str | None) -> bool:
        """
        验证来自 Dify 的请求（使用 KeyPick 自己的 API Key）

        Args:
            authorization: Authorization header value

        Returns:
            True if authorized
        """
        # 开发环境可以跳过验证
        if settings.is_development and not self.keypick_api_keys:
            return True

        if not authorization:
            return False

        # 获取 token
        token = authorization
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")

        # 验证是否是有效的 KeyPick API Key
        return token in self.keypick_api_keys

    async def start_crawl_task(self, platform: str, keywords: list[str], max_results: int) -> str:
        """
        Start an async crawl task

        Args:
            platform: Platform to crawl
            keywords: Search keywords
            max_results: Maximum results

        Returns:
            Task ID
        """
        try:
            task_id = str(uuid.uuid4())

            # Start crawler task
            await self.crawler_service.execute_crawl(
                task_id=task_id, platform=platform, keywords=keywords, max_results=max_results
            )

            # Store task info
            self.tasks[task_id] = {
                "status": "processing",
                "started_at": datetime.utcnow().isoformat(),
                "platform": platform,
                "keywords": keywords,
            }

            return task_id

        except Exception as e:
            logger.error(f"Failed to start crawl task: {str(e)}")
            raise

    async def crawl_sync(
        self, platform: str, keywords: list[str], max_results: int
    ) -> dict[str, Any]:
        """
        Execute synchronous crawl

        Args:
            platform: Platform to crawl
            keywords: Search keywords
            max_results: Maximum results

        Returns:
            Crawl results
        """
        try:
            task_id = str(uuid.uuid4())

            # Execute crawl synchronously
            result = await self.crawler_service.execute_crawl(
                task_id=task_id, platform=platform, keywords=keywords, max_results=max_results
            )

            # Format for Dify
            return self._format_for_dify(result)

        except Exception as e:
            logger.error(f"Sync crawl failed: {str(e)}")
            raise

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task status

        Args:
            task_id: Task identifier

        Returns:
            Task status dictionary
        """
        # Check crawler service for task
        task_info = await self.crawler_service.get_task_status(task_id)

        if task_info:
            return {
                "status": task_info.get("status"),
                "progress": task_info.get("progress", 0),
                "result": (
                    self._format_for_dify(task_info.get("result"))
                    if task_info.get("result")
                    else None
                ),
                "error": task_info.get("error"),
            }

        return None

    async def process_webhook(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Process webhook from Dify

        Args:
            event: Webhook event data

        Returns:
            Processing result
        """
        try:
            event_type = event.get("type")
            event_data = event.get("data", {})

            logger.info(f"Processing Dify webhook: {event_type}")

            if event_type == "workflow.completed":
                # Handle workflow completion
                return await self._handle_workflow_completed(event_data)
            elif event_type == "workflow.failed":
                # Handle workflow failure
                return await self._handle_workflow_failed(event_data)
            elif event_type == "agent.message":
                # Handle agent message
                return await self._handle_agent_message(event_data)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return {"status": "ignored", "reason": "Unknown event type"}

        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            raise

    async def call_dify_workflow(self, workflow_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Call a Dify workflow

        Args:
            workflow_id: Workflow identifier
            inputs: Workflow inputs

        Returns:
            Workflow response
        """
        try:
            if not self.dify_crawler_key:
                raise ValueError("Dify crawler key not configured")
            headers = {
                "Authorization": f"Bearer {self.dify_crawler_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.dify_api_url}/workflows/{workflow_id}/run",
                    headers=headers,
                    json={"inputs": inputs},
                )

                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to call Dify workflow: {str(e)}")
            raise

    async def call_dify_agent(
        self, agent_id: str, message: str, conversation_id: str | None = None
    ) -> dict[str, Any]:
        """
        Call a Dify agent

        Args:
            agent_id: Agent identifier
            message: User message
            conversation_id: Conversation ID for context

        Returns:
            Agent response
        """
        try:
            if not self.dify_crawler_key:
                raise ValueError("Dify crawler key not configured")
            headers = {
                "Authorization": f"Bearer {self.dify_crawler_key}",
                "Content-Type": "application/json",
            }

            payload = {"message": message, "user": "keypick_api"}

            if conversation_id:
                payload["conversation_id"] = conversation_id

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.dify_api_url}/agents/{agent_id}/chat", headers=headers, json=payload
                )

                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to call Dify agent: {str(e)}")
            raise

    def _format_for_dify(self, data: Any) -> dict[str, Any]:
        """
        Format data for Dify consumption

        Args:
            data: Raw data

        Returns:
            Formatted data
        """
        if not data:
            return {}

        # Ensure data is JSON-serializable
        if isinstance(data, dict):
            formatted: dict[str, Any] = {}
            for key, value in data.items():
                if isinstance(value, (datetime,)):
                    formatted[key] = value.isoformat()
                elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
                    formatted[key] = value  # type: ignore[assignment]
                else:
                    formatted[key] = str(value)
            return formatted
        elif isinstance(data, list):
            return {"items": data, "count": len(data)}
        else:
            return {"data": data}

    async def _handle_workflow_completed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle workflow completion event"""
        workflow_id = data.get("workflow_id")
        outputs = data.get("outputs", {})

        logger.info(f"Workflow {workflow_id} completed with outputs: {outputs}")

        # Process outputs if needed
        # For example, store results in database

        return {
            "status": "processed",
            "workflow_id": workflow_id,
            "message": "Workflow completion handled",
        }

    async def _handle_workflow_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle workflow failure event"""
        workflow_id = data.get("workflow_id")
        error = data.get("error", "Unknown error")

        logger.error(f"Workflow {workflow_id} failed: {error}")

        # Handle failure, e.g., retry or notify

        return {
            "status": "processed",
            "workflow_id": workflow_id,
            "message": "Workflow failure handled",
        }

    async def _handle_agent_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle agent message event"""
        agent_id = data.get("agent_id")
        message = data.get("message", "")
        conversation_id = data.get("conversation_id")

        logger.info(f"Agent {agent_id} message in conversation {conversation_id}: {message}")

        # Process agent message if needed

        return {
            "status": "processed",
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "message": "Agent message handled",
        }
