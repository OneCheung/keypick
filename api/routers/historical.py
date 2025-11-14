"""
Historical Data Retrieval API endpoints
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.models.crawler_config import HistoricalDataQuery, SortBy
from api.services.historical_service import HistoricalDataService

router = APIRouter()

# Initialize service
historical_service = HistoricalDataService()


class HistoricalDataResponse(BaseModel):
    """Response model for historical data queries"""

    success: bool
    total: int
    items: List[Dict[str, Any]]
    query: HistoricalDataQuery
    metadata: Dict[str, Any] = Field(default={})


class AggregatedDataResponse(BaseModel):
    """Response model for aggregated data"""

    success: bool
    aggregation_type: str
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]


class DataExportResponse(BaseModel):
    """Response model for data export"""

    success: bool
    format: str
    total_records: int
    file_url: Optional[str] = None
    data: Optional[str] = None  # For inline export


@router.get("/", response_model=HistoricalDataResponse)
async def get_historical_data(
    # Task filters
    task_ids: Optional[str] = Query(default=None, description="Comma-separated task IDs"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms"),
    keywords: Optional[str] = Query(default=None, description="Comma-separated keywords"),

    # Time filters
    crawled_after: Optional[datetime] = Query(default=None, description="Data crawled after this date"),
    crawled_before: Optional[datetime] = Query(default=None, description="Data crawled before this date"),
    published_after: Optional[datetime] = Query(default=None, description="Content published after this date"),
    published_before: Optional[datetime] = Query(default=None, description="Content published before this date"),

    # Content filters
    search_text: Optional[str] = Query(default=None, description="Search in content"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
    authors: Optional[str] = Query(default=None, description="Comma-separated authors"),

    # Engagement filters
    min_engagement: Optional[int] = Query(default=None, ge=0, description="Minimum engagement"),
    max_engagement: Optional[int] = Query(default=None, ge=0, description="Maximum engagement"),

    # Sorting and pagination
    sort_by: SortBy = Query(default=SortBy.RECENT, description="Sort order"),
    sort_desc: bool = Query(default=True, description="Sort descending"),
    limit: int = Query(default=100, ge=1, le=1000, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),

    # Options
    include_stats: bool = Query(default=False, description="Include statistics")
) -> HistoricalDataResponse:
    """
    Query historical crawled data

    This endpoint allows querying previously crawled data without running new crawl tasks.
    Supports filtering by time range, platform, keywords, engagement metrics, and more.

    Examples:
    - Get data from last 7 days: crawled_after=2024-01-01T00:00:00
    - Get highly engaged content: min_engagement=1000&sort_by=hot
    - Search specific content: search_text=keyword&platforms=xiaohongshu,weibo
    """
    try:
        # Parse comma-separated values
        task_id_list = task_ids.split(",") if task_ids else None
        platform_list = platforms.split(",") if platforms else None
        keyword_list = keywords.split(",") if keywords else None
        tag_list = tags.split(",") if tags else None
        author_list = authors.split(",") if authors else None

        # Create query object
        query = HistoricalDataQuery(
            task_ids=task_id_list,
            platforms=platform_list,
            keywords=keyword_list,
            crawled_after=crawled_after,
            crawled_before=crawled_before,
            published_after=published_after,
            published_before=published_before,
            search_text=search_text,
            tags=tag_list,
            authors=author_list,
            min_engagement=min_engagement,
            max_engagement=max_engagement,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            include_stats=include_stats
        )

        # Execute query
        result = await historical_service.query_historical_data(query)

        return HistoricalDataResponse(
            success=True,
            total=result["total"],
            items=result["items"],
            query=query,
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/search", response_model=HistoricalDataResponse)
async def search_historical_data(
    q: str = Query(..., description="Search query"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms"),
    time_range: str = Query(default="7d", description="Time range (e.g., '7d', '30d')"),
    sort_by: SortBy = Query(default=SortBy.RELEVANT, description="Sort order"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
) -> HistoricalDataResponse:
    """
    Full-text search in historical data

    Performs full-text search across all crawled content.
    """
    try:
        # Calculate time range
        time_ranges = {
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }

        crawled_after = None
        if time_range in time_ranges:
            crawled_after = datetime.utcnow() - time_ranges[time_range]

        platform_list = platforms.split(",") if platforms else None

        # Create query
        query = HistoricalDataQuery(
            search_text=q,
            platforms=platform_list,
            crawled_after=crawled_after,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )

        # Execute search
        result = await historical_service.search_historical_data(query)

        return HistoricalDataResponse(
            success=True,
            total=result["total"],
            items=result["items"],
            query=query,
            metadata={"search_query": q, "time_range": time_range}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/aggregate", response_model=AggregatedDataResponse)
async def get_aggregated_data(
    aggregate_by: str = Query(..., description="Aggregation type: day, week, month, platform, author"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms"),
    start_date: Optional[datetime] = Query(default=None, description="Start date"),
    end_date: Optional[datetime] = Query(default=None, description="End date"),
    metrics: str = Query(default="engagement", description="Metrics to aggregate: engagement, posts, authors")
) -> AggregatedDataResponse:
    """
    Get aggregated historical data

    Returns time-series or categorical aggregations of crawled data.

    Examples:
    - Daily engagement: aggregate_by=day&metrics=engagement
    - Platform comparison: aggregate_by=platform&metrics=posts
    - Author rankings: aggregate_by=author&metrics=engagement
    """
    try:
        platform_list = platforms.split(",") if platforms else None

        # Default to last 30 days if no date range specified
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Execute aggregation
        result = await historical_service.aggregate_data(
            aggregate_by=aggregate_by,
            platforms=platform_list,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics
        )

        return AggregatedDataResponse(
            success=True,
            aggregation_type=aggregate_by,
            data=result["data"],
            summary=result["summary"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@router.post("/export", response_model=DataExportResponse)
async def export_historical_data(
    format: str = Query(default="csv", description="Export format: csv, json, excel"),
    task_ids: Optional[str] = Query(default=None, description="Comma-separated task IDs"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms"),
    start_date: Optional[datetime] = Query(default=None, description="Start date"),
    end_date: Optional[datetime] = Query(default=None, description="End date"),
    fields: Optional[str] = Query(default=None, description="Comma-separated fields to export"),
    limit: int = Query(default=10000, ge=1, le=100000, description="Maximum records to export")
) -> DataExportResponse:
    """
    Export historical data

    Export crawled data in various formats for external analysis.

    Supported formats:
    - CSV: Tabular format for spreadsheet applications
    - JSON: Structured format for programmatic use
    - Excel: Native Excel format with multiple sheets
    """
    try:
        task_id_list = task_ids.split(",") if task_ids else None
        platform_list = platforms.split(",") if platforms else None
        field_list = fields.split(",") if fields else None

        # Create query
        query = HistoricalDataQuery(
            task_ids=task_id_list,
            platforms=platform_list,
            crawled_after=start_date,
            crawled_before=end_date,
            limit=limit
        )

        # Execute export
        result = await historical_service.export_data(
            query=query,
            format=format,
            fields=field_list
        )

        return DataExportResponse(
            success=True,
            format=format,
            total_records=result["total_records"],
            file_url=result.get("file_url"),
            data=result.get("data")  # For small inline exports
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stats")
async def get_statistics(
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms"),
    time_range: str = Query(default="30d", description="Time range for statistics")
) -> dict:
    """
    Get statistics about historical data

    Returns summary statistics about stored data including:
    - Total records
    - Platform distribution
    - Time range coverage
    - Storage usage
    """
    try:
        platform_list = platforms.split(",") if platforms else None

        stats = await historical_service.get_statistics(
            platforms=platform_list,
            time_range=time_range
        )

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.delete("/cleanup")
async def cleanup_old_data(
    older_than_days: int = Query(..., ge=1, le=365, description="Delete data older than N days"),
    platforms: Optional[str] = Query(default=None, description="Comma-separated platforms to clean"),
    dry_run: bool = Query(default=True, description="If true, only simulate deletion")
) -> dict:
    """
    Clean up old historical data

    Removes data older than specified days to manage storage.
    Use dry_run=true to preview what would be deleted.
    """
    try:
        platform_list = platforms.split(",") if platforms else None

        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        result = await historical_service.cleanup_old_data(
            cutoff_date=cutoff_date,
            platforms=platform_list,
            dry_run=dry_run
        )

        return {
            "success": True,
            "dry_run": dry_run,
            "deleted_count": result["deleted_count"],
            "freed_space_mb": result.get("freed_space_mb", 0),
            "message": f"{'Would delete' if dry_run else 'Deleted'} {result['deleted_count']} records"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")