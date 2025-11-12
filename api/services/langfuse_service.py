"""
Langfuse integration service for LLM observability
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from api.config import settings

logger = logging.getLogger(__name__)

# Import Langfuse client conditionally
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("Langfuse client not installed. Install with: pip install langfuse")


class LangfuseService:
    """
    Service for LLM observability and evaluation using Langfuse Cloud
    """

    def __init__(self):
        self.public_key = settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = settings.LANGFUSE_SECRET_KEY
        self.host = settings.LANGFUSE_HOST
        self.client = None

        if LANGFUSE_AVAILABLE and self.public_key and self.secret_key:
            try:
                self.client = Langfuse(
                    public_key=self.public_key, secret_key=self.secret_key, host=self.host
                )
                logger.info("Langfuse client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {str(e)}")
                self.client = None
        else:
            logger.warning("Langfuse not configured or not available")

    async def trace_llm_call(
        self,
        name: str,
        input_data: Any,
        output_data: Any,
        model: str = "unknown",
        tokens: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> str | None:
        """
        Trace an LLM call

        Args:
            name: Name of the operation
            input_data: Input sent to LLM
            output_data: Output from LLM
            model: Model name
            tokens: Token usage (prompt, completion, total)
            metadata: Additional metadata
            user_id: User identifier
            session_id: Session identifier

        Returns:
            Trace ID if successful
        """
        try:
            if not self.client:
                return None

            # Create trace
            trace = self.client.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata={"service": "keypick", "model": model, **(metadata or {})},
            )

            # Add generation span
            trace.generation(
                name=f"{name}_generation",
                model=model,
                input=input_data,
                output=output_data,
                usage=tokens,
                metadata=metadata,
            )

            # Flush to ensure data is sent
            self.client.flush()

            return trace.id

        except Exception as e:
            logger.error(f"Error tracing LLM call: {str(e)}")
            return None

    async def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
        data_type: str = "NUMERIC",
    ) -> bool:
        """
        Add a score to a trace

        Args:
            trace_id: Trace identifier
            name: Score name (e.g., "quality", "relevance")
            value: Score value
            comment: Optional comment
            data_type: Score data type

        Returns:
            True if successful
        """
        try:
            if not self.client:
                return False

            self.client.score(
                trace_id=trace_id, name=name, value=value, comment=comment, data_type=data_type
            )

            self.client.flush()
            return True

        except Exception as e:
            logger.error(f"Error adding score: {str(e)}")
            return False

    async def trace_api_call(
        self,
        endpoint: str,
        method: str,
        request_data: dict[str, Any],
        response_data: dict[str, Any],
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
    ) -> str | None:
        """
        Trace an API call

        Args:
            endpoint: API endpoint
            method: HTTP method
            request_data: Request payload
            response_data: Response payload
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_id: User identifier

        Returns:
            Trace ID if successful
        """
        try:
            if not self.client:
                return None

            trace = self.client.trace(
                name=f"API_{method}_{endpoint}",
                user_id=user_id,
                metadata={
                    "service": "keypick_api",
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

            # Add span for the API call
            trace.span(
                name="api_request",
                input=request_data,
                output=response_data,
                metadata={"status_code": status_code, "duration_ms": duration_ms},
            )

            self.client.flush()
            return trace.id

        except Exception as e:
            logger.error(f"Error tracing API call: {str(e)}")
            return None

    async def trace_crawler_task(
        self,
        task_id: str,
        platform: str,
        keywords: list[str],
        result_count: int,
        success: bool,
        duration_s: float,
        error: str | None = None,
    ) -> str | None:
        """
        Trace a crawler task execution

        Args:
            task_id: Task identifier
            platform: Platform crawled
            keywords: Keywords used
            result_count: Number of results
            success: Whether task succeeded
            duration_s: Task duration in seconds
            error: Error message if failed

        Returns:
            Trace ID if successful
        """
        try:
            if not self.client:
                return None

            trace = self.client.trace(
                name=f"crawler_{platform}",
                metadata={
                    "service": "keypick_crawler",
                    "task_id": task_id,
                    "platform": platform,
                    "keywords": keywords,
                    "result_count": result_count,
                    "success": success,
                    "duration_s": duration_s,
                    "error": error,
                },
            )

            # Add span for the crawl operation
            trace.span(
                name="crawl_execution",
                input={"platform": platform, "keywords": keywords},
                output={"result_count": result_count, "success": success},
                metadata={"duration_s": duration_s, "error": error},
            )

            # Auto-score based on success
            if success:
                await self.score(trace.id, "success_rate", 1.0)
            else:
                await self.score(trace.id, "success_rate", 0.0, comment=error)

            self.client.flush()
            return trace.id

        except Exception as e:
            logger.error(f"Error tracing crawler task: {str(e)}")
            return None

    async def trace_data_processing(
        self,
        operation: str,
        input_count: int,
        output_count: int,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Trace data processing operations

        Args:
            operation: Operation name (clean, extract, transform)
            input_count: Number of input items
            output_count: Number of output items
            duration_ms: Processing duration
            metadata: Additional metadata

        Returns:
            Trace ID if successful
        """
        try:
            if not self.client:
                return None

            trace = self.client.trace(
                name=f"process_{operation}",
                metadata={
                    "service": "keypick_processor",
                    "operation": operation,
                    "input_count": input_count,
                    "output_count": output_count,
                    "duration_ms": duration_ms,
                    **(metadata or {}),
                },
            )

            # Calculate efficiency score
            if input_count > 0:
                efficiency = output_count / input_count
                await self.score(trace.id, "processing_efficiency", efficiency)

            self.client.flush()
            return trace.id

        except Exception as e:
            logger.error(f"Error tracing data processing: {str(e)}")
            return None

    async def get_metrics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Get aggregated metrics

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            Metrics dictionary
        """
        try:
            if not self.client:
                return {}

            # Note: Langfuse SDK doesn't directly provide metrics API
            # This would typically be accessed via Langfuse dashboard
            # or their REST API

            return {
                "note": "Metrics available in Langfuse dashboard",
                "dashboard_url": f"{self.host}/project",
            }

        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return {}

    async def create_dataset(
        self,
        name: str,
        description: str | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> bool:
        """
        Create a dataset for evaluation

        Args:
            name: Dataset name
            description: Dataset description
            items: Initial dataset items

        Returns:
            True if successful
        """
        try:
            if not self.client:
                return False

            # Create dataset
            self.client.create_dataset(
                name=name,
                description=description or f"KeyPick dataset created at {datetime.utcnow()}",
            )

            # Add items if provided
            if items:
                for item in items:
                    self.client.create_dataset_item(
                        dataset_name=name,
                        input=item.get("input"),
                        expected_output=item.get("expected_output"),
                        metadata=item.get("metadata"),
                    )

            self.client.flush()
            return True

        except Exception as e:
            logger.error(f"Error creating dataset: {str(e)}")
            return False

    async def run_evaluation(
        self, dataset_name: str, model: str, eval_function: Callable[..., Any]
    ) -> dict[str, Any]:
        """
        Run evaluation on a dataset

        Args:
            dataset_name: Dataset to evaluate
            model: Model name
            eval_function: Function to evaluate items

        Returns:
            Evaluation results
        """
        try:
            if not self.client:
                return {}

            # This is a simplified example
            # In practice, you'd fetch dataset items and run evaluation

            results = {
                "dataset": dataset_name,
                "model": model,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Full evaluation requires implementation",
            }

            return results

        except Exception as e:
            logger.error(f"Error running evaluation: {str(e)}")
            return {}

    def flush(self):
        """
        Flush any pending traces to Langfuse
        """
        try:
            if self.client:
                self.client.flush()
        except Exception as e:
            logger.error(f"Error flushing traces: {str(e)}")
