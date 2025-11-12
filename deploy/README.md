# KeyPick 部署文件

本目录包含 KeyPick 的生产部署配置和脚本。

## 📁 目录结构

```
deploy/
├── cloudflare/           # Cloudflare Workers 配置
│   ├── worker.js        # Workers 网关代码
│   └── wrangler.toml    # Wrangler 配置
├── fly/                 # Fly.io 配置
│   └── fly.toml        # Fly 应用配置
└── scripts/            # 部署脚本
    ├── deploy.sh       # 一键部署脚本
    ├── rollback.sh     # 回滚脚本
    └── monitor.sh      # 监控脚本
```

## 🚀 快速部署

### 前置要求
1. 安装 [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
2. 安装 [Wrangler](https://developers.cloudflare.com/workers/cli-wrangler/install-update)
3. 注册相关账号

### 一键部署
```bash
cd deploy/scripts
./deploy.sh
```

选择选项 1 进行完整部署（Fly.io + Cloudflare）。

## 🏗️ 架构说明

### Cloudflare Workers (API 网关)
- **作用**：全球 CDN、认证、缓存、队列
- **文件**：`cloudflare/worker.js`
- **配置**：`cloudflare/wrangler.toml`

主要功能：
- API 密钥验证
- 请求路由到后端
- 响应缓存（KV）
- 异步任务队列

### Fly.io (应用服务器)
- **作用**：运行 FastAPI 应用、执行爬虫任务
- **文件**：`fly/fly.toml`
- **区域**：新加坡（sin）或香港（hkg）

主要配置：
- 自动扩缩容（0-3 实例）
- 健康检查
- 持久存储卷
- 环境变量

## 🔧 配置说明

### 环境变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| KEYPICK_API_KEYS | API 认证密钥 | keypick-prod-001,keypick-prod-002 |
| INTERNAL_KEY | 内部通信密钥 | random-secret-key |
| BACKEND_URL | 后端服务地址 | https://keypick.fly.dev |
| SUPABASE_URL | Supabase 项目 URL | https://xxx.supabase.co |
| SUPABASE_ANON_KEY | Supabase 匿名密钥 | eyJxxx... |

### KV 命名空间
用于缓存和任务状态存储：
- 平台列表缓存（1小时）
- 任务状态缓存（24小时）
- 速率限制计数器

### 队列配置
用于异步爬虫任务：
- 队列名：keypick-crawler-queue
- 批次大小：10
- 超时：30秒

## 📝 部署步骤

### 1. 部署 Fly.io
```bash
# 登录
fly auth login

# 创建应用
fly launch --name keypick --region sin

# 设置密钥
fly secrets set KEYPICK_API_KEYS="your-keys"

# 部署
fly deploy
```

### 2. 部署 Cloudflare
```bash
# 登录
wrangler login

# 创建 KV
wrangler kv:namespace create "CACHE"

# 设置密钥
wrangler secret put KEYPICK_API_KEYS

# 部署
wrangler deploy --env production
```

## 🔄 更新和回滚

### 更新部署
```bash
# 更新 Fly.io
fly deploy

# 更新 Cloudflare
wrangler deploy --env production
```

### 回滚
```bash
./scripts/rollback.sh
```

## 📊 监控

### 使用监控脚本
```bash
./scripts/monitor.sh
```

功能：
- 检查服务状态
- 查看日志
- 性能测试
- 资源使用情况

### 在线监控
- Fly.io: `fly dashboard`
- Cloudflare: [Dashboard](https://dash.cloudflare.com)

## 🚨 故障排除

### 常见问题

#### 502 Bad Gateway
- 检查 Fly.io 是否运行：`fly status`
- 验证 BACKEND_URL 配置

#### 认证失败
- 检查 API 密钥配置
- 验证密钥格式（逗号分隔）

#### 性能问题
- 增加 Fly.io 实例：`fly scale count 2`
- 检查 Cloudflare 缓存命中率

## 💰 成本

| 服务 | 免费额度 | 超出后价格 |
|------|---------|-----------|
| Cloudflare Workers | 100k/天 | $0.5/百万 |
| Cloudflare KV | 100k 读/天 | $0.5/百万 |
| Fly.io | 3 个 VM | $2/月/VM |

预估月成本：**$0**（小规模使用）

## 📚 相关文档

- [完整部署指南](../DEPLOY_GUIDE.md)
- [Cloudflare 部署](../CLOUDFLARE_DEPLOYMENT.md)
- [Fly vs Railway 对比](../FLY_VS_RAILWAY.md)
- [部署方案对比](../DEPLOYMENT_COMPARISON.md)

## 🆘 获取帮助

1. 查看 [Fly.io 文档](https://fly.io/docs)
2. 查看 [Cloudflare Workers 文档](https://developers.cloudflare.com/workers)
3. 提交 Issue 到项目仓库