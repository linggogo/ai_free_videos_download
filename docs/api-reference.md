# API 参考文档

## 基础信息
- 后端地址：http://localhost:8001
- 前端开发地址：http://localhost:5173（通过 Vite proxy 代理 /api 到后端）
- 系统依赖：ffmpeg（brew install ffmpeg）— yt-dlp 合并视频+音频流必需
- Python 依赖：fastapi, uvicorn, yt-dlp, python-multipart, httpx, openai, stripe, python-dotenv
- 环境变量：
  - `DEEPSEEK_API_KEY`（AI 总结/问答功能必需）
  - `STRIPE_SECRET_KEY`、`STRIPE_PUBLISHABLE_KEY`、`STRIPE_PRICE_ID`（支付功能必需）
  - `STRIPE_WEBHOOK_SECRET`（Webhook 签名验证必需）

---

## 1. POST /api/parse

解析视频链接，返回视频元信息和可用格式列表。

**请求体：**
```json
{
  "url": "https://www.youtube.com/watch?v=xxxxx"
}
```

**响应：**
```json
{
  "title": "视频标题",
  "thumbnail": "https://..../thumbnail.jpg",
  "duration": 180,
  "duration_string": "3:00",
  "uploader": "作者名",
  "platform": "youtube",
  "formats": [
    {
      "format_id": "137+140",
      "ext": "mp4",
      "resolution": "1920x1080",
      "filesize": 52428800,
      "filesize_approx": 52428800,
      "note": "1080p"
    }
  ]
}
```

---

## 2. POST /api/download

开始下载指定格式的视频，返回任务 ID。

**请求体：**
```json
{
  "url": "https://www.youtube.com/watch?v=xxxxx",
  "format_id": "137+140"
}
```

**响应：**
```json
{
  "task_id": "uuid-string",
  "status": "downloading"
}
```

---

## 3. GET /api/progress/{task_id}

SSE（Server-Sent Events）实时推送下载进度。

**响应（SSE 流）：**
```
data: {"status": "downloading", "progress": 45.2, "speed": "2.5MiB/s", "eta": "00:15", "filename": "", "error": ""}

data: {"status": "downloading", "progress": 99, "speed": "", "eta": "", "filename": "", "error": ""}

data: {"status": "complete", "progress": 100, "speed": "", "eta": "", "filename": "/path/to/video.mp4", "error": ""}
```

> **注意事项：**
> - 合并格式时（如 bestvideo+bestaudio），progress hook 的 finished 对每个流分别触发
> - 实际完成标志以 `status: "complete"` 为准，由 `ydl.download()` 返回后设置
> - speed/eta/error 字段已清理 ANSI 转义码

---

## 4. GET /api/file/{task_id}

下载已完成的视频文件（返回文件流）。

**响应：** 文件二进制流，`Content-Disposition: attachment; filename="video.mp4"`

---

## 5. GET /health

健康检查。

**响应：**
```json
{
  "status": "ok"
}
```

---

## 6. GET /api/thumbnail

代理获取视频缩略图，绕过平台防盗链限制（如 B站 hdslb.com）。

**查询参数：**
- `url`（必填）：缩略图原始 URL

**示例：**
```
GET /api/thumbnail?url=http://i1.hdslb.com/bfs/archive/xxx.jpg
```

**响应：** 图片二进制流，`Content-Type` 与原图一致，缓存 24 小时。

**前端使用：**
```vue
<img :src="`/api/thumbnail?url=${encodeURIComponent(videoInfo.thumbnail)}`" />
```

---

## 7. POST /api/subtitle

提取视频字幕。B 站优先使用平台 dm/view API，其他平台使用 yt-dlp。

**请求体：**
```json
{
  "url": "https://www.bilibili.com/video/BV1mAAmzqEfP"
}
```

