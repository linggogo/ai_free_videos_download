# 万能视频下载网站 - 技术设计文档

## 一、整体架构

```
前端 (Vue3 + Vite + Tailwind CSS v4)       -- 独立前端项目，开发时代理到后端
  |                                           - VideoAI.vue（AI 分析面板：总结/字幕/思维导图/问答）
  |                                           - markmap（思维导图渲染）/ marked（Markdown 渲染）
  |
FastAPI 后端 (Python)                       -- 提供 REST API + SSE
  |                                           - subtitle.py（通用字幕提取 yt-dlp）
  |                                           - bilibili_subtitle.py（B站 dm/view API 专用字幕提取）
  |                                           - ai_service.py（DeepSeek 大模型 AI 总结/问答）
  |
yt-dlp (核心下载引擎, 148k+ stars)           -- 封装为服务层
  |
DeepSeek API (AI 大模型)                     -- 流式 AI 总结 + 问答
```

**技术选型：**
- 前端：Vue3 + Vite v8 + Tailwind CSS v4（前后端分离，独立开发和构建）
- 后端：Python FastAPI 0.115+（轻量、高性能、自带异步、CORS 支持）
- 下载引擎：yt-dlp 2024.8+（支持 1000+ 网站）
- AI 模型：DeepSeek（兼容 OpenAI SDK，通过 openai Python 库调用）
- HTTP 客户端：httpx（用于后端缩略图代理、B站 API 调用）
- 思维导图：markmap-lib + markmap-view（Markdown → 交互式 SVG 思维导图）
- Markdown 渲染：marked（AI 总结流式输出 Markdown → HTML）
- 系统依赖：ffmpeg（yt-dlp 合并视频+音频流必需）
- 无数据库，文件临时存储 + 自动清理

## 二、核心功能

### 基础功能（v1.0）
1. **视频链接解析** - 粘贴链接，自动识别平台，获取视频信息（标题、封面、时长、分辨率列表）
2. **多格式下载** - 支持选择不同分辨率/格式（MP4、MP3 音频提取等）
3. **实时下载进度** - 通过 SSE 推送下载进度到前端
4. **移动端适配** - 响应式设计，手机直接使用

### AI 增值功能（v1.1）[已完成]
5. **AI 视频总结（P0）** - 自动提取字幕，调用 DeepSeek 大模型生成结构化 Markdown 摘要（流式输出）
6. **字幕/转录展示（P0）** - 展示带时间戳的字幕文本，支持人工字幕和自动字幕
7. **思维导图（P1）** - 基于 AI 总结的 Markdown 内容，使用 markmap 渲染交互式思维导图
8. **AI 问答（P2）** - 基于视频字幕内容的互动问答，支持多轮对话

### 会员支付功能（v1.2）[已完成]
9. **Stripe 会员支付** - 支持月度会员订阅，一次性付款模式
10. **用户认证系统** - 邮箱注册/登录，JWT Token 认证
11. **VIP 会员状态** - subscription_status 激活，AI 功能不限量

## 三、UI 设计方案

暗色（Dark）主题风格，参考 ai.codefather.cn/painting：
- 背景色：#0a0a0f（深黑）/ #12121a（卡片）/ #1e1e2e（边框）
- 主色调：#3b82f6（蓝）/ #8b5cf6（紫）/ #06b6d4（青）
- 渐变强调：蓝→紫→青（用于 CTA 按钮、标题渐变文字）
- 文字：#f1f5f9（主）/ #94a3b8（辅助）/ #64748b（弱化）
- 字体：Inter（Google Fonts）
- 特效：毛玻璃导航栏、发光边框、光晕背景装饰
- 页面结构：Header -> Hero -> URL输入 -> 结果卡片 -> 功能亮点 -> 定价 -> Footer

## 四、项目目录结构

