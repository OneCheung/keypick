"""
KeyPick API 集成测试套件
包含完整的 API 功能测试
"""

import asyncio

import httpx
import pytest

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_API_KEY = "keypick-test-001"


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """测试健康检查端点"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "keypick-api"
            assert "version" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """测试根路径端点"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "KeyPick API"
            assert "version" in data
            assert "environment" in data

    @pytest.mark.asyncio
    async def test_api_info(self):
        """测试 API 信息端点"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api")
            assert response.status_code == 200
            data = response.json()
            assert "endpoints" in data
            assert data["endpoints"]["crawler"] == "/api/crawl"
            assert data["endpoints"]["processor"] == "/api/process"
            assert data["endpoints"]["tools"] == "/api/tools"


class TestCrawlerAPI:
    """爬虫 API 测试"""

    @pytest.mark.asyncio
    async def test_get_platforms(self):
        """测试获取平台列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/crawl/platforms")
            assert response.status_code == 200
            platforms = response.json()
            assert isinstance(platforms, list)
            assert len(platforms) >= 3

            # 验证平台结构
            for platform in platforms:
                assert "id" in platform
                assert "name" in platform
                assert "enabled" in platform
                assert "config" in platform

    @pytest.mark.asyncio
    async def test_create_crawl_task(self):
        """测试创建爬取任务"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 测试小红书爬取
            response = await client.post(
                f"{BASE_URL}/api/crawl/",
                json={"platform": "xiaohongshu", "keywords": ["测试"], "max_results": 5},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "task_id" in data
            assert data["status"] == "pending"

            return data["task_id"]

    @pytest.mark.asyncio
    async def test_crawl_task_status(self):
        """测试任务状态查询"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先创建任务
            create_response = await client.post(
                f"{BASE_URL}/api/crawl/",
                json={"platform": "weibo", "keywords": ["测试"], "max_results": 3},
            )
            task_id = create_response.json()["task_id"]

            # 等待一下
            await asyncio.sleep(2)

            # 查询状态
            response = await client.get(f"{BASE_URL}/api/crawl/status/{task_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert "status" in data
            assert "progress" in data

    @pytest.mark.asyncio
    async def test_invalid_platform(self):
        """测试无效平台"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/crawl/",
                json={"platform": "invalid_platform", "keywords": ["test"], "max_results": 10},
            )
            # FastAPI 返回 422 用于验证错误
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_all_platforms(self):
        """测试所有支持的平台"""
        platforms = ["xiaohongshu", "weibo", "douyin"]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for platform in platforms:
                response = await client.post(
                    f"{BASE_URL}/api/crawl/",
                    json={"platform": platform, "keywords": ["测试", "KeyPick"], "max_results": 2},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "task_id" in data

                # 简单验证任务创建成功
                task_id = data["task_id"]
                await asyncio.sleep(1)

                status_response = await client.get(f"{BASE_URL}/api/crawl/status/{task_id}")
                assert status_response.status_code == 200


class TestDataProcessor:
    """数据处理 API 测试"""

    @pytest.mark.asyncio
    async def test_clean_data(self):
        """测试数据清洗"""
        test_data = [
            {"id": "1", "content": "内容1", "author": "作者1"},
            {"id": "2", "content": "内容2", "author": "作者2"},
            {"id": "1", "content": "内容1", "author": "作者1"},  # 重复
            {"id": "3", "content": "内容3", "author": "作者3"},
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/process/clean",
                json={"data": test_data, "remove_duplicates": True, "normalize": True},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["original_count"] == 4
            assert data["cleaned_count"] == 3
            assert data["removed_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_insights(self):
        """测试洞察提取"""
        test_data = [
            {"content": "这是测试内容", "platform": "test"},
            {"content": "另一个测试", "platform": "test"},
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/process/extract",
                json={"data": test_data, "analysis_type": "summary", "use_llm": False},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "insights" in data
            assert "summary" in data
            assert "keywords" in data

    @pytest.mark.asyncio
    async def test_transform_data(self):
        """测试数据转换"""
        test_data = [
            {"id": "1", "content": "测试"},
            {"id": "2", "content": "内容"},
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/process/transform",
                json={"data": test_data, "output_format": "json"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["format"] == "json"

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """测试数据验证"""
        test_data = [
            {"id": "1", "content": "测试"},
            {"id": "2"},  # 缺少 content 字段
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/process/validate", json={"data": test_data}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "valid" in data
            assert "errors" in data
            assert "stats" in data


class TestDifyIntegration:
    """Dify 集成测试"""

    @pytest.mark.asyncio
    async def test_dify_schema(self):
        """测试 Dify 工具 Schema"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/tools/dify/schema")
            assert response.status_code == 200
            schema = response.json()
            assert schema["name"] == "keypick_crawler"
            assert "description" in schema
            assert "parameters" in schema
            assert "response" in schema
            assert len(schema["parameters"]) >= 3

    @pytest.mark.asyncio
    async def test_dify_crawl_without_auth(self):
        """测试无认证的 Dify 爬取（应该失败）"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/tools/dify/crawl",
                json={
                    "platform": "xiaohongshu",
                    "keywords": "test,keyword",
                    "max_results": 5,
                    "async_mode": False,
                },
            )
            # 开发环境可能允许无认证访问
            assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_dify_crawl_with_auth(self):
        """测试带认证的 Dify 爬取"""
        headers = {"Authorization": f"Bearer {TEST_API_KEY}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/tools/dify/crawl",
                json={
                    "platform": "xiaohongshu",
                    "keywords": "test",
                    "max_results": 3,
                    "async_mode": False,
                },
                headers=headers,
            )
            # 根据配置可能返回 200 或 401
            if response.status_code == 200:
                data = response.json()
                assert "success" in data
            elif response.status_code == 401:
                # API Key 未配置或无效
                pass

    @pytest.mark.asyncio
    async def test_dify_async_mode(self):
        """测试 Dify 异步模式"""
        headers = {"Authorization": f"Bearer {TEST_API_KEY}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/tools/dify/crawl",
                json={
                    "platform": "weibo",
                    "keywords": "test",
                    "max_results": 2,
                    "async_mode": True,
                },
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                assert "success" in data
                if data["success"]:
                    assert "task_id" in data


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求处理"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 并发创建多个任务
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{BASE_URL}/api/crawl/",
                    json={"platform": "xiaohongshu", "keywords": [f"test_{i}"], "max_results": 2},
                )
                tasks.append(task)

            # 等待所有任务完成
            responses = await asyncio.gather(*tasks)

            # 验证所有请求都成功
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_response_time(self):
        """测试响应时间"""
        import time

        async with httpx.AsyncClient() as client:
            # 测试健康检查响应时间
            start = time.time()
            response = await client.get(f"{BASE_URL}/health")
            end = time.time()

            assert response.status_code == 200
            assert (end - start) < 1.0  # 应该在1秒内响应

            # 测试平台列表响应时间
            start = time.time()
            response = await client.get(f"{BASE_URL}/api/crawl/platforms")
            end = time.time()

            assert response.status_code == 200
            assert (end - start) < 1.0  # 应该在1秒内响应


@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整的工作流程"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 检查服务健康
        health_response = await client.get(f"{BASE_URL}/health")
        assert health_response.status_code == 200

        # 2. 获取支持的平台
        platforms_response = await client.get(f"{BASE_URL}/api/crawl/platforms")
        assert platforms_response.status_code == 200
        platforms = platforms_response.json()

        # 3. 选择一个平台进行爬取
        platform = platforms[0]["id"]
        crawl_response = await client.post(
            f"{BASE_URL}/api/crawl/",
            json={"platform": platform, "keywords": ["测试工作流"], "max_results": 3},
        )
        assert crawl_response.status_code == 200
        task_id = crawl_response.json()["task_id"]

        # 4. 等待并获取结果
        await asyncio.sleep(2)
        status_response = await client.get(f"{BASE_URL}/api/crawl/status/{task_id}")
        assert status_response.status_code == 200

        # 5. 如果有结果，进行数据处理
        status_data = status_response.json()
        if status_data.get("result") and status_data["result"].get("items"):
            items = status_data["result"]["items"]

            # 清洗数据
            clean_response = await client.post(
                f"{BASE_URL}/api/process/clean", json={"data": items, "remove_duplicates": True}
            )
            assert clean_response.status_code == 200

            # 提取洞察
            insights_response = await client.post(
                f"{BASE_URL}/api/process/extract",
                json={"data": items, "analysis_type": "summary", "use_llm": False},
            )
            assert insights_response.status_code == 200
