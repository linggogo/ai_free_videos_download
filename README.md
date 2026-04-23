# SaveAny - 万能视频下载器 + AI 视频总结

> 一键下载全网视频，AI 自动总结内容，支持 1800+ 平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 在线预览

![SaveAny 万能视频下载器界面](/docs/top.png)

## 核心功能

### 视频下载
- **1800+ 平台支持**：YouTube、Bilibili、抖音、TikTok、Twitter/X、Instagram 等
- **多清晰度下载**：支持 4K、1080p、720p 等多种分辨率
- **音频提取**：支持提取视频音轨为 M4A 格式
- **实时进度**：SSE 实时推送下载进度

### AI 智能分析
- **AI 视频总结**：自动提取字幕 + DeepSeek 大模型生成结构化 Markdown 摘要

![SaveAny万能视频AI总结界面](/docs/ai_summary.png)
- **思维导图**：基于总结内容生成交互式思维导图，支持导出 SVG/PNG

![SaveAny万能视频AI 思维导图界面](/docs/ai_mind.png)

- **字幕提取**：支持人工字幕和 AI 自动字幕，带时间戳展示
![SaveAny万能视频AI 字幕界面](/docs/ai_txt.png)
- **AI 问答**：基于视频字幕进行多轮互动问答
![SaveAny万能视频AI问答界面](/docs/ai_qa.png)
### 会员系统（接通国际支付Stripe）

- **免费版**：每日 3 次 AI 总结/思维导图，10 次 AI 问答
- **专业版**：¥19.9/月，所有 AI 功能无限使用

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 + Vite + Tailwind CSS v4 |
| 后端 | Python FastAPI |
| 下载引擎 | yt-dlp (148k+ Stars) |
| AI 模型 | DeepSeek (兼容 OpenAI SDK) |
| 思维导图 | markmap-lib + markmap-view |
| 支付 | Stripe Checkout |
| 数据库 | SQLite (用户认证) |

## 支持的平台

`YouTube` `Bilibili (B站)` `抖音` `TikTok` `Twitter/X` `Instagram` `Twitch` `快手` `Vimeo` `小红书` ...

**总计支持 1800+ 视频平台**

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- ffmpeg (`brew install ffmpeg`)

### 后端安装

```bash
cd backend
pip install -r requirements.txt

# 配置环境变量 (.env)
DEEPSEEK_API_KEY=your_api_key
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_PRICE_ID=price_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# 启动服务
python run.py
```

后端地址: http://localhost:8001

### 前端安装

```bash
cd frontend
npm install
npm run dev
```

前端地址: http://localhost:5173

## 使用方法

1. 打开网站，粘贴视频链接
2. 选择需要的清晰度/格式
3. 点击下载，支持实时进度查看
4. 下载完成后自动触发 AI 分析
5. 查看 AI 总结、思维导图、字幕文本
6. 可针对视频内容进行 AI 问答

## API 接口

### 基础视频 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/parse` | POST | 解析视频链接 |
| `/api/download` | POST | 开始下载 |
| `/api/progress/{task_id}` | GET(SSE) | 下载进度 |
| `/api/file/{task_id}` | GET | 下载文件 |

### AI 功能 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/subtitle` | POST | 提取字幕 |
| `/api/summarize` | POST(SSE) | AI 总结 |
| `/api/chat` | POST(SSE) | AI 问答 |

### 支付 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/payment/create-checkout-session` | POST | 创建支付 |
| `/api/payment/verify-session` | POST | 验证支付 |
| `/api/stripe/webhook` | POST | Webhook |

详细 API 文档请参考 [docs/api-reference.md](docs/api-reference.md)

## 项目结构

```
ai_free_videos_download/
├── backend/                     # Python 后端
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── auth.py             # JWT 认证
│   │   ├── database.py         # SQLite 用户 CRUD
│   │   ├── routers/
│   │   │   ├── video.py        # 视频解析/下载 API
│   │   │   ├── auth.py         # 用户认证 API
│   │   │   └── payment.py      # Stripe 支付 API
│   │   └── services/
│   │       ├── downloader.py   # yt-dlp 封装
│   │       ├── subtitle.py     # 字幕提取
│   │       ├── bilibili_subtitle.py  # B站专用
│   │       ├── ai_service.py   # DeepSeek AI
│   │       └── payment_service.py   # Stripe 业务
│   ├── downloads/              # 临时下载目录
│   └── requirements.txt
├── frontend/                    # Vue3 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── AppHeader.vue
│   │   │   ├── HeroSection.vue
│   │   │   ├── UrlInput.vue
│   │   │   ├── VideoResult.vue
│   │   │   ├── VideoAI.vue     # AI 分析面板
│   │   │   ├── AuthModal.vue
│   │   │   ├── FeatureSection.vue
│   │   │   ├── PricingSection.vue
│   │   │   └── FaqSection.vue
│   │   ├── stores/user.js     # 用户状态
│   │   └── api/                # API 封装
│   └── vite.config.js
└── docs/                        # 技术文档
    ├── technical-design.md
    └── api-reference.md
```

## SEO 优化

- Open Graph + Twitter Card 社交分享支持
- JSON-LD 结构化数据 (WebApplication, FAQPage, HowTo)
- robots.txt 支持所有主流爬虫
- llms.txt AI 爬虫协议文件
- 语义化 HTML + 无障碍优化

## 安全与隐私

- 不存储用户下载的视频文件（自动定期清理）
- 不收集用户隐私数据
- Stripe 安全支付
- JWT Token 认证

## 免责声明

本工具仅供学习交流使用，请勿用于商业牟利或下载受版权保护的内容。下载前请确保遵守当地法律法规和平台服务条款。

## License

MIT License

---

Built with ❤️ by linggogo