```
ai_free_videos_download/
├── backend/                        # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口 + CORS（端口 8001）
│   │   ├── auth.py                 # JWT 认证工具 + 依赖注入
│   │   ├── database.py             # SQLite 数据库 + 用户 CRUD
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── video.py            # 视频解析/下载/字幕/AI总结 API
│   │   │   ├── auth.py             # 用户注册/登录 API
│   │   │   └── payment.py          # Stripe 支付 + Webhook API
│   │   └── services/
│   │       ├── downloader.py       # yt-dlp 封装服务
│   │       ├── douyin.py           # 抖音专用解析（无Cookie下载）
│   │       ├── subtitle.py         # 通用字幕提取（yt-dlp + 平台优先）
│   │       ├── bilibili_subtitle.py # B站专用字幕提取（dm/view API）
│   │       ├── ai_service.py        # DeepSeek AI 总结/问答服务
│   │       └── payment_service.py   # Stripe 支付业务逻辑
│   ├── downloads/                   # 临时下载目录（自动清理）
│   ├── saveany.db                  # SQLite 数据库文件
│   ├── .env                        # 环境变量配置
│   ├── requirements.txt
│   └── run.py
├── frontend/                       # Vue3 前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── stores/
│   │   │   └── user.js             # 用户状态管理（Vue3 reactive）
│   │   ├── components/
│   │   │   ├── AppHeader.vue        # 导航栏
│   │   │   ├── HeroSection.vue      # 首屏 Hero
│   │   │   ├── UrlInput.vue        # URL 输入框
│   │   │   ├── VideoResult.vue     # 视频信息 + 下载
│   │   │   ├── VideoAI.vue         # AI 分析面板（总结/字幕/思维导图/问答）
│   │   │   ├── AuthModal.vue       # 登录/注册弹窗
│   │   │   ├── FaqSection.vue      # FAQ 手风琴组件
│   │   │   ├── FeatureSection.vue  # 功能亮点
│   │   │   ├── PricingSection.vue  # 定价展示
│   │   │   └── AppFooter.vue       # 页脚
│   │   └── api/
│   │       ├── video.js            # 视频相关 API（含 SSE 流式）
│   │       ├── auth.js             # 用户认证 API
│   │       └── payment.js          # 支付 API
│   ├── vite.config.js              # Vite 配置（proxy -> :8001）
│   └── package.json
└── docs/                           # 技术文档
    ├── technical-design.md          # 本文档
    └── api-reference.md             # API 参考
```

## 五、API 设计

### 基础视频 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/parse` | POST | 解析视频链接，返回视频信息 |
| `/api/download` | POST | 开始下载指定格式视频，返回 task_id |
| `/api/progress/{task_id}` | GET(SSE) | 实时下载进度推送 |
| `/api/file/{task_id}` | GET | 下载已完成的文件 |
| `/api/thumbnail` | GET | 代理获取视频缩略图（绕过防盗链） |

### AI 功能 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/subtitle` | POST | 提取视频字幕（B站优先平台API，其他平台 yt-dlp） |
| `/api/summarize` | POST(SSE) | AI 视频总结（DeepSeek 流式输出） |
| `/api/chat` | POST(SSE) | AI 视频问答（DeepSeek 流式输出） |

### 用户认证 API

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 邮箱注册 | 否 |
| `/api/auth/login` | POST | 邮箱登录 | 否 |
| `/api/auth/me` | GET | 获取当前用户信息 | 需要 |

### 支付 API

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/payment/create-checkout-session` | POST | 创建 Stripe Checkout Session | 需要 |
| `/api/payment/create-portal-session` | POST | 创建 Stripe 客户门户 | 需要 |
| `/api/payment/verify-session` | POST | 主动验证支付结果并激活会员 | 需要 |
| `/api/payment/config` | GET | 获取 Stripe 配置信息 | 否 |
| `/api/stripe/webhook` | POST | Stripe Webhook 接收端点 | Stripe 签名 |

### 系统 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/health` | GET | 健康检查（备用） |

## 六、版权与风险控制

- 页面底部显示免责声明
- 不存储用户下载的视频（下载后定时清理）
- 使用 yt-dlp 作为后端引擎（风险由开源项目承担）

## 七、已确认事项

- v1.0/v1.1 已完成基础视频下载和 AI 增值功能
- 会员支付系统已实现，支持 Stripe Checkout 和 Webhook
- 用户认证系统已完成，支持邮箱注册/登录，JWT Token
- 本地开发运行即可，暂不考虑生产部署

## 八、分阶段实施计划

### 阶段一：项目初始化与基础框架 [已完成]
- 后端 FastAPI 框架搭建（端口 8001）
- 前端 Vue3 + Vite + Tailwind CSS v4 初始化
- 前后端代理通信验证通过

### 阶段二：yt-dlp 服务封装 + API 开发 [已完成]
- yt-dlp 下载服务封装（extract_info / download / progress_hooks）
- 4 个核心 API 端点完整实现 + thumbnail 代理接口
- B站视频端到端测试通过（解析→下载→SSE进度→文件获取）

