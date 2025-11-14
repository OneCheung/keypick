# 小红书权限问题解决方案

## 问题描述

错误信息：`您当前登录的账号没有权限访问`

这个错误通常发生在以下情况：
1. Cookie过期或无效
2. 账号被限制访问
3. 反爬虫机制检测
4. 登录状态异常

## 解决方案

### 方案1：清除Cookie并重新登录（推荐）

```bash
# 运行修复脚本
cd /Users/admin/Downloads/OpenSource/keypick
python scripts/fix_xhs_permission.py
```

选择选项2，按照提示完成手动登录。

### 方案2：修改MediaCrawler配置

编辑 `MediaCrawler/config/base_config.py`：

```python
# 关键配置
PLATFORM = "xhs"
LOGIN_TYPE = "qrcode"  # 改为扫码登录
HEADLESS = False  # 显示浏览器界面
ENABLE_CDP_MODE = True  # 使用CDP模式
SAVE_LOGIN_STATE = True  # 保存登录状态

# 降低爬取频率
CRAWLER_MAX_NOTES_COUNT = 10  # 减少单次爬取数量
```

### 方案3：使用增强的适配器

在 `api/services/crawler_service.py` 中使用新的适配器：

```python
from api.services.mediacrawler_adapter_v2 import get_enhanced_mediacrawler_adapter

# 在 CrawlerService.__init__ 中
self.adapter = get_enhanced_mediacrawler_adapter()
```

### 方案4：手动登录步骤

1. **清除旧的登录状态**
   ```bash
   rm -rf MediaCrawler/browser_data/xhs_browser_context/
   ```

2. **启动浏览器并登录**
   ```bash
   cd MediaCrawler
   python main.py
   ```

3. **登录注意事项**
   - 使用手机扫码登录
   - 完成所有验证（滑块验证等）
   - 确保能正常浏览内容
   - 不要立即关闭浏览器

4. **测试搜索功能**
   - 在浏览器中搜索"美食"
   - 确保能看到搜索结果
   - 浏览几个笔记确保正常

### 方案5：降级到Mock数据

如果实际爬取持续失败，系统会自动降级到Mock数据：

```python
# 在 api/services/crawler_service.py 中已实现
# 当 MediaCrawler 失败时，自动使用 Mock 数据
```

## 预防措施

### 1. 合理控制爬取频率

```python
# 添加延迟
import time
import random

# 在每次请求之间添加随机延迟
time.sleep(random.uniform(2, 5))
```

### 2. 使用代理IP

```python
# 在 MediaCrawler/config/base_config.py
ENABLE_IP_PROXY = True
IP_PROXY_POOL_COUNT = 5
```

### 3. 轮换User-Agent

```python
# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    # 更多User-Agent
]
```

### 4. 定期更新Cookie

建议每天或每几天重新登录一次，保持Cookie新鲜。

## 监控和日志

### 查看日志

```bash
# 查看MediaCrawler日志
tail -f MediaCrawler/logs/crawler.log

# 查看KeyPick日志
tail -f logs/keypick.log
```

### 错误处理

在代码中添加更详细的错误处理：

```python
try:
    result = await crawler.crawl()
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    # 触发重新登录流程
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # 降级到Mock数据
```

## 长期解决方案

1. **实现账号池**：多个账号轮换使用
2. **分布式爬取**：多台机器分散请求
3. **API接入**：考虑官方API或第三方数据服务
4. **智能调度**：根据时间段和频率智能调度爬取任务

## 测试命令

```bash
# 测试基础爬取
curl -X POST http://localhost:8000/api/crawl/ \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xiaohongshu",
    "keywords": ["测试"],
    "max_results": 5
  }'

# 查看任务状态
curl http://localhost:8000/api/crawl/status/{task_id}
```

## 联系支持

如果问题持续存在：
1. 检查MediaCrawler的GitHub Issues
2. 查看小红书的使用条款更新
3. 考虑使用其他平台进行测试

## 更新记录

- 2024-11-14: 初始版本
- 增加增强适配器
- 添加自动降级策略
- 完善错误处理机制