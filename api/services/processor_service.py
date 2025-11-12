"""
Data processing service
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProcessorService:
    """
    Service for processing and analyzing crawled data
    """

    async def clean_data(
        self,
        data: List[Dict[str, Any]],
        remove_duplicates: bool = True,
        normalize: bool = True,
        extract_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Clean and normalize data

        Args:
            data: Raw data to clean
            remove_duplicates: Whether to remove duplicates
            normalize: Whether to normalize formats
            extract_fields: Specific fields to extract

        Returns:
            Cleaned data list
        """
        try:
            cleaned_data = data.copy()

            # Remove duplicates
            if remove_duplicates:
                cleaned_data = self._remove_duplicates(cleaned_data)

            # Normalize data
            if normalize:
                cleaned_data = self._normalize_data(cleaned_data)

            # Extract specific fields
            if extract_fields:
                cleaned_data = self._extract_fields(cleaned_data, extract_fields)

            return cleaned_data

        except Exception as e:
            logger.error(f"Data cleaning failed: {str(e)}")
            raise

    async def extract_insights(
        self,
        data: List[Dict[str, Any]],
        analysis_type: str = "summary",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Extract insights from data

        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            use_llm: Whether to use LLM for analysis

        Returns:
            Insights dictionary
        """
        try:
            insights = {
                "total_items": len(data),
                "analysis_type": analysis_type,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Basic statistical analysis
            insights.update(self._analyze_statistics(data))

            # Extract keywords
            insights["keywords"] = self._extract_keywords(data)

            # Generate summary
            if analysis_type == "summary":
                insights["summary"] = self._generate_summary(data)
            elif analysis_type == "trends":
                insights["trends"] = self._analyze_trends(data)
            elif analysis_type == "sentiment":
                insights["sentiment"] = self._analyze_sentiment(data)

            # If LLM is enabled, enhance insights
            if use_llm:
                # TODO: Integrate with Dify LLM for advanced analysis
                insights["llm_analysis"] = "LLM analysis will be integrated with Dify"

            return {
                "insights": insights,
                "summary": insights.get("summary", ""),
                "keywords": insights.get("keywords", []),
                "trends": insights.get("trends")
            }

        except Exception as e:
            logger.error(f"Insight extraction failed: {str(e)}")
            raise

    async def transform_data(
        self,
        data: List[Dict[str, Any]],
        output_format: str = "json"
    ) -> Any:
        """
        Transform data to different formats

        Args:
            data: Data to transform
            output_format: Target format

        Returns:
            Transformed data
        """
        try:
            if output_format == "json":
                return data
            elif output_format == "csv":
                return self._to_csv(data)
            elif output_format == "markdown":
                return self._to_markdown(data)
            else:
                raise ValueError(f"Unsupported format: {output_format}")

        except Exception as e:
            logger.error(f"Data transformation failed: {str(e)}")
            raise

    async def validate_data(
        self,
        data: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate data against schema

        Args:
            data: Data to validate
            schema: Validation schema

        Returns:
            Validation results
        """
        try:
            errors = []
            warnings = []
            valid_count = 0

            for i, item in enumerate(data):
                item_errors = self._validate_item(item, schema)
                if item_errors:
                    errors.extend([f"Item {i}: {err}" for err in item_errors])
                else:
                    valid_count += 1

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "stats": {
                    "total_items": len(data),
                    "valid_items": valid_count,
                    "invalid_items": len(data) - valid_count
                }
            }

        except Exception as e:
            logger.error(f"Data validation failed: {str(e)}")
            raise

    def _remove_duplicates(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items based on content hash"""
        seen: Set[str] = set()
        unique_data = []

        for item in data:
            # Create hash of item content
            item_hash = hashlib.md5(
                json.dumps(item, sort_keys=True).encode()
            ).hexdigest()

            if item_hash not in seen:
                seen.add(item_hash)
                unique_data.append(item)

        return unique_data

    def _normalize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize data formats"""
        normalized = []

        for item in data:
            normalized_item = {}

            # Normalize common fields
            for key, value in item.items():
                # Convert to lowercase keys
                key_lower = key.lower()

                # Normalize dates
                if "date" in key_lower or "time" in key_lower:
                    normalized_item[key] = self._normalize_date(value)
                # Normalize numbers
                elif isinstance(value, (int, float)):
                    normalized_item[key] = value
                # Normalize strings
                elif isinstance(value, str):
                    normalized_item[key] = value.strip()
                else:
                    normalized_item[key] = value

            normalized.append(normalized_item)

        return normalized

    def _extract_fields(
        self,
        data: List[Dict[str, Any]],
        fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract specific fields from data"""
        extracted = []

        for item in data:
            extracted_item = {}
            for field in fields:
                if field in item:
                    extracted_item[field] = item[field]
            if extracted_item:
                extracted.append(extracted_item)

        return extracted

    def _analyze_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze basic statistics"""
        stats = {
            "item_count": len(data),
            "platforms": {},
            "date_range": {}
        }

        # Count by platform
        for item in data:
            platform = item.get("platform", "unknown")
            stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1

        return stats

    def _extract_keywords(self, data: List[Dict[str, Any]]) -> List[str]:
        """Extract keywords from data"""
        # Simple keyword extraction for MVP
        keywords = set()

        for item in data:
            # Extract from tags
            if "tags" in item:
                if isinstance(item["tags"], list):
                    keywords.update(item["tags"])

            # Extract from hashtags
            if "hashtags" in item:
                if isinstance(item["hashtags"], list):
                    keywords.update(item["hashtags"])

        return list(keywords)[:20]  # Return top 20 keywords

    def _generate_summary(self, data: List[Dict[str, Any]]) -> str:
        """Generate summary of data"""
        # Simple summary for MVP
        total = len(data)
        platforms = set(item.get("platform", "unknown") for item in data)

        return (
            f"Analyzed {total} items from {len(platforms)} platform(s): "
            f"{', '.join(platforms)}. "
            f"Data contains various social media posts and content."
        )

    def _analyze_trends(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze trends in data"""
        # Simple trend analysis for MVP
        trends = []

        # Count hashtags/tags frequency
        tag_counts = {}
        for item in data:
            tags = item.get("tags", []) + item.get("hashtags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Get top trends
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            trends.append({
                "topic": tag,
                "count": count,
                "trend": "rising"  # Simplified for MVP
            })

        return trends

    def _analyze_sentiment(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment of data"""
        # Simplified sentiment analysis for MVP
        return {
            "positive": 0.4,
            "neutral": 0.5,
            "negative": 0.1,
            "note": "Sentiment analysis will be enhanced with LLM integration"
        }

    def _normalize_date(self, value: Any) -> str:
        """Normalize date format"""
        if isinstance(value, str):
            # Simple normalization for MVP
            return value
        return str(value)

    def _to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert data to CSV format"""
        if not data:
            return ""

        # Get all unique keys
        keys = set()
        for item in data:
            keys.update(item.keys())

        # Create CSV
        csv_lines = [",".join(keys)]
        for item in data:
            values = [str(item.get(key, "")) for key in keys]
            csv_lines.append(",".join(values))

        return "\n".join(csv_lines)

    def _to_markdown(self, data: List[Dict[str, Any]]) -> str:
        """Convert data to Markdown format"""
        if not data:
            return "# No Data"

        md_lines = ["# Data Report", ""]
        md_lines.append(f"**Total Items**: {len(data)}")
        md_lines.append("")

        # Add items
        for i, item in enumerate(data[:10], 1):  # Show first 10 items
            md_lines.append(f"## Item {i}")
            for key, value in item.items():
                md_lines.append(f"- **{key}**: {value}")
            md_lines.append("")

        return "\n".join(md_lines)

    def _validate_item(
        self,
        item: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Validate a single item"""
        errors = []

        # Basic validation
        if not item:
            errors.append("Item is empty")

        # Schema validation if provided
        if schema:
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in item:
                    errors.append(f"Missing required field: {field}")

        return errors