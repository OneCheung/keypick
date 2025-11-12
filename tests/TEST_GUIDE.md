# KeyPick 测试指南

## 目录结构

```
tests/
├── TEST_GUIDE.md          # 本文档
├── test_api.py           # 基础 API 单元测试
├── test_integration.py   # 完整集成测试套件
└── conftest.py          # pytest 配置（如需要）
```

## 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装测试依赖
uv pip install pytest pytest-asyncio pytest-cov httpx

# 启动 API 服务
uvicorn api.main:app --reload
```

### 2. 运行测试

#### 运行所有测试
```bash
# 在项目根目录执行
pytest tests/ -v

# 或带覆盖率报告
pytest tests/ --cov=api --cov-report=html
```

#### 运行特定测试
```bash
# 只运行单元测试
pytest tests/test_api.py -v

# 只运行集成测试
pytest tests/test_integration.py -v

# 运行特定测试类
pytest tests/test_integration.py::TestCrawlerAPI -v

# 运行特定测试方法
pytest tests/test_integration.py::TestCrawlerAPI::test_get_platforms -v
```

#### 并行运行测试（更快）
```bash
# 安装 pytest-xdist
uv pip install pytest-xdist

# 使用 4 个进程并行运行
pytest tests/ -n 4
```

## 测试类别

### 1. 健康检查测试 (`TestHealthCheck`)
- ✅ 健康检查端点
- ✅ 根路径端点
- ✅ API 信息端点

### 2. 爬虫 API 测试 (`TestCrawlerAPI`)
- ✅ 获取平台列表
- ✅ 创建爬取任务
- ✅ 查询任务状态
- ✅ 无效平台处理
- ✅ 所有平台测试

### 3. 数据处理测试 (`TestDataProcessor`)
- ✅ 数据清洗（去重）
- ✅ 洞察提取
- ✅ 数据转换
- ✅ 数据验证

### 4. Dify 集成测试 (`TestDifyIntegration`)
- ✅ Schema 获取
- ✅ 无认证调用
- ✅ 带认证调用
- ✅ 异步模式

### 5. 性能测试 (`TestPerformance`)
- ✅ 并发请求处理
- ✅ 响应时间测试

### 6. 完整工作流测试
- ✅ 端到端测试
- ✅ 完整数据流程

## 测试配置

### 环境变量配置

创建 `.env.test` 文件用于测试：
```env
ENVIRONMENT=testing
DEBUG=True
KEYPICK_API_KEYS=keypick-test-001,keypick-test-002
```

### 测试时使用特定配置
```bash
# 使用测试配置文件
cp .env.test .env
pytest tests/
```

## 测试覆盖率

### 生成覆盖率报告
```bash
# 生成终端报告
pytest tests/ --cov=api --cov-report=term

# 生成 HTML 报告
pytest tests/ --cov=api --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html  # macOS
# 或
xdg-open htmlcov/index.html  # Linux
```

### 覆盖率目标
- 核心功能：> 80%
- 工具函数：> 70%
- 错误处理：> 60%

## 测试标记

使用 pytest 标记来组织测试：

```python
# 在测试中添加标记
@pytest.mark.slow
async def test_large_crawl():
    pass

@pytest.mark.integration
async def test_full_workflow():
    pass
```

运行特定标记的测试：
```bash
# 只运行快速测试（跳过慢速测试）
pytest tests/ -m "not slow"

# 只运行集成测试
pytest tests/ -m integration
```

## 持续集成 (CI)

### GitHub Actions 配置

测试已集成到 CI 中，每次推送都会自动运行：
- 单元测试
- 集成测试
- 代码覆盖率报告

查看 `.github/workflows/ci.yml` 了解详情。

## 调试测试

### 1. 打印调试信息
```bash
# 显示所有打印输出
pytest tests/ -s

# 显示详细信息
pytest tests/ -vv
```

### 2. 进入调试器
```python
# 在测试中添加断点
import pdb; pdb.set_trace()
```

### 3. 只运行失败的测试
```bash
# 运行上次失败的测试
pytest tests/ --lf

# 先运行失败的测试，然后运行其他
pytest tests/ --ff
```

## 测试数据

### Mock 数据
当前使用 Mock 数据进行测试，位于：
- `api/services/crawler_service.py` 中的 `_crawl_*` 方法

### 测试账号
- API Key: `keypick-test-001`
- 平台: `xiaohongshu`, `weibo`, `douyin`

## 常见问题

### Q: 测试失败：连接被拒绝
**A:** 确保 API 服务正在运行：
```bash
uvicorn api.main:app --reload
```

### Q: 测试失败：401 Unauthorized
**A:** 在 `.env` 中配置测试 API Key：
```env
KEYPICK_API_KEYS=keypick-test-001
```

### Q: 测试太慢
**A:** 使用并行测试或跳过慢速测试：
```bash
# 并行运行
pytest tests/ -n auto

# 跳过慢速测试
pytest tests/ -m "not slow"
```

### Q: 如何测试真实爬虫？
**A:** 配置 MediaCrawler 后，修改 `crawler_service.py` 中的实现。

## 测试最佳实践

1. **独立性**：每个测试应该独立运行
2. **可重复**：测试结果应该可重复
3. **快速**：单元测试应该快速完成
4. **清晰**：测试名称应该描述测试内容
5. **完整**：测试应该覆盖正常和异常情况

## 测试检查清单

在提交代码前，确保：

- [ ] 所有测试通过：`pytest tests/`
- [ ] 代码覆盖率达标：`pytest tests/ --cov=api`
- [ ] 代码格式正确：`black api/ tests/`
- [ ] 代码检查通过：`ruff check api/ tests/`
- [ ] 类型检查通过：`mypy api/`

## 扩展测试

### 添加新测试

1. 在相应的测试类中添加新方法
2. 使用 `async def test_` 前缀
3. 添加适当的断言
4. 运行测试验证

### 测试新功能

1. 先写测试（TDD）
2. 实现功能
3. 确保测试通过
4. 重构代码

## 联系方式

如有测试相关问题，请：
1. 查看本文档
2. 查看测试代码注释
3. 提交 Issue 到项目仓库