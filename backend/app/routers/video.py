import asyncio
import json
import re
import httpx
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import StreamingResponse, FileResponse, Response

from app.services.downloader import parse_video, start_download, get_task, get_task_file, _strip_ansi
from app.services.subtitle import extract_subtitles
from app.services.ai_service import summarize_video, chat_about_video
from app.auth import get_current_user
from app.database import get_ai_usage_count, increment_ai_usage, FREE_AI_DAILY_LIMIT, CHAT_AI_DAILY_LIMIT

router = APIRouter()

# AI 功能类型定义
AI_FEATURES = {
    'subtitle': '字幕提取',
    'summarize': 'AI 总结',
    'chat': 'AI 问答',
}


async def _check_ai_limit(request: Request, user: dict | None, feature_type: str = 'summarize'):
    """
    检查 AI 使用次数限制。
    会员用户不限制，免费/匿名用户每日 3 次。
    返回 (user_id, client_ip) 用于后续计数。
    """
    if user and user.get("subscription_status") == "active":
        return user["id"], None  # 会员不限制

    user_id = user["id"] if user else None
    client_ip = request.client.host if not user else None

    count = await get_ai_usage_count(user_id, client_ip, feature_type)
    if count >= FREE_AI_DAILY_LIMIT:
        raise HTTPException(
            status_code=403,
            detail={
                "message": f"今日AI{_get_feature_name(feature_type)}使用次数已用完（3次/天），升级会员享无限使用",
                "code": "AI_LIMIT_EXCEEDED",
                "used": count,
                "limit": FREE_AI_DAILY_LIMIT,
                "feature": feature_type,
            },
        )
    return user_id, client_ip


def _get_feature_name(feature_type: str) -> str:
    """将功能类型转换为友好名称"""
    return AI_FEATURES.get(feature_type, feature_type)

# 解析超时（秒）
PARSE_TIMEOUT = 60

# URL 基本校验
_URL_RE = re.compile(r"^https?://[^\s]+$")


class ParseRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("请输入视频链接")
        if not _URL_RE.match(v):
            raise ValueError("请输入有效的视频链接（以 http:// 或 https:// 开头）")
        return v


class DownloadRequest(BaseModel):
    url: str
    format_id: str


@router.post("/parse")
async def api_parse_video(req: ParseRequest):
    """解析视频链接，返回视频信息和可用格式列表"""
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(parse_video, req.url),
            timeout=PARSE_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="解析超时，请稍后重试或检查链接是否有效")
    except Exception as e:
        msg = _strip_ansi(str(e))
        # 友好化常见错误
        if "Unsupported URL" in msg:
            detail = "暂不支持该链接，请检查 URL 是否正确"
        elif "Video unavailable" in msg or "Private video" in msg:
            detail = "视频不可用（可能是私密视频或已被删除）"
        elif "HTTP Error 403" in msg:
            detail = "无法访问该视频（可能需要登录或有地区限制）"
        elif "HTTP Error 404" in msg:
            detail = "视频不存在，请检查链接"
        elif "sign in" in msg.lower() or "login" in msg.lower():
            detail = "该视频需要登录才能访问，暂时无法下载"
        elif "抖音" in msg or "douyin" in msg.lower():
            detail = f"抖音视频解析失败: {msg}"
        elif "视频 ID" in msg or "video ID" in msg.lower():
            detail = "无法识别该链接，请确认是有效的视频链接"
        else:
            detail = f"解析失败: {msg}"
        raise HTTPException(status_code=400, detail=detail)


@router.post("/download")
async def api_download_video(req: DownloadRequest):
    """开始下载视频，返回 task_id"""
    url = req.url.strip()
    format_id = req.format_id.strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入视频链接")
    if not format_id:
        raise HTTPException(status_code=400, detail="请选择下载格式")

    try:
        task_id = start_download(url, format_id)
        return {"task_id": task_id, "status": "downloading"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动下载失败: {str(e)}")


@router.get("/progress/{task_id}")
async def api_get_progress(task_id: str):
    """SSE 实时推送下载进度"""
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def _event_stream():
        no_update_count = 0
        while True:
            task = get_task(task_id)
            if task is None:
                yield f"data: {json.dumps({'status': 'error', 'error': '任务丢失'}, ensure_ascii=False)}\n\n"
                break

            yield f"data: {json.dumps(task, ensure_ascii=False)}\n\n"

            if task["status"] in ("complete", "error"):
                break

            # 超时保护：如果5分钟内进度无变化，标记为超时
            no_update_count += 1
            if no_update_count > 600:  # 600 * 0.5s = 5min
                yield f"data: {json.dumps({'status': 'error', 'error': '下载超时，请重试'}, ensure_ascii=False)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/file/{task_id}")
async def api_get_file(task_id: str):
    """下载已完成的文件"""
    file_path = get_task_file(task_id)
    if file_path is None:
        raise HTTPException(status_code=404, detail="文件不存在或下载未完成")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


class SubtitleRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("请输入视频链接")
        if not _URL_RE.match(v):
            raise ValueError("请输入有效的视频链接")
        return v