### 阶段三：前端 UI 页面开发 [已完成]
- 暗色主题风格全套组件（Header / Footer / Hero）
- 核心交互组件（UrlInput / VideoResult）
- 营销展示组件（Feature / Pricing）
- 前端通过 /api/thumbnail 代理加载封面（绕过防盗链）

### 已修复的问题
- **ffmpeg 缺失**：安装 ffmpeg 解决"最佳画质"下载报错和视频无声音问题
- **封面不显示**：新增 /api/thumbnail 后端代理接口，前端通过代理加载缩略图
- **ANSI 转义码**：在 speed/eta/error 字段统一清理终端颜色码
- **progress hook 逻辑**：合并格式时 finished 对每个流分别触发，改为下载完成后统一扫描目录

### 阶段四：联调测试与优化 [已完成]
- 后端：临时文件自动清理（1小时过期，每10分钟扫描）
- 后端：URL 校验（Pydantic validator）+ 解析超时控制（60s）+ 友好错误信息
- 后端：SSE 进度超时保护（5分钟无变化自动断开）
- 前端：SSE 自动重连机制（指数退避，最多3次重试）
- 前端：解析中骨架屏（Skeleton Loading）
- 前端：视频结果卡片入场动画（Transition）
- 前端：错误提示过渡动画
- 前端：下载进度 ETA 剩余时间显示
- 前端：下载完成状态展示 + 重新下载按钮
- 前端：解析成功自动滚动到结果区域
- 前端：移动端响应式优化（按钮尺寸、间距、字体大小自适应）
- 前端：格式列表分类图标（合并/仅视频/仅音频）
- 前端：客户端请求超时控制（65s AbortController）
- 前端：Pydantic 验证错误格式兼容
- CORS 配置扩展（支持 5173/5174 端口）

### 阶段五：AI 视频总结与增值功能 [已完成]

#### 后端新增模块
- **字幕提取服务** `subtitle.py`：通用字幕提取入口，支持 VTT/SRT/JSON3 三种格式解析
  - 字幕语言优先级：zh-Hans > zh-CN > zh > zh-TW > en > en-US > ja > ko
  - 自动过滤弹幕（danmaku）和直播聊天（live_chat）等无效"字幕"类型
  - 字幕去重：合并连续相同文本的时间段
