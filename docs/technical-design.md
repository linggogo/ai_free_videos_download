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

### 进阶功能（v1.2，待实现）
9. 批量下载、字幕导出（SRT/VTT/TXT）、用户认证、Stripe 支付

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
│   │   ├── routers/
│   │   │   └── video.py            # 视频解析/下载/字幕/AI总结 API
│   │   └── services/
│   │       ├── downloader.py       # yt-dlp 封装服务
│   │       ├── douyin.py           # 抖音专用解析（无Cookie下载）
│   │       ├── subtitle.py         # 通用字幕提取（yt-dlp + 平台优先）
│   │       ├── bilibili_subtitle.py # B站专用字幕提取（dm/view API）
│   │       └── ai_service.py       # DeepSeek AI 总结/问答服务
│   ├── downloads/                  # 临时下载目录（自动清理）
│   ├── requirements.txt
│   └── run.py
├── frontend/                       # Vue3 前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   │   ├── AppHeader.vue       # 导航栏
│   │   │   ├── HeroSection.vue     # 首屏 Hero
│   │   │   ├── UrlInput.vue        # URL 输入框
│   │   │   ├── VideoResult.vue     # 视频信息 + 下载
│   │   │   ├── VideoAI.vue         # AI 分析面板（总结/字幕/思维导图/问答）
│   │   │   ├── FeatureSection.vue  # 功能亮点
│   │   │   ├── PricingSection.vue  # 定价展示
│   │   │   └── AppFooter.vue       # 页脚
│   │   └── api/
│   │       └── video.js            # API 调用封装（含 SSE 流式）
│   ├── vite.config.js              # Vite 配置（proxy -> :8001）
│   └── package.json
└── docs/                           # 技术文档
    ├── technical-design.md          # 本文档
    └── api-reference.md             # API 参考
```

## 五、API 设计

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/parse` | POST | 解析视频链接，返回视频信息 |
| `/api/download` | POST | 开始下载指定格式视频，返回 task_id |
| `/api/progress/{task_id}` | GET(SSE) | 实时下载进度推送 |
| `/api/file/{task_id}` | GET | 下载已完成的文件 |
| `/api/thumbnail` | GET | 代理获取视频缩略图（绕过防盗链） |
| `/api/subtitle` | POST | 提取视频字幕（B站优先平台API，其他平台 yt-dlp） |
| `/api/summarize` | POST(SSE) | AI 视频总结（DeepSeek 流式输出） |
| `/api/chat` | POST(SSE) | AI 视频问答（DeepSeek 流式输出） |
| `/health` | GET | 健康检查 |

## 六、版权与风险控制

- 页面底部显示免责声明
- 不存储用户下载的视频（下载后定时清理）
- 使用 yt-dlp 作为后端引擎（风险由开源项目承担）

## 七、已确认事项

- v1.0 做匿名免费版，不需要登录/注册/付费功能
- 本地开发运行即可，暂不考虑生产部署
- 定价区/会员对比表仅做静态展示（为后续付费铺垫）

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
