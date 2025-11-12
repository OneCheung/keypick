"""
Data processor API endpoints
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.processor_service import ProcessorService

router = APIRouter()

# Initialize services
processor_service = ProcessorService()


class CleanDataRequest(BaseModel):
    """Data cleaning request"""

    data: list[dict[str, Any]] = Field(..., description="Raw data to clean")
    remove_duplicates: bool = Field(default=True, description="Remove duplicate entries")
    normalize: bool = Field(default=True, description="Normalize data format")
    extract_fields: list[str] | None = Field(default=None, description="Fields to extract")


class CleanDataResponse(BaseModel):
    """Data cleaning response"""

    success: bool
    original_count: int
    cleaned_count: int
    removed_count: int
    data: list[dict[str, Any]]
    message: str


class ExtractInsightsRequest(BaseModel):
    """Insights extraction request"""

    data: list[dict[str, Any]] = Field(..., description="Data to analyze")
    analysis_type: str = Field(
        default="summary", description="Type of analysis (summary, trends, sentiment)"
    )
    use_llm: bool = Field(default=True, description="Use LLM for analysis")


class ExtractInsightsResponse(BaseModel):
    """Insights extraction response"""

    success: bool
    insights: dict[str, Any]
    summary: str
    keywords: list[str]
    trends: list[dict[str, Any]] | None = None


@router.post("/clean", response_model=CleanDataResponse)
async def clean_data(request: CleanDataRequest) -> CleanDataResponse:
    """
    Clean and normalize crawled data

    This endpoint processes raw crawled data by:
    - Removing duplicates
    - Normalizing formats
    - Extracting specified fields
    - Validating data quality
    """
    try:
        # Process data
        cleaned_data = await processor_service.clean_data(
            data=request.data,
            remove_duplicates=request.remove_duplicates,
            normalize=request.normalize,
            extract_fields=request.extract_fields,
        )

        original_count = len(request.data)
        cleaned_count = len(cleaned_data)
        removed_count = original_count - cleaned_count

        return CleanDataResponse(
            success=True,
            original_count=original_count,
            cleaned_count=cleaned_count,
            removed_count=removed_count,
            data=cleaned_data,
            message=f"Successfully cleaned data: {removed_count} duplicates removed",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clean data: {str(e)}")


@router.post("/extract", response_model=ExtractInsightsResponse)
async def extract_insights(request: ExtractInsightsRequest) -> ExtractInsightsResponse:
    """
    Extract insights from processed data

    Uses LLM to analyze data and extract:
    - Key insights and patterns
    - Summary of content
    - Trending topics
    - Sentiment analysis (if applicable)
    """
    try:
        # Extract insights
        result = await processor_service.extract_insights(
            data=request.data, analysis_type=request.analysis_type, use_llm=request.use_llm
        )

        return ExtractInsightsResponse(
            success=True,
            insights=result.get("insights", {}),
            summary=result.get("summary", ""),
            keywords=result.get("keywords", []),
            trends=result.get("trends"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract insights: {str(e)}")


class TransformDataRequest(BaseModel):
    """Data transformation request"""

    data: list[dict[str, Any]] = Field(..., description="Data to transform")
    output_format: str = Field(default="json", description="Output format (json, csv, markdown)")


@router.post("/transform")
async def transform_data(request: TransformDataRequest) -> dict[str, Any]:
    """
    Transform data to different formats

    Supports transformation to:
    - JSON (structured)
    - CSV format
    - Markdown report
    - Custom templates
    """
    try:
        transformed = await processor_service.transform_data(
            data=request.data, output_format=request.output_format
        )

        return {"success": True, "format": request.output_format, "data": transformed}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transform data: {str(e)}")


class ValidateDataRequest(BaseModel):
    """Data validation request"""

    data: list[dict[str, Any]] = Field(..., description="Data to validate")
    schema: dict[str, Any] | None = Field(default=None, description="Validation schema")


@router.post("/validate")
async def validate_data(request: ValidateDataRequest) -> dict[str, Any]:
    """
    Validate data against schema

    Checks data quality and completeness based on provided schema
    or default validation rules.
    """
    try:
        validation_result = await processor_service.validate_data(
            data=request.data, schema=request.schema
        )

        return {
            "success": True,
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "stats": validation_result.get("stats", {}),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate data: {str(e)}")
