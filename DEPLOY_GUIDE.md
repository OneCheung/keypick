# KeyPick 生产部署指南 (Cloudflare Workers + Fly.io)

## 🏗️ 架构概览

```
用户请求
    ↓
[Cloudflare Workers] - 全球 CDN 网关
    • API 认证
    • 请求路由
    • 响应缓存
    • 队列管理
    ↓
[Fly.io] - 应用服务器
    • FastAPI 应用
    • 爬虫任务执行
    • 数据处理
    ↓
[外部服务]
    • Supabase - 数据库
    • Upstash Redis - 缓存
    • Dify - 工作流
```

## 📋 前置准备

### 必需账号
- [ ] [Cloudflare](https://dash.cloudflare.com/sign-up) 账号
- [ ] [Fly.io](https://fly.io/app/sign-up) 账号
- [ ] [Supabase](https://supabase.com) 账号（可选）
- [ ] [Upstash](https://upstash.com) 账号（可选）

### 工具安装
```bash
# 安装 Cloudflare Wrangler
npm install -g wrangler

# 安装 Fly CLI
curl -L https://fly.io/install.sh | sh

# 验证安装
wrangler --version
fly version
```

## 🚀 第一步：部署 Fly.io 后端

### 1.1 登录 Fly.io
```bash
fly auth login
```

### 1.2 创建 Fly 应用
```bash
cd keypick
fly launch --name keypick --region sin --no-deploy

# 选择配置：
# - Organization: personal
# - Region: sin (Singapore) 或 hkg (Hong Kong)
# - Postgres: No
# - Redis: No
```

### 1.3 配置环境变量
```bash
# 设置密钥（这些不会在日志中显示）
fly secrets set KEYPICK_API_KEYS="keypick-prod-001,keypick-prod-002"
fly secrets set INTERNAL_KEY="your-internal-secret-key"

# 可选：Supabase 配置
fly secrets set SUPABASE_URL="https://your-project.supabase.co"
fly secrets set SUPABASE_ANON_KEY="your-anon-key"
fly secrets set SUPABASE_SERVICE_KEY="your-service-key"

# 可选：Redis 配置
fly secrets set REDIS_URL="redis://default:password@redis-host:6379"
```

### 1.4 创建持久存储卷
```bash
fly volumes create keypick_data --region sin --size 1
```

### 1.5 配置 GitHub Actions 自动部署（推荐）

#### 1.5.1 准备 fly.toml
```bash
# 首次部署：将模板文件复制到项目根目录（GitHub Actions 需要）
# 注意：deploy/fly/fly.toml 是模板文件，根目录的 fly.toml 是实际使用的配置
cp deploy/fly/fly.toml .
git add fly.toml
git commit -m "Add fly.toml for deployment"
```

> **说明**：
> - `deploy/fly/fly.toml`：部署配置模板文件，作为参考和初始配置
> - `fly.toml`（根目录）：实际使用的配置文件，会被提交到 git
> - 首次部署后，后续修改应直接编辑根目录的 `fly.toml`
> - 如果根目录的 `fly.toml` 丢失，可以从 `deploy/fly/fly.toml` 恢复

#### 1.5.2 获取 Fly.io API Token
```bash
# 在 Fly.io Dashboard 中获取
# 1. 访问 https://fly.io/dashboard/account/tokens
# 2. 创建新的 Access Token
# 3. 复制 token（只显示一次，请妥善保存）
```

#### 1.5.3 配置 GitHub Secrets
在 GitHub 仓库中配置 Secrets：
1. 进入仓库 Settings > Secrets and variables > Actions
2. 点击 "New repository secret"
3. 添加以下 Secrets：

   **Fly.io 部署：**
   - **Name**: `FLY_API_TOKEN`
   - **Value**: 你的 Fly.io API Token

   **Cloudflare Workers 部署（可选）：**
   - **Name**: `CLOUDFLARE_API_TOKEN`
   - **Value**: 你的 Cloudflare API Token（见下方获取方法）
   - **Name**: `CLOUDFLARE_ACCOUNT_ID`
   - **Value**: 你的 Cloudflare Account ID（见下方获取方法）

#### 1.5.4 首次手动部署（初始化）
```bash
# 首次部署需要手动执行一次
# 注意：fly deploy 会使用本地代码构建和部署，不是 GitHub 的代码
# 确保本地代码是最新的，或者先提交到 GitHub
fly deploy

# 检查状态
fly status
fly logs
```

> **重要提示**：
> - `fly deploy`（本地命令）：使用**本地代码**构建 Docker 镜像并部署
> - GitHub Actions 自动部署：使用 **GitHub 仓库的代码**构建和部署
> - 如果本地有未提交的修改，`fly deploy` 会部署这些修改
> - 建议：使用 GitHub Actions 自动部署，确保部署的是已提交的代码

#### 1.5.5 自动部署
配置完成后，每次推送到 `main` 分支时，GitHub Actions 会自动：
- 运行 CI 测试
- 构建 Docker 镜像
- 部署到 Fly.io（当相关文件变更时）

查看部署状态：
- GitHub Actions: 仓库的 Actions 标签页
- Fly.io: `fly status` 或 Dashboard

> **注意**：Cloudflare Workers 的自动部署需要单独配置（见 2.6 节）

### 1.6 获取应用 URL
```bash
fly info
# 记录下 Hostname: keypick.fly.dev
```

## 🌐 第二步：配置 Cloudflare Workers

### 2.1 登录 Cloudflare
```bash
wrangler login
```

### 2.2 创建 KV 命名空间
```bash
# 创建生产环境 KV（Wrangler 4.x 使用空格分隔命令）
wrangler kv namespace create "CACHE"
# 记录输出的 id: "xxx"

# 创建开发环境 KV
wrangler kv namespace create "CACHE" --preview
# 记录输出的 preview_id: "xxx"
```

### 2.3 配置队列（可选，需要 Workers Paid 计划）

> **注意**：Cloudflare Queues 需要 Workers Paid 计划（$5/月起）。如果使用免费计划，可以跳过此步骤，应用仍可正常工作，但异步任务处理功能会受限。

#### 方案 A：使用 Queues（推荐，需要付费计划）

1. **升级到 Workers Paid 计划**
   - 访问 [Cloudflare Dashboard](https://dash.cloudflare.com)
   - 进入 Workers & Pages > Overview
   - 点击 "Upgrade" 升级到 Paid 计划（$5/月）

2. **创建队列**
   ```bash
   # 在 Cloudflare Dashboard 中创建
   # 1. 进入 Workers & Pages > Queues
   # 2. Enable Queues（首次使用需要启用）
   # 3. Create Queue
   # 4. 名称：keypick-crawler-queue
   ```

3. **保持 wrangler.toml 中的队列配置**（已默认配置）

#### 方案 B：不使用 Queues（免费计划）

如果使用免费计划，可以跳过队列配置：

1. **注释掉 wrangler.toml 中的队列配置**
   ```toml
   # Queue for async tasks (requires Workers Paid plan)
   # [[queues.producers]]
   # binding = "CRAWLER_QUEUE"
   # queue = "keypick-crawler-queue"
   #
   # [[queues.consumers]]
   # queue = "keypick-crawler-queue"
   # max_batch_size = 10
   # max_batch_timeout = 30
   ```

2. **功能说明**
   - ✅ API 认证、路由、缓存等功能正常
   - ✅ 爬虫任务可以创建，但会同步处理（可能超时）
   - ❌ 异步任务队列处理不可用

### 2.4 更新配置文件
```bash
cd deploy/cloudflare

# 编辑 wrangler.toml
# 替换 YOUR_KV_NAMESPACE_ID 为实际 ID
# 替换 YOUR_KV_PREVIEW_ID 为实际 preview ID
```

### 2.5 设置密钥

> **重要**：由于配置了多个环境（development 和 production），必须为每个环境单独设置 secrets。

```bash
# API 密钥（用于客户端认证）- 为 production 环境设置
wrangler secret put KEYPICK_API_KEYS --env production
# 输入: keypick-prod-001,keypick-prod-002（使用你自己的 API keys）

# 内部通信密钥（与 Fly.io 通信）- 为 production 环境设置
wrangler secret put INTERNAL_KEY --env production
# 输入: your-internal-secret-key（与 Fly.io 相同，使用你自己的密钥）

# 可选：为 development 环境设置（用于本地测试）
# wrangler secret put KEYPICK_API_KEYS --env development
# wrangler secret put INTERNAL_KEY --env development
```

### 2.6 配置 GitHub Actions 自动部署（推荐）

#### 2.6.1 获取 Cloudflare API Token 和 Account ID

**获取 API Token：**
1. 访问 [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. 点击 "Create Token"
3. 使用 "Edit Cloudflare Workers" 模板，或自定义权限：
   - Account: Workers Scripts: Edit
   - Account: Workers KV Storage: Edit
   - Account: Account Settings: Read
4. 复制生成的 Token（只显示一次，请妥善保存）

**获取 Account ID：**
1. 访问 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 在右侧边栏可以看到 Account ID
3. 或从 URL 中获取：`https://dash.cloudflare.com/{account_id}/...`

#### 2.6.2 配置 GitHub Secrets

在 GitHub 仓库中配置 Secrets（如果 1.5.3 中未配置）：
1. 进入仓库 Settings > Secrets and variables > Actions
2. 点击 "New repository secret"
3. 添加以下 Secrets：
   - **Name**: `CLOUDFLARE_API_TOKEN`
   - **Value**: 你的 Cloudflare API Token
   - **Name**: `CLOUDFLARE_ACCOUNT_ID`
   - **Value**: 你的 Cloudflare Account ID

#### 2.6.3 首次手动部署（初始化）

```bash
cd deploy/cloudflare

# 部署到生产环境
wrangler deploy --env production

# 测试部署（使用 Workers 默认域名或自定义域名）
curl https://keypick-gateway-production.YOUR-SUBDOMAIN.workers.dev/health
# 或使用自定义域名（如果已配置）
curl https://keypick.example.com/health
```

#### 2.6.4 自动部署

配置完成后，每次修改 `deploy/cloudflare/` 目录下的文件并推送到 `main` 分支时，GitHub Actions 会自动：
- 安装 Wrangler CLI
- 部署 Worker 到 Cloudflare
- 显示部署状态

查看部署状态：
- GitHub Actions: 仓库的 Actions 标签页
- Cloudflare Dashboard: Workers & Pages > keypick-gateway-production

## 🔧 第三步：配置自定义域名（可选）

### 3.1 Cloudflare 自定义域名
```bash
# 在 Cloudflare Dashboard 中：
# 1. 进入你的域名（例如：example.com）
# 2. Workers Routes
# 3. Add route
#    - Route: keypick.example.com/*
#    - Worker: keypick-gateway-production
```

### 3.2 Fly.io 自定义域名
```bash
# 添加证书
fly certs add api-backend.keypick.com

# 获取 DNS 记录
fly certs show api-backend.keypick.com
# 添加显示的 CNAME 记录到 DNS
```

## 🧪 第四步：测试部署

### 4.1 测试健康检查
```bash
# Cloudflare Worker（自定义域名，如果已配置）
curl https://keypick.example.com/health

# 或使用 Workers 默认域名
curl https://keypick-gateway-production.YOUR-SUBDOMAIN.workers.dev/health

# Fly.io 直接访问
curl https://keypick.fly.dev/health
```

### 4.2 测试 API 认证
```bash
# 无认证（应该失败）
curl -X GET https://keypick.example.com/api/crawl/platforms

# 有认证（应该成功）
curl -X GET https://keypick.example.com/api/crawl/platforms \
  -H "X-API-Key: keypick-prod-001"
```

### 4.3 测试爬虫任务
```bash
# 创建任务
curl -X POST https://keypick.example.com/api/crawl/ \
  -H "X-API-Key: keypick-prod-001" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xiaohongshu",
    "keywords": ["测试"],
    "max_results": 10
  }'

# 检查任务状态
curl -X GET https://keypick.example.com/api/crawl/status/{task_id} \
  -H "X-API-Key: keypick-prod-001"
```

## 📊 第五步：监控和日志

### 5.1 Cloudflare Analytics
```bash
# 查看 Worker 分析
wrangler tail

# 或在 Dashboard 中查看：
# Workers & Pages > keypick-gateway > Analytics
```

### 5.2 Fly.io 监控
```bash
# 实时日志
fly logs

# SSH 进入容器
fly ssh console

# 查看指标
fly status
```

### 5.3 设置告警（可选）
```bash
# Fly.io 健康检查已配置
# Cloudflare 可以设置 Worker 告警
```

## 🔄 更新和回滚

### 更新 Fly.io（自动部署）

如果已配置 GitHub Actions（推荐方式）：
```bash
# 1. 提交代码更改
git add .
git commit -m "Update application"
git push origin main

# 2. GitHub Actions 会自动触发部署
# 查看部署进度：GitHub 仓库 > Actions 标签页
```

### 手动部署 Fly.io（可选）

如果需要手动部署：
```bash
# 确保 fly.toml 在根目录
cp deploy/fly/fly.toml .

# 部署
fly deploy

# 查看部署历史
fly releases
```

### 回滚 Fly.io
```bash
# 查看部署历史
fly releases

# 回滚到指定版本
fly releases rollback <version>

# 或回滚到上一版本
fly releases rollback
```

### 更新 Cloudflare Worker（自动部署）

如果已配置 GitHub Actions（推荐方式）：
```bash
# 1. 修改 deploy/cloudflare/ 目录下的文件
# 2. 提交代码更改
git add deploy/cloudflare/
git commit -m "Update Cloudflare Worker"
git push origin main

# 3. GitHub Actions 会自动触发部署
# 查看部署进度：GitHub 仓库 > Actions 标签页
```

### 手动部署 Cloudflare Worker（可选）

如果需要手动部署：
```bash
cd deploy/cloudflare

# 部署到生产环境
wrangler deploy --env production

# 查看部署历史
wrangler deployments list --env production

# 回滚（在 Dashboard 中操作）
# 1. 进入 Cloudflare Dashboard
# 2. Workers & Pages > keypick-gateway-production
# 3. 选择之前的版本进行回滚
```

## 💰 成本估算

### 月度成本（免费计划）
| 服务 | 免费额度 | 预估成本 |
|-----|---------|---------|
| Cloudflare Workers | 100k 请求/天 | $0 |
| Cloudflare KV | 100k 读/天 | $0 |
| Cloudflare Queues | ❌ 需要付费计划 | - |
| Fly.io | 3 个 VM | $0 |
| Supabase | 500MB 数据库 | $0 |
| Upstash Redis | 10k 命令/天 | $0 |
| **总计（不含 Queues）** | - | **$0** |

### 付费功能（可选）
- **Cloudflare Workers Paid 计划**: $5/月
  - 包含 Queues 功能
  - 更高的请求限制
  - 更长的执行时间

### 扩展成本（如果超出免费额度）
- Cloudflare Workers: $0.50/百万请求
- Fly.io: ~$2/月/VM
- Supabase: $25/月 Pro

## 🚨 故障排除

### 问题：502 Bad Gateway
```bash
# 检查 Fly.io 是否运行
fly status

# 检查 Worker 配置的 BACKEND_URL
wrangler secret list
```

### 问题：认证失败
```bash
# 验证 API 密钥配置
fly secrets list
wrangler secret list
```

### 问题：任务超时
```bash
# 增加 Fly.io 实例内存
fly scale memory 1024

# 或增加实例数量
fly scale count 2
```

## 🔒 安全建议

1. **API 密钥管理**
   - 定期轮换 API 密钥
   - 使用不同环境的不同密钥
   - 监控异常使用

2. **内部通信**
   - INTERNAL_KEY 只用于 Workers 和 Fly.io 之间
   - 使用 HTTPS 加密所有通信

3. **数据保护**
   - 敏感数据存储在 Supabase
   - 使用 Redis 仅缓存非敏感数据

## 📝 部署清单

### Fly.io 后端
- [ ] Fly.io 应用已创建并运行
- [ ] 环境变量和 Secrets 已配置
- [ ] 持久存储卷已创建
- [ ] `fly.toml` 已复制到项目根目录
- [ ] GitHub Secrets 已配置（`FLY_API_TOKEN`）
- [ ] GitHub Actions 工作流已测试
- [ ] 首次手动部署成功
- [ ] 自动部署流程验证通过

### Cloudflare Workers
- [ ] Cloudflare Worker 已部署
- [ ] KV 命名空间已创建
- [ ] KV namespace IDs 已更新到 wrangler.toml
- [ ] API 密钥已设置（通过 `wrangler secret put`）
- [ ] GitHub Secrets 已配置（`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`）
- [ ] GitHub Actions 工作流已测试
- [ ] 队列已创建（可选，需要 Workers Paid 计划）
- [ ] 自定义域名已配置（可选，例如：keypick.example.com）

### 测试验证
- [ ] 健康检查通过
- [ ] API 认证测试通过
- [ ] 爬虫任务测试通过
- [ ] 监控已设置
- [ ] 文档已更新

## 🆘 支持

如遇到问题：
1. 查看 [Fly.io 文档](https://fly.io/docs)
2. 查看 [Cloudflare Workers 文档](https://developers.cloudflare.com/workers)
3. 提交 Issue 到项目仓库

## 🎉 完成！

恭喜！KeyPick 已成功部署到生产环境。

访问你的 API：
- Gateway: `https://keypick.example.com` (如果配置了自定义域名)
- 或: `https://keypick-gateway-production.YOUR-SUBDOMAIN.workers.dev` (Workers 默认域名)

下一步：
1. 配置 Dify 工作流使用生产 API
2. 设置监控和告警
3. 优化性能和成本