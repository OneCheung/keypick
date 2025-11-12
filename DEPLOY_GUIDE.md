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

### 1.5 部署应用
```bash
# 使用提供的 fly.toml
cp deploy/fly/fly.toml .

# 部署
fly deploy

# 检查状态
fly status
fly logs
```

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
# 创建生产环境 KV
wrangler kv:namespace create "CACHE"
# 记录输出的 id: "xxx"

# 创建开发环境 KV
wrangler kv:namespace create "CACHE" --preview
# 记录输出的 preview_id: "xxx"
```

### 2.3 创建队列
```bash
# 在 Cloudflare Dashboard 中创建
# 1. 进入 Workers & Pages > Queues
# 2. Create Queue
# 3. 名称：keypick-crawler-queue
```

### 2.4 更新配置文件
```bash
cd deploy/cloudflare

# 编辑 wrangler.toml
# 替换 YOUR_KV_NAMESPACE_ID 为实际 ID
# 替换 YOUR_KV_PREVIEW_ID 为实际 preview ID
```

### 2.5 设置密钥
```bash
# API 密钥（用于客户端认证）
wrangler secret put KEYPICK_API_KEYS
# 输入: keypick-prod-001,keypick-prod-002

# 内部通信密钥（与 Fly.io 通信）
wrangler secret put INTERNAL_KEY
# 输入: your-internal-secret-key（与 Fly.io 相同）
```

### 2.6 部署 Worker
```bash
# 部署到生产环境
wrangler deploy --env production

# 测试部署
curl https://keypick-gateway.YOUR-SUBDOMAIN.workers.dev/health
```

## 🔧 第三步：配置自定义域名（可选）

### 3.1 Cloudflare 自定义域名
```bash
# 在 Cloudflare Dashboard 中：
# 1. 进入你的域名
# 2. Workers Routes
# 3. Add route
#    - Route: api.keypick.com/*
#    - Worker: keypick-gateway
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
# Cloudflare Worker
curl https://api.keypick.com/health

# Fly.io 直接访问
curl https://keypick.fly.dev/health
```

### 4.2 测试 API 认证
```bash
# 无认证（应该失败）
curl -X GET https://api.keypick.com/api/crawl/platforms

# 有认证（应该成功）
curl -X GET https://api.keypick.com/api/crawl/platforms \
  -H "X-API-Key: keypick-prod-001"
```

### 4.3 测试爬虫任务
```bash
# 创建任务
curl -X POST https://api.keypick.com/api/crawl/ \
  -H "X-API-Key: keypick-prod-001" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xiaohongshu",
    "keywords": ["测试"],
    "max_results": 10
  }'

# 检查任务状态
curl -X GET https://api.keypick.com/api/crawl/status/{task_id} \
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

### 更新 Fly.io
```bash
# 更新代码后
fly deploy

# 查看部署历史
fly releases

# 回滚到上一版本
fly deploy --image registry.fly.io/keypick:v{number}
```

### 更新 Cloudflare Worker
```bash
# 更新 worker.js 后
wrangler deploy --env production

# 查看部署
wrangler deployments list

# 回滚（在 Dashboard 中操作）
```

## 💰 成本估算

### 月度成本
| 服务 | 免费额度 | 预估成本 |
|-----|---------|---------|
| Cloudflare Workers | 100k 请求/天 | $0 |
| Cloudflare KV | 100k 读/天 | $0 |
| Fly.io | 3 个 VM | $0 |
| Supabase | 500MB 数据库 | $0 |
| Upstash Redis | 10k 命令/天 | $0 |
| **总计** | - | **$0** |

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

- [ ] Fly.io 应用已创建并运行
- [ ] 环境变量已配置
- [ ] Cloudflare Worker 已部署
- [ ] KV 命名空间已创建
- [ ] API 密钥已设置
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
- Gateway: `https://api.keypick.com` (如果配置了域名)
- 或: `https://keypick-gateway.YOUR-SUBDOMAIN.workers.dev`

下一步：
1. 配置 Dify 工作流使用生产 API
2. 设置监控和告警
3. 优化性能和成本