"""
Historical Data Service for querying and managing previously crawled data
"""

import json
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.models.crawler_config import HistoricalDataQuery, SortBy
from api.services.supabase_service import SupabaseService
from api.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """Service for managing historical crawled data"""

    def __init__(self):
        self.supabase = SupabaseService()
        self.redis = RedisService()
        self.cache_ttl = 3600  # 1 hour cache for historical queries

    async def query_historical_data(self, query: HistoricalDataQuery) -> Dict[str, Any]:
        """
        Query historical data based on filters

        Args:
            query: Query parameters for filtering and sorting

        Returns:
            Dictionary with items, total count, and metadata
        """
        try:
            # Check cache first
            cache_key = f"historical:{query.model_dump_json()}"
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info("Returning cached historical data")
                return json.loads(cached)

            # Build database query
            results = await self.supabase.query_results(query)

            # Process and enrich results
            processed_items = []
            for result in results.get("items", []):
                item = await self._process_historical_item(result)
                processed_items.append(item)

            # Apply additional filtering if needed
            if query.min_engagement or query.max_engagement:
                processed_items = self._filter_by_engagement(
                    processed_items,
                    query.min_engagement,
                    query.max_engagement
                )

            # Sort results
            processed_items = self._sort_results(processed_items, query.sort_by, query.sort_desc)

            # Apply pagination
            total = len(processed_items)
            start = query.offset
            end = start + query.limit
            paginated_items = processed_items[start:end]

            # Generate metadata
            metadata = {}
            if query.include_stats:
                metadata = await self._generate_statistics(processed_items)

            result = {
                "items": paginated_items,
                "total": total,
                "metadata": metadata
            }

            # Cache the result
            await self.redis.set(cache_key, json.dumps(result), ttl=self.cache_ttl)

            return result

        except Exception as e:
            logger.error(f"Failed to query historical data: {e}")
            raise

    async def search_historical_data(self, query: HistoricalDataQuery) -> Dict[str, Any]:
        """
        Perform full-text search in historical data

        Args:
            query: Search query with filters

        Returns:
            Search results with relevance scoring
        """
        try:
            # Use Supabase full-text search if available
            results = await self.supabase.search_results(
                search_text=query.search_text,
                platforms=query.platforms,
                after_date=query.crawled_after
            )

            # Score results by relevance
            scored_items = []
            for item in results.get("items", []):
                score = self._calculate_relevance_score(item, query.search_text)
                item["relevance_score"] = score
                scored_items.append(item)

            # Sort by relevance if requested
            if query.sort_by == SortBy.RELEVANT:
                scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)
            else:
                scored_items = self._sort_results(scored_items, query.sort_by, query.sort_desc)

            # Apply pagination
            total = len(scored_items)
            start = query.offset
            end = start + query.limit
            paginated_items = scored_items[start:end]

            return {
                "items": paginated_items,
                "total": total,
                "metadata": {
                    "search_query": query.search_text,
                    "max_relevance": max((i["relevance_score"] for i in scored_items), default=0)
                }
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def aggregate_data(
        self,
        aggregate_by: str,
        platforms: Optional[List[str]],
        start_date: datetime,
        end_date: datetime,
        metrics: str
    ) -> Dict[str, Any]:
        """
        Aggregate historical data by various dimensions

        Args:
            aggregate_by: Aggregation dimension (day, week, month, platform, author)
            platforms: Filter by platforms
            start_date: Start of date range
            end_date: End of date range
            metrics: Metrics to calculate (engagement, posts, authors)

        Returns:
            Aggregated data and summary statistics
        """
        try:
            # Query raw data
            query = HistoricalDataQuery(
                platforms=platforms,
                crawled_after=start_date,
                crawled_before=end_date,
                limit=10000  # Large limit for aggregation
            )

            results = await self.supabase.query_results(query)
            items = results.get("items", [])

            # Perform aggregation based on type
            if aggregate_by == "day":
                aggregated = self._aggregate_by_day(items, metrics)
            elif aggregate_by == "week":
                aggregated = self._aggregate_by_week(items, metrics)
            elif aggregate_by == "month":
                aggregated = self._aggregate_by_month(items, metrics)
            elif aggregate_by == "platform":
                aggregated = self._aggregate_by_platform(items, metrics)
            elif aggregate_by == "author":
                aggregated = self._aggregate_by_author(items, metrics)
            else:
                raise ValueError(f"Unsupported aggregation type: {aggregate_by}")

            # Calculate summary statistics
            summary = self._calculate_summary(aggregated, metrics)

            return {
                "data": aggregated,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            raise

    async def export_data(
        self,
        query: HistoricalDataQuery,
        format: str,
        fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        """
        Export historical data in various formats

        Args:
            query: Query to filter data
            format: Export format (csv, json, excel)
            fields: Specific fields to export

        Returns:
            Export result with file URL or inline data
        """
        try:
            # Query data
            results = await self.query_historical_data(query)
            items = results["items"]

            # Filter fields if specified
            if fields:
                items = [
                    {k: v for k, v in item.items() if k in fields}
                    for item in items
                ]

            # Export based on format
            if format == "csv":
                export_data = self._export_to_csv(items)
            elif format == "json":
                export_data = self._export_to_json(items)
            elif format == "excel":
                export_data = await self._export_to_excel(items)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # For small exports, return inline
            if len(items) <= 1000:
                return {
                    "total_records": len(items),
                    "data": export_data
                }

            # For large exports, save to storage and return URL
            file_url = await self._save_export_file(export_data, format)
            return {
                "total_records": len(items),
                "file_url": file_url
            }

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

    async def get_statistics(
        self,
        platforms: Optional[List[str]],
        time_range: str
    ) -> Dict[str, Any]:
        """
        Get statistics about stored historical data

        Args:
            platforms: Filter by platforms
            time_range: Time range for statistics

        Returns:
            Statistical summary
        """
        try:
            # Parse time range
            time_ranges = {
                "1d": timedelta(days=1),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30),
                "90d": timedelta(days=90),
                "all": None
            }

            after_date = None
            if time_range in time_ranges and time_ranges[time_range]:
                after_date = datetime.utcnow() - time_ranges[time_range]

            # Get statistics from database
            stats = await self.supabase.get_statistics(
                platforms=platforms,
                after_date=after_date
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise

    async def cleanup_old_data(
        self,
        cutoff_date: datetime,
        platforms: Optional[List[str]],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Clean up old historical data

        Args:
            cutoff_date: Delete data older than this date
            platforms: Specific platforms to clean
            dry_run: If true, only simulate deletion

        Returns:
            Cleanup results
        """
        try:
            if dry_run:
                # Count records that would be deleted
                count = await self.supabase.count_old_records(
                    cutoff_date=cutoff_date,
                    platforms=platforms
                )
                return {
                    "deleted_count": count,
                    "freed_space_mb": count * 0.1  # Estimate ~100KB per record
                }

            # Perform actual deletion
            deleted = await self.supabase.delete_old_records(
                cutoff_date=cutoff_date,
                platforms=platforms
            )

            # Clear related caches
            await self.redis.clear_pattern("historical:*")

            return {
                "deleted_count": deleted,
                "freed_space_mb": deleted * 0.1
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise

    # Helper methods

    async def _process_historical_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enrich a historical data item"""
        # Extract raw data
        raw_data = item.get("raw_data", {})

        # Flatten the structure for easier access
        processed = {
            "id": item.get("id"),
            "task_id": item.get("task_id"),
            "platform": item.get("platform"),
            "crawled_at": item.get("created_at"),
            **raw_data
        }

        # Calculate total engagement if not present
        if "total_engagement" not in processed:
            processed["total_engagement"] = (
                processed.get("likes", 0) +
                processed.get("comments", 0) +
                processed.get("shares", 0) +
                processed.get("collects", 0)
            )

        return processed

    def _filter_by_engagement(
        self,
        items: List[Dict],
        min_engagement: Optional[int],
        max_engagement: Optional[int]
    ) -> List[Dict]:
        """Filter items by engagement metrics"""
        filtered = []
        for item in items:
            engagement = item.get("total_engagement", 0)
            if min_engagement and engagement < min_engagement:
                continue
            if max_engagement and engagement > max_engagement:
                continue
            filtered.append(item)
        return filtered

    def _sort_results(
        self,
        items: List[Dict],
        sort_by: SortBy,
        desc: bool
    ) -> List[Dict]:
        """Sort results by specified criteria"""
        if sort_by == SortBy.HOT:
            key = lambda x: x.get("total_engagement", 0)
        elif sort_by == SortBy.RECENT:
            key = lambda x: x.get("publish_time", x.get("crawled_at", ""))
        elif sort_by == SortBy.TRENDING:
            # Calculate engagement velocity
            now = datetime.utcnow()
            key = lambda x: self._calculate_trend_score(x, now)
        elif sort_by == SortBy.LIKES:
            key = lambda x: x.get("likes", 0)
        elif sort_by == SortBy.COMMENTS:
            key = lambda x: x.get("comments", 0)
        else:
            key = lambda x: x.get("crawled_at", "")

        return sorted(items, key=key, reverse=desc)

    def _calculate_trend_score(self, item: Dict, now: datetime) -> float:
        """Calculate trending score based on engagement velocity"""
        try:
            publish_time = datetime.fromisoformat(
                item.get("publish_time", item.get("crawled_at", ""))
            )
            days_old = max(1, (now - publish_time).days)
            engagement = item.get("total_engagement", 0)
            return engagement / days_old
        except:
            return 0

    def _calculate_relevance_score(self, item: Dict, search_text: str) -> float:
        """Calculate relevance score for search results"""
        score = 0
        search_lower = search_text.lower()

        # Check title (highest weight)
        if search_lower in item.get("title", "").lower():
            score += 10

        # Check content (medium weight)
        if search_lower in item.get("content", "").lower():
            score += 5

        # Check tags (lower weight)
        tags = item.get("tags", [])
        if any(search_lower in tag.lower() for tag in tags):
            score += 3

        # Boost by engagement
        engagement = item.get("total_engagement", 0)
        score += min(5, engagement / 1000)  # Max 5 points from engagement

        return score

    async def _generate_statistics(self, items: List[Dict]) -> Dict[str, Any]:
        """Generate statistics for a set of items"""
        if not items:
            return {}

        total_engagement = sum(i.get("total_engagement", 0) for i in items)
        avg_engagement = total_engagement / len(items) if items else 0

        platforms = {}
        authors = {}

        for item in items:
            # Platform stats
            platform = item.get("platform", "unknown")
            if platform not in platforms:
                platforms[platform] = {"count": 0, "engagement": 0}
            platforms[platform]["count"] += 1
            platforms[platform]["engagement"] += item.get("total_engagement", 0)

            # Author stats
            author = item.get("author", "unknown")
            if author not in authors:
                authors[author] = {"count": 0, "engagement": 0}
            authors[author]["count"] += 1
            authors[author]["engagement"] += item.get("total_engagement", 0)

        # Get top authors
        top_authors = sorted(
            authors.items(),
            key=lambda x: x[1]["engagement"],
            reverse=True
        )[:10]

        return {
            "total_items": len(items),
            "total_engagement": total_engagement,
            "average_engagement": avg_engagement,
            "platform_distribution": platforms,
            "top_authors": dict(top_authors)
        }

    def _aggregate_by_day(self, items: List[Dict], metrics: str) -> List[Dict]:
        """Aggregate data by day"""
        aggregated = {}

        for item in items:
            date_str = item.get("publish_time", item.get("crawled_at", ""))
            if not date_str:
                continue

            try:
                date = datetime.fromisoformat(date_str).date()
                key = date.isoformat()

                if key not in aggregated:
                    aggregated[key] = {
                        "date": key,
                        "count": 0,
                        "engagement": 0,
                        "authors": set()
                    }

                aggregated[key]["count"] += 1
                aggregated[key]["engagement"] += item.get("total_engagement", 0)
                aggregated[key]["authors"].add(item.get("author", "unknown"))

            except:
                continue

        # Convert sets to counts
        result = []
        for key, data in aggregated.items():
            data["unique_authors"] = len(data["authors"])
            del data["authors"]
            result.append(data)

        return sorted(result, key=lambda x: x["date"])

    def _aggregate_by_platform(self, items: List[Dict], metrics: str) -> List[Dict]:
        """Aggregate data by platform"""
        aggregated = {}

        for item in items:
            platform = item.get("platform", "unknown")

            if platform not in aggregated:
                aggregated[platform] = {
                    "platform": platform,
                    "count": 0,
                    "engagement": 0,
                    "authors": set()
                }

            aggregated[platform]["count"] += 1
            aggregated[platform]["engagement"] += item.get("total_engagement", 0)
            aggregated[platform]["authors"].add(item.get("author", "unknown"))

        # Convert to list
        result = []
        for platform, data in aggregated.items():
            data["unique_authors"] = len(data["authors"])
            del data["authors"]
            result.append(data)

        return sorted(result, key=lambda x: x["engagement"], reverse=True)

    def _aggregate_by_author(self, items: List[Dict], metrics: str) -> List[Dict]:
        """Aggregate data by author"""
        aggregated = {}

        for item in items:
            author = item.get("author", "unknown")

            if author not in aggregated:
                aggregated[author] = {
                    "author": author,
                    "count": 0,
                    "engagement": 0,
                    "platforms": set()
                }

            aggregated[author]["count"] += 1
            aggregated[author]["engagement"] += item.get("total_engagement", 0)
            aggregated[author]["platforms"].add(item.get("platform", "unknown"))

        # Convert to list and get top authors
        result = []
        for author, data in aggregated.items():
            data["platform_count"] = len(data["platforms"])
            del data["platforms"]
            result.append(data)

        return sorted(result, key=lambda x: x["engagement"], reverse=True)[:100]

    def _aggregate_by_week(self, items: List[Dict], metrics: str) -> List[Dict]:
        """Aggregate data by week"""
        # Similar to day aggregation but group by week
        # Implementation would be similar to _aggregate_by_day
        return self._aggregate_by_day(items, metrics)  # Simplified for now

    def _aggregate_by_month(self, items: List[Dict], metrics: str) -> List[Dict]:
        """Aggregate data by month"""
        # Similar to day aggregation but group by month
        return self._aggregate_by_day(items, metrics)  # Simplified for now

    def _calculate_summary(self, aggregated: List[Dict], metrics: str) -> Dict[str, Any]:
        """Calculate summary statistics for aggregated data"""
        if not aggregated:
            return {}

        total_count = sum(a.get("count", 0) for a in aggregated)
        total_engagement = sum(a.get("engagement", 0) for a in aggregated)

        return {
            "total_count": total_count,
            "total_engagement": total_engagement,
            "average_engagement_per_item": total_engagement / total_count if total_count else 0,
            "data_points": len(aggregated)
        }

    def _export_to_csv(self, items: List[Dict]) -> str:
        """Export items to CSV format"""
        if not items:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)

        return output.getvalue()

    def _export_to_json(self, items: List[Dict]) -> str:
        """Export items to JSON format"""
        return json.dumps(items, indent=2, default=str)

    async def _export_to_excel(self, items: List[Dict]) -> bytes:
        """Export items to Excel format"""
        # This would require openpyxl or similar library
        # For now, return CSV as fallback
        return self._export_to_csv(items).encode()

    async def _save_export_file(self, data: str | bytes, format: str) -> str:
        """Save export file and return URL"""
        # In production, this would upload to S3 or similar
        # For now, return a placeholder URL
        timestamp = datetime.utcnow().isoformat()
        filename = f"export_{timestamp}.{format}"
        return f"/exports/{filename}"