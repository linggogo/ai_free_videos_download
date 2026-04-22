"""AI 服务 — 封装 DeepSeek API 调用（兼容 OpenAI 格式）"""
import os
import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI

logger = logging.getLogger("ai_service")

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 最大字幕文本长度（避免超出 token 限制）
MAX_SUBTITLE_LENGTH = 15000


def _get_client() -> AsyncOpenAI:
    """获取 DeepSeek API 客户端"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("未配置 DEEPSEEK_API_KEY 环境变量，请设置后重试")
    return AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )


def _truncate_text(text: str, max_length: int = MAX_SUBTITLE_LENGTH) -> str:
    """截断过长文本，保留前后部分"""
    if len(text) <= max_length:
        return text
    half = max_length // 2
    return text[:half] + "\n\n...(中间部分省略)...\n\n" + text[-half:]


# -----------------------------------------------------------------------
# AI 视频总结
# -----------------------------------------------------------------------

SUMMARIZE_SYSTEM_PROMPT = """你是一个专业的视频内容分析助手。请根据视频标题和字幕内容，生成结构化的视频总结。

要求：
1. 使用 Markdown 格式输出
2. 结构如下：
   - **视频概述**：用 2-3 句话概括视频核心内容
   - **内容大纲**：用编号列表列出视频的主要章节/话题（每个章节下可有子要点）
   - **关键要点**：提炼 3-5 个最重要的知识点或结论
   - **一句话总结**：用一句话概括视频价值
3. 语言简洁明了，条理清晰
4. 保持客观，忠实于原始内容
5. 大纲层级使用 ##、### 标题格式（方便生成思维导图）"""


async def summarize_video(
    title: str,
    subtitle_text: str,
) -> AsyncGenerator[str, None]:
    """
    AI 生成视频总结（流式输出）。
    yields: 逐块的文本内容
    """
    client = _get_client()
    subtitle_text = _truncate_text(subtitle_text)

    user_message = f"视频标题：{title}\n\n字幕内容：\n{subtitle_text}"

    stream = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        stream=True,
        temperature=0.3,
        max_tokens=2000,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# -----------------------------------------------------------------------
# AI 视频问答
# -----------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """你是一个智能视频内容助手。用户正在观看一个视频，你需要根据视频的标题和字幕内容来回答用户的问题。

规则：
1. 回答要基于视频内容，不要编造视频中没有提到的信息
2. 如果问题超出视频内容范围，诚实告知并尽可能提供相关的补充信息
3. 回答使用 Markdown 格式，简洁明了
4. 使用与用户问题相同的语言回答"""


async def chat_about_video(
    title: str,
    subtitle_text: str,
    history: list[dict],
    question: str,
) -> AsyncGenerator[str, None]:
    """
    AI 视频问答（流式输出）。
    history: [{"role": "user"/"assistant", "content": "..."}]
    yields: 逐块的文本内容
    """
    client = _get_client()
    subtitle_text = _truncate_text(subtitle_text)

    system_message = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"当前视频标题：{title}\n\n"
        f"视频字幕内容：\n{subtitle_text}"
    )

    messages = [{"role": "system", "content": system_message}]

    # 添加对话历史（最多保留最近 10 轮）
    if history:
        messages.extend(history[-20:])

    messages.append({"role": "user", "content": question})

    stream = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        stream=True,
        temperature=0.5,
        max_tokens=1500,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