class SummarizeRequest(BaseModel):
    title: str
    subtitle_text: str


class ChatRequest(BaseModel):
    title: str
    subtitle_text: str
    history: list[dict] = []
    question: str


@router.post("/subtitle")
async def api_extract_subtitle(
    req: SubtitleRequest,
    request: Request,
    user: dict | None = Depends(get_current_user),
):
    """提取视频字幕，返回带时间戳的结构化字幕数据（受 AI 使用次数限制）"""
    user_id, client_ip = await _check_ai_limit(request, user, 'subtitle')

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(extract_subtitles, req.url),
            timeout=PARSE_TIMEOUT,
        )
        # 成功提取后计数 +1
        if result.get("available"):
            await increment_ai_usage(user_id, client_ip, 'subtitle')
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="字幕提取超时，请稍后重试")
    except Exception as e:
        msg = _strip_ansi(str(e))
        raise HTTPException(status_code=400, detail=f"字幕提取失败: {msg}")


@router.post("/summarize")
async def api_summarize_video(
    req: SummarizeRequest,
    request: Request,
    user: dict | None = Depends(get_current_user),
):
    """AI 生成视频总结（SSE 流式返回，受 AI 使用次数限制）"""
    if not req.subtitle_text.strip():
        raise HTTPException(status_code=400, detail="字幕内容为空，无法生成总结")

    user_id, client_ip = await _check_ai_limit(request, user, 'summarize')
    # 提前计数（流式接口在开始时就计数）
    await increment_ai_usage(user_id, client_ip, 'summarize')

    async def _event_stream():
        try:
            async for chunk in summarize_video(req.title, req.subtitle_text):
                data = json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat")
async def api_chat_about_video(
    req: ChatRequest,
    request: Request,
    user: dict | None = Depends(get_current_user),
):
    """AI 视频问答（SSE 流式返回，受 AI 使用次数限制）"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="请输入问题")

    # 检查 AI 问答每日配额（独立限额 10 次）
    if user and user.get("subscription_status") != "active":
        user_id = user["id"]
        client_ip = request.client.host if not user else None
        chat_count = await get_ai_usage_count(user_id, client_ip, 'chat')
        if chat_count >= CHAT_AI_DAILY_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": f"今日AI问答使用次数已用完（{CHAT_AI_DAILY_LIMIT}次/天），升级会员享无限使用",
                    "code": "AI_LIMIT_EXCEEDED",
                    "used": chat_count,
                    "limit": CHAT_AI_DAILY_LIMIT,
                    "feature": "chat",
                },
            )

    user_id = user["id"] if user else None
    client_ip = request.client.host if not user else None

    async def _event_stream():
        try:
            async for chunk in chat_about_video(
                req.title, req.subtitle_text, req.history, req.question
            ):
                data = json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            # 完成时计数
            await increment_ai_usage(user_id, client_ip, 'chat')
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/thumbnail")
async def api_proxy_thumbnail(url: str = Query(..., description="缩略图 URL")):
    """代理获取视频缩略图，绕过防盗链限制"""
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="无效的缩略图 URL")

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": url,
            })
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        raise HTTPException(status_code=502, detail="获取缩略图失败")


class UsageStatusResponse(BaseModel):
    subtitle: dict  # { used: int, remaining: int, limit: int }
    summarize: dict
    chat: dict
    is_vip: bool


@router.get("/usage", response_model=UsageStatusResponse)
async def api_get_usage_status(
    request: Request,
    user: dict | None = Depends(get_current_user),
):
    """获取用户各 AI 功能的今日使用状态"""
    is_vip = user and user.get("subscription_status") == "active"

    if is_vip:
        # 会员无限制
        return UsageStatusResponse(
            subtitle={"used": 0, "remaining": -1, "limit": -1},
            summarize={"used": 0, "remaining": -1, "limit": -1},
            chat={"used": 0, "remaining": -1, "limit": -1},
            is_vip=True,
        )

    user_id = user["id"] if user else None
    client_ip = request.client.host if not user else None

    result = {}
    for feature in ['subtitle', 'summarize']:
        count = await get_ai_usage_count(user_id, client_ip, feature)
        remaining = max(0, FREE_AI_DAILY_LIMIT - count)
        result[feature] = {
            "used": count,
            "remaining": remaining,
            "limit": FREE_AI_DAILY_LIMIT,
        }
    # AI 问答独立限额
    chat_count = await get_ai_usage_count(user_id, client_ip, 'chat')
    result['chat'] = {
        "used": chat_count,
        "remaining": max(0, CHAT_AI_DAILY_LIMIT - chat_count),
        "limit": CHAT_AI_DAILY_LIMIT,
    }

    return UsageStatusResponse(
        subtitle=result.get('subtitle', {"used": 0, "remaining": 3, "limit": 3}),
        summarize=result.get('summarize', {"used": 0, "remaining": 3, "limit": 3}),
        chat=result.get('chat', {"used": 0, "remaining": 10, "limit": 10}),
        is_vip=False,
    )