- **B站字幕专用提取** `bilibili_subtitle.py`：通过 B站 `x/v2/dm/view` API 获取字幕
  - 参考开源项目 [liyupi/free-video-downloader](https://github.com/liyupi/free-video-downloader) 的实现
  - 无需 WBI 签名、无需登录即可获取 CC 字幕和 AI 自动字幕
  - 优先调用平台 API，失败后 fallback 到 yt-dlp 通用方案
  - 支持短链接 b23.tv 解析、BV号/AV号提取
- **AI 服务** `ai_service.py`：封装 DeepSeek API（兼容 OpenAI SDK）
  - 环境变量：`DEEPSEEK_API_KEY`（必填）、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`
  - `summarize_video()`：流式生成视频总结（Markdown 格式：视频概述 + 内容大纲 + 关键要点 + 一句话总结）
  - `chat_about_video()`：流式问答，支持多轮对话历史
  - 文本截断：`MAX_SUBTITLE_LENGTH = 15000`，保留前后部分

#### 后端新增 API 端点
- `POST /api/subtitle`：提取视频字幕，60s 超时
- `POST /api/summarize`：SSE 流式返回 AI 总结，数据格式 `{"type":"chunk","content":"..."}`
- `POST /api/chat`：SSE 流式返回 AI 问答回复

#### 前端新增组件
- **VideoAI.vue**（~475 行）：AI 分析面板，4 个 Tab 页
  - 总结摘要：流式 Markdown 渲染 + 打字机光标效果
  - 字幕文本：带时间戳列表，显示语言标签（自动/人工字幕）
  - 思维导图：使用 `Markmap.create()` 渲染交互式 SVG
  - AI 问答：聊天界面 + 预设问题快捷按钮 + 历史上下文
- **video.js 新增 API 函数**：
  - `fetchSubtitle(url)`：字幕提取
  - `streamSummary()`：SSE 流式 AI 总结
  - `streamChat()`：SSE 流式 AI 问答
  - 所有流式函数返回 `{ close() }` 可手动中断

#### 字幕提取策略（平台优先 + fallback）
```
用户输入 URL
  ├── 抖音 → 暂不支持字幕提取
  ├── B站 → bilibili_subtitle.py（dm/view API，无需登录）
  │         ├── 成功 → 返回字幕
  │         └── 失败 → fallback 到 yt-dlp
  └── 其他平台 → subtitle.py（yt-dlp 通用提取）
```

#### 已修复的 AI 功能相关问题
- **B站弹幕被当作字幕**：yt-dlp 将 B 站弹幕列为 subtitles，通过 `_SKIP_LANGS = {"danmaku", "live_chat"}` 过滤
- **B站 Player API 需登录**：`x/player/wbi/v2` 接口即使有 WBI 签名也需要登录才返回字幕 URL
- **解决方案**：改用 `x/v2/dm/view` 弹幕视图接口，该接口无需签名/登录即可返回完整字幕列表和 URL

### 阶段六：SEO 搜索引擎优化 [已完成]

#### 页面 Meta 与结构化数据（`index.html`）
- 添加 `<meta name="description">` 和 `<meta name="keywords">` 标签，覆盖核心关键词
- 添加 Open Graph（og:title / og:description / og:image / og:url）用于社交分享
- 添加 Twitter Card（twitter:card / twitter:title / twitter:description）
- 添加 `<link rel="canonical">` 规范化 URL（域名占位符 `saveany.com`）
- 注入 JSON-LD 结构化数据（`WebApplication` + `SoftwareApplication` schema）
- 添加 `<noscript>` 降级内容，供不执行 JS 的爬虫读取核心信息
- 添加 `<link rel="preconnect">` 预连接 Google Fonts 加速字体加载

#### SEO 静态文件
- **`public/robots.txt`**：允许所有爬虫抓取，指向 sitemap.xml
- **`public/sitemap.xml`**：站点地图（域名占位符，待上线替换）

#### SPA 预渲染方案
- 尝试 `vite-plugin-prerender`，因 ESM 兼容性问题（`require is not defined`）弃用
- 改为独立预渲染脚本 `scripts/prerender.mjs`（基于 puppeteer）
- `package.json` 新增 `prerender` 和 `build:seo` 脚本

#### 语义化 HTML 与无障碍优化
- **HeroSection.vue**：优化 H1 标题关键词（"一键下载 · AI 总结"），副标题强化功能描述
- **FeatureSection.vue**：`<div>` → `<article>` 语义化标签，新增 `role="list/listitem"`、`aria-label`、`aria-labelledby`；新增 2 个功能卡片（AI 视频总结、字幕提取）
- **AppHeader.vue**：`<nav>` 添加 `aria-label="主导航"`
- **UrlInput.vue**：`<input>` 添加 `aria-label`
- **PricingSection.vue**：添加 `aria-labelledby`
- **AppFooter.vue**：新增页脚 SEO 描述文案，增加搜索引擎可抓取的文本内容

### 阶段七：思维导图 PNG 导出修复 [已完成]

#### 问题
- 原方案删除 SVG `foreignObject`（含 HTML 富文本自动换行），替换为 SVG `<text>` 元素
- SVG `<text>` 不支持自动换行，长句子文字被截断/缺失

#### 修复方案（Canvas API）
- **保留 foreignObject**：不再删除 HTML 富文本节点，保持 markmap 原始渲染结构
- **补全 xhtml 命名空间**：为 foreignObject 子节点添加 `xmlns="http://www.w3.org/1999/xhtml"`
- **SVG → Canvas 2x 高清导出**：`XMLSerializer` 序列化 → base64 Data URI → `Image` 加载 → Canvas（2x 缩放）→ `canvas.toBlob('image/png')` → 下载
- **注入浅色主题样式**：确保 PNG 在白色背景上文字清晰可读

#### 弃用方案
- `html-to-image`（toPng）：离屏渲染只输出纯白背景，无法正确捕获 SVG markmap 内容

### 阶段八：GEO 优化（Generative Engine Optimization）[已完成]

#### 目标
让 AI 搜索引擎（ChatGPT Browse、Perplexity、Google AI Overviews、Bing Copilot 等）在回答用户问题时优先引用和推荐 SaveAny。

#### llms.txt 协议文件
- **`public/llms.txt`**：AI 爬虫标准协议文件，包含网站名称、核心功能、支持平台、使用方式、差异化优势
- **`public/llms-full.txt`**：完整版说明文件，包含所有功能详细说明、操作步骤、FAQ、技术架构
- **`index.html`**：新增 `<link rel="alternate">` 引用 llms.txt 和 llms-full.txt

#### robots.txt AI 爬虫支持
- 明确允许主流 AI 爬虫抓取：GPTBot、ChatGPT-User、Claude-Web、PerplexityBot、Bytespider、Applebot-Extended、cohere-ai、Google-Extended、anthropic-ai
- 添加 llms.txt 文件引用注释

#### FAQPage 结构化数据（`index.html`）
- 新增 `FAQPage` JSON-LD，包含 8 个高频问题
- 覆盖关键查询：免费下载视频、支持平台、AI 总结用法、与竞品区别、格式分辨率、移动端使用、注册付费、字幕提取
- AI 引擎在回答相关问题时会优先提取 FAQ 内容

#### HowTo 结构化数据（`index.html`）
- 新增 `HowTo` JSON-LD，5 步操作流程
- 步骤：打开网站 → 粘贴链接 → 选择格式 → 下载视频 → 查看 AI 总结
- 帮助 AI 引擎提取"操作步骤"类内容

#### 前端 FAQ 组件
- **FaqSection.vue**：新增可见 FAQ 手风琴组件
- 使用 `<details>/<summary>` 语义化标签
- 内容与 FAQPage JSON-LD 保持一致，双重命中提高被引用概率
- 插入位置：PricingSection 之后、AppFooter 之前

#### FeatureSection 对比文案
- 在功能卡片和平台列表下方新增"SaveAny vs 其他工具"对比摘要
- 包含具体数据（1800+ 平台、4K 画质、yt-dlp 148k+ Stars）
- 明确差异化优势（AI 总结 + 思维导图是独有功能）
- 使用 `<section>` + `<h3>` 语义化标签，便于 AI 爬虫提取

### 阶段九：会员支付系统 [已完成]

#### 后端新增模块
- **用户认证** `auth.py` + `database.py`：JWT Token 生成与验证，SQLite 用户存储
  - `create_token()` / `decode_token()`：JWT Token 工具
  - `require_user()` / `get_current_user()`：FastAPI 依赖注入
  - `get_user_by_email()` / `get_user_by_id()` / `update_user()`：用户 CRUD
- **支付服务** `payment_service.py`：Stripe 支付业务逻辑
  - `create_checkout_session()`：创建 Stripe Checkout Session
  - `verify_checkout_session()`：主动验证支付结果并激活会员（webhook 补充机制）
  - `handle_webhook_event()`：处理 Stripe Webhook 事件（幂等性去重）
  - 支持一次性付款（payment）和订阅模式（subscription）两种模式
  - 一次性付款会员有效期 30 天

#### 后端新增 API 端点
- `POST /api/auth/register`：邮箱注册
- `POST /api/auth/login`：邮箱登录
- `GET /api/auth/me`：获取当前用户信息（含 AI 使用量）
- `POST /api/payment/create-checkout-session`：创建支付会话
- `POST /api/payment/create-portal-session`：创建客户门户
- `POST /api/payment/verify-session`：主动验证支付并激活会员
- `GET /api/payment/config`：获取 Stripe 配置
- `POST /api/stripe/webhook`：Stripe Webhook 接收端点

#### 前端新增组件
- **AuthModal.vue**：登录/注册弹窗组件
  - Tab 切换登录/注册
  - 邮箱 + 密码表单验证
  - 错误提示和成功反馈
- **user.js**：用户状态管理
  - `isLoggedIn`：登录状态（token + user 双条件）
  - `isVip`：VIP 会员判断
  - `aiUsage`：AI 使用量追踪
- **payment.js**：支付 API 封装
  - `createCheckoutSession()`：创建支付会话
  - `verifySession()`：验证支付结果
  - `getPaymentConfig()`：获取支付配置

#### 已修复的支付相关问题
- **Stripe v15 兼容性**：`metadata` 从 dict 改为 StripeObject，使用 `_safe_metadata_get()` 访问
- **Webhook 未送达**：前端支付成功回跳时主动调用 `verify-session` 确保激活
- **VIP 状态同步**：`App.vue onMounted` 中获取最新用户信息
