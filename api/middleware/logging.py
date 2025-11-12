"""
Logging middleware
"""

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/Response logging middleware
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response information
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Get request details
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(f"[{request_id}] {method} {url} - Client: {client_host}")

        # Process request and measure time
        start_time = time.time()
        try:
            response: Response = await call_next(request)  # type: ignore[assignment, no-any-return]
            process_time = round(time.time() - start_time, 3)

            # Log response
            logger.info(
                f"[{request_id}] {method} {url} - "
                f"Status: {response.status_code} - "
                f"Duration: {process_time}s"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response
        except Exception as e:
            process_time = round(time.time() - start_time, 3)
            logger.error(
                f"[{request_id}] {method} {url} - Error: {str(e)} - Duration: {process_time}s"
            )
            raise