**响应：**
```json
{
  "available": true,
  "language": "zh",
  "language_doc": "中文",
  "source": "bilibili_api (manual)",
  "segments": [
    {"start": 0.0, "end": 3.0, "text": "字幕第一句"},
    {"start": 3.0, "end": 5.5, "text": "字幕第二句"}
  ],
  "full_text": "完整字幕文本（用于 AI 总结）",
  "message": ""
}
```

**字幕提取策略：**
- 抖音：暂不支持，返回 `available: false`
- B 站：优先 `bilibili_subtitle.py`（dm/view API，无需登录），失败后 fallback 到 yt-dlp
- 其他平台：`subtitle.py` 通过 yt-dlp 提取，支持 VTT/SRT/JSON3 三种格式

**超时：** 60 秒

---

## 8. POST /api/summarize

AI 视频总结（SSE 流式输出）。基于 DeepSeek 大模型对视频字幕进行结构化总结。

**请求体：**
```json
{
  "title": "视频标题",
  "subtitle_text": "视频字幕完整文本..."
}
```

**响应（SSE 流）：**
```
data: {"type": "chunk", "content": "## 视频概述\n"}

data: {"type": "chunk", "content": "这个视频主要讲述了..."}

data: {"type": "done"}
```

**总结输出格式（Markdown）：**
- 视频概述：2-3 句话概括
- 内容大纲：按逻辑顺序列出主要章节
- 关键要点：提取最重要的知识点
- 一句话总结

> **注意：** 字幕文本超过 15000 字符时会自动截断（保留前后部分）

---

## 9. POST /api/chat

AI 视频问答（SSE 流式输出）。基于视频字幕内容进行互动问答。

**请求体：**
```json
{
  "title": "视频标题",
  "subtitle_text": "视频字幕完整文本...",
  "question": "这个视频的主要观点是什么？",
  "history": [
    {"role": "user", "content": "之前的问题"},
    {"role": "assistant", "content": "之前的回答"}
  ]
}
```

**响应（SSE 流）：**
```
data: {"type": "chunk", "content": "根据视频内容，"}

data: {"type": "chunk", "content": "主要观点是..."}

data: {"type": "done"}
```

---

## 关键技术参考（来自 Context7 最新文档）

### FastAPI SSE（Server-Sent Events）

FastAPI 0.115+ 原生支持 SSE，使用 `EventSourceResponse` + `ServerSentEvent`：

```python
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.get("/stream", response_class=EventSourceResponse)
async def stream() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"progress": 50}, event="progress", id="1")
```

### yt-dlp Python 嵌入

```python
from yt_dlp import YoutubeDL

# 提取视频信息（不下载）
ydl_opts = {'quiet': True, 'no_warnings': True}
with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    info_dict = ydl.sanitize_info(info)

# 带进度回调的下载
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
    elif d['status'] == 'finished':
        print(f"完成: {d['filename']}")

ydl_opts = {
    'format': 'bestvideo[height<=1080]+bestaudio/best',
    'merge_output_format': 'mp4',
    'outtmpl': '%(title)s.%(ext)s',
    'progress_hooks': [progress_hook],
}
with YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
```

### Tailwind CSS v4 + Vite 配置

```js
// vite.config.js
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [vue(), tailwindcss()],
})
```

```css
/* style.css - Tailwind v4 只需一行 */
@import "tailwindcss";
```

### Vue3 Composition API

```vue
<script setup>
import { ref, onMounted } from 'vue'
const data = ref(null)
onMounted(async () => {
  const res = await fetch('/api/health')
  data.value = await res.json()
})
</script>
```

### B站字幕提取（dm/view API）

通过 B 站弹幕视图接口获取 CC 字幕和 AI 自动字幕，无需 WBI 签名或登录：

