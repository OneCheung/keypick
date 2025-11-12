"""
Basic API tests
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "KeyPick API"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "keypick-api"


def test_api_info_endpoint():
    """Test API info endpoint"""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "KeyPick API"
    assert "endpoints" in data
    assert "crawler" in data["endpoints"]
    assert "processor" in data["endpoints"]
    assert "tools" in data["endpoints"]


def test_get_platforms():
    """Test get supported platforms"""
    response = client.get("/api/crawl/platforms")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Check platform structure
    for platform in data:
        assert "id" in platform
        assert "name" in platform
        assert "enabled" in platform
        assert "config" in platform


def test_dify_tool_schema():
    """Test Dify tool schema endpoint"""
    response = client.get("/api/tools/dify/schema")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "keypick_crawler"
    assert "description" in data
    assert "parameters" in data
    assert "response" in data
    assert isinstance(data["parameters"], list)


@pytest.mark.asyncio
async def test_crawl_request_validation():
    """Test crawl request validation"""
    # Test missing required fields
    response = client.post("/api/crawl/", json={})
    assert response.status_code == 422  # Validation error

    # Test invalid platform
    response = client.post(
        "/api/crawl/",
        json={"platform": "invalid_platform", "keywords": ["test"], "max_results": 10},
    )
    assert response.status_code == 422  # FastAPI validation error for invalid enum value

    # Test valid request (mock mode)
    response = client.post(
        "/api/crawl/",
        json={"platform": "xiaohongshu", "keywords": ["test", "keyword"], "max_results": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_data_cleaning():
    """Test data cleaning endpoint"""
    test_data = [
        {"id": "1", "content": "test1"},
        {"id": "2", "content": "test2"},
        {"id": "1", "content": "test1"},  # Duplicate
    ]

    response = client.post(
        "/api/process/clean", json={"data": test_data, "remove_duplicates": True}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["original_count"] == 3
    assert data["cleaned_count"] == 2
    assert data["removed_count"] == 1


@pytest.mark.asyncio
async def test_dify_crawl_tool():
    """Test Dify crawl tool endpoint"""
    response = client.post(
        "/api/tools/dify/crawl",
        json={
            "platform": "xiaohongshu",
            "keywords": "test,keyword",
            "max_results": 10,
            "async_mode": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # In sync mode, should have data
    if not data.get("async_mode"):
        assert "data" in data or "task_id" in data
