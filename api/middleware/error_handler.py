"""
Error handling middleware
"""

import logging
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler middleware
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any errors
        """
        try:
            response: Response = await call_next(request)  # type: ignore[assignment]
            return response
        except ValueError as e:
            # Handle validation errors
            logger.warning(f"Validation error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {"type": "ValidationError", "message": str(e)},
                    "data": None,
                },
            )
        except PermissionError as e:
            # Handle permission errors
            logger.warning(f"Permission error: {str(e)}")
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {"type": "PermissionError", "message": str(e)},
                    "data": None,
                },
            )
        except FileNotFoundError as e:
            # Handle not found errors
            logger.warning(f"Resource not found: {str(e)}")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {"type": "NotFoundError", "message": str(e)},
                    "data": None,
                },
            )
        except TimeoutError as e:
            # Handle timeout errors
            logger.error(f"Timeout error: {str(e)}")
            return JSONResponse(
                status_code=408,
                content={
                    "success": False,
                    "error": {"type": "TimeoutError", "message": "Request timeout"},
                    "data": None,
                },
            )
        except Exception as e:
            # Handle all other errors
            error_id = (
                request.state.request_id if hasattr(request.state, "request_id") else "unknown"
            )
            logger.error(f"Unhandled error [{error_id}]: {str(e)}\n{traceback.format_exc()}")

            # In production, don't expose internal errors
            from api.config import settings

            if settings.is_production:
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": {
                            "type": "InternalServerError",
                            "message": "An internal error occurred",
                            "error_id": error_id,
                        },
                        "data": None,
                    },
                )
            else:
                # In development, include more details
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": {
                            "type": "InternalServerError",
                            "message": str(e),
                            "error_id": error_id,
                            "traceback": traceback.format_exc().split("\n"),
                        },
                        "data": None,
                    },
                )
