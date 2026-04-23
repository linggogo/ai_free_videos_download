# SaveAny — 万能视频下载 & AI 视频分析

> 支持 1000+ 视频平台的免费下载工具，内置 AI 视频总结、字幕提取、思维导图、智能问答等增值功能。

## ✨ 功能特性

### 基础功能（v1.0）

- **万能链接解析** — 粘贴链接自动识别平台，获取视频标题、封面、时长、可用分辨率
- **多格式下载** — 支持选择不同分辨率和格式（MP4、M4A 音频提取等）
- **实时下载进度** — SSE 推送下载进度，显示速度和剩余时间
- **缩略图代理** — 绕过平台防盗链，正确显示视频封面
- **移动端适配** — 响应式设计，手机直接使用

### AI 增值功能（v1.1）

- **AI 视频总结** — 基于 DeepSeek 大模型，自动生成结构化 Markdown 摘要（流式输出）
- **字幕提取** — B 站优先平台 API（无需登录），其他平台 yt-dlp 通用方案
- **思维导图** — 基于 AI 总结内容，使用 markmap 渲染交互式 SVG 思维导图
- **AI 问答** — 基于视频字幕内容的多轮互动问答

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite 8 + Tailwind CSS v4 |
| 后端框架 | Python FastAPI 0.115 + Uvicorn |
| 下载引擎 | yt-dlp（支持 1000+ 网站） |
| AI 模型 | DeepSeek（兼容 OpenAI SDK） |
| HTTP 客户端 | httpx（缩略图代理、B 站 API 调用） |
| Markdown 渲染 | marked |
| 思维导图 | markmap-lib + markmap-view |
| 系统依赖 | ffmpeg（视频+音频流合并） |

## 📁 项目结构

```
ai_free_videos_download/
├── backend/                        # Python 后端
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口 + CORS
│   │   ├── routers/
│   │   │   └── video.py            # API 路由（解析/下载/字幕/AI）
│   │   └── services/
│   │       ├── downloader.py       # yt-dlp 下载服务封装
│   │       ├── douyin.py           # 抖音专用解析
│   │       ├── subtitle.py         # 通用字幕提取（yt-dlp）
│   │       ├── bilibili_subtitle.py # B 站字幕提取（dm/view API）
│   │       └── ai_service.py       # DeepSeek AI 总结/问答
│   ├── downloads/                  # 临时下载目录（自动清理）
│   ├── requirements.txt
│   └── run.py                      # 启动脚本
├── frontend/                       # Vue3 前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── AppHeader.vue       # 导航栏（毛玻璃暗色主题）
│   │   │   ├── HeroSection.vue     # 首屏展示
│   │   │   ├── UrlInput.vue        # URL 输入框
│   │   │   ├── VideoResult.vue     # 视频信息 + 下载面板
│   │   │   ├── VideoAI.vue         # AI 分析面板（4 个 Tab）
│   │   │   ├── FeatureSection.vue  # 功能亮点
│   │   │   ├── PricingSection.vue  # 定价展示
│   │   │   └── AppFooter.vue       # 页脚
│   │   └── api/
│   │       └── video.js            # API 调用封装（含 SSE 流式）
│   ├── vite.config.js              # Vite 配置（proxy → :8001）
│   └── package.json
└── docs/                           # 技术文档
    ├── technical-design.md
    └── api-reference.md
```

## 🚀 快速开始

### 前置依赖

- **Python** 3.10+
- **Node.js** 18+
- **ffmpeg**（yt-dlp 合并视频+音频必需）

```bash
# macOS 安装 ffmpeg
brew install ffmpeg
```

### 1. 克隆项目

```bash
git clone https://github.com/your-username/ai_free_videos_download.git
cd ai_free_videos_download
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python run.py
# 后端运行在 http://localhost:8001
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 4. 配置 AI 功能（可选）

AI 总结和问答功能需要配置 DeepSeek API Key：

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `DEEPSEEK_API_KEY` | 是（AI 功能） | — | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | API 基地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 模型名称 |

### 5. 打开浏览器

访问 http://localhost:5173 ，粘贴视频链接即可开始使用。

## 📡 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/parse` | POST | 解析视频链接，返回视频元信息 |
| `/api/download` | POST | 开始下载，返回 task_id |
| `/api/progress/{task_id}` | GET (SSE) | 实时下载进度推送 |
| `/api/file/{task_id}` | GET | 下载已完成的文件 |
| `/api/thumbnail` | GET | 代理获取缩略图（绕过防盗链） |
| `/api/subtitle` | POST | 提取视频字幕 |
| `/api/summarize` | POST (SSE) | AI 视频总结（流式） |
| `/api/chat` | POST (SSE) | AI 视频问答（流式） |
| `/health` | GET | 健康检查 |

详细的请求/响应格式请参考 [API 参考文档](docs/api-reference.md)。

## 🎨 UI 设计

采用暗色（Dark）主题风格：

- **背景**：深黑渐变（#0a0a0f / #12121a）
- **主色调**：蓝 → 紫 → 青渐变（#3b82f6 / #8b5cf6 / #06b6d4）
- **特效**：毛玻璃导航栏、发光边框、光晕背景装饰
- **字体**：Inter（Google Fonts）

## 🔧 字幕提取策略

```
用户输入 URL
  ├── 抖音 → 暂不支持字幕提取
  ├── B 站 → dm/view API（无需登录）
  │         ├── 成功 → 返回字幕
  │         └── 失败 → fallback 到 yt-dlp
  └── 其他平台 → yt-dlp 通用提取
```

- B 站通过 `x/v2/dm/view` 弹幕视图接口获取 CC 字幕和 AI 自动字幕
- 字幕语言优先级：zh-Hans > zh-CN > zh > zh-TW > en > ja > ko
- 自动过滤弹幕和直播聊天等无效类型

## 📝 开发路线

- [x] **阶段一**：项目初始化与基础框架搭建
- [x] **阶段二**：yt-dlp 服务封装 + 核心 API 开发
- [x] **阶段三**：前端 UI 页面开发（暗色主题）
- [x] **阶段四**：联调测试与交互优化
- [x] **阶段五**：AI 视频总结与增值功能
- [ ] **阶段六**：批量下载、字幕导出、用户认证、Stripe 支付

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 强大的视频下载引擎

## ⚠️ 免责声明

本工具仅供个人学习和研究使用。请尊重视频创作者的版权，不要将下载的内容用于商业用途或未经授权的传播。使用本工具即表示您同意自行承担相关法律责任。