```python
import httpx

headers = {
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://www.bilibili.com/",
}

# 1. 获取视频 aid, cid
view_resp = httpx.get(
    "https://api.bilibili.com/x/web-interface/view",
    params={"bvid": "BV1mAAmzqEfP"},
    headers=headers,
)
data = view_resp.json()["data"]
aid, cid = data["aid"], data["cid"]

# 2. 通过 dm/view 获取字幕列表
dm_resp = httpx.get(
    "https://api.bilibili.com/x/v2/dm/view",
    params={"aid": aid, "oid": cid, "type": 1},
    headers=headers,
)
subtitles = dm_resp.json()["data"]["subtitle"]["subtitles"]
# => [{"lan": "zh", "lan_doc": "中文", "subtitle_url": "http://aisubtitle.hdslb.com/..."}, ...]

# 3. 下载字幕 JSON（body: [{from, to, content}]）
sub_url = "https:" + subtitles[0]["subtitle_url"]
sub_data = httpx.get(sub_url, headers=headers).json()
segments = [{"start": item["from"], "end": item["to"], "text": item["content"]} for item in sub_data["body"]]
```

### DeepSeek AI 总结（兼容 OpenAI SDK）

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 流式生成总结
stream = await client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个专业的视频内容分析助手..."},
        {"role": "user", "content": f"请对以下视频字幕进行总结：\n{subtitle_text}"},
    ],
    stream=True,
    temperature=0.3,
    max_tokens=2000,
)
async for chunk in stream:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

### 前端 SSE 流式接收（fetch + ReadableStream）

```javascript
// video.js 中的 streamSummary 实现方式
const response = await fetch('/api/summarize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title, subtitle_text }),
})
const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  const text = decoder.decode(value)
  // 解析 SSE: "data: {\"type\":\"chunk\",\"content\":\"...\"}\n\n"
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6))
      if (data.type === 'chunk') onChunk(data.content)
      if (data.type === 'done') onDone()
    }
  }
}
```

---

## 10. POST /api/payment/create-checkout-session

创建 Stripe Checkout Session（需要登录）。

**请求头：**
```
Authorization: Bearer {token}
```

**响应：**
```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

---

## 11. POST /api/payment/create-portal-session

创建 Stripe 客户门户会话（需要登录）。

**请求头：**
```
Authorization: Bearer {token}
```

**响应：**
```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

---

## 12. POST /api/payment/verify-session

主动验证支付结果并激活会员（需要登录）。

支付成功回跳后调用此接口，确保即使 webhook 未送达也能激活会员。

**请求头：**
```
Authorization: Bearer {token}
```

**请求体：**
```json
{
  "session_id": "cs_test_xxx"
}
```

**响应：**
```json
{
  "activated": true,
  "reason": "会员已激活"
}
```

> **注意**：Stripe Python SDK v15 中 `metadata` 是 `StripeObject` 类型，不支持 `.get()` 方法。代码中应使用 `_safe_metadata_get()` 辅助函数。

---

## 13. GET /api/payment/config

获取 Stripe 配置信息。

**响应：**
```json
{
  "publishable_key": "pk_test_xxx",
  "price": "19.9",
  "currency": "CNY",
  "period": "月"
}
```

---

## 14. POST /api/stripe/webhook

Stripe Webhook 接收端点。

注意：这个端点必须接收原始 body（不能被 JSON 解析），因为 Stripe 签名验证需要原始 payload。

**请求头：**
```
Stripe-Signature: t=xxx,v1=xxx
```

**响应：**
```json
{
  "status": "ok",
  "message": "Processed checkout.session.completed"
}
```

---

## 15. GET /api/auth/me

获取当前用户信息（需要登录）。

**请求头：**
```
Authorization: Bearer {token}
```

**响应：**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "subscription_status": "active",
    "subscription_end_date": "2026-05-22T11:58:56+00:00",
    "created_at": "2026-04-22T10:51:13"
  },
  "ai_usage": {
    "used": 0,
    "limit": null,
    "is_vip": true
  }
}
```

> **注意**：`subscription_status` 为 `active` 表示 VIP 会员，`is_vip` 为 true 表示 VIP 用户（AI 功能不限量）。

