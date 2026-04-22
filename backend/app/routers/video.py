import asyncio
import json
import re
import httpx
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, Response

from app.services.downloader import parse_video, start_download, get_task, get_task_file, _strip_ansi
from app.services.subtitle import extract_subtitles
from app.services.ai_service import summarize_video, chat_about_video

router = APIRouter()

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
async def api_extract_subtitle(req: SubtitleRequest):
    """提取视频字幕，返回带时间戳的结构化字幕数据"""
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(extract_subtitles, req.url),
            timeout=PARSE_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="字幕提取超时，请稍后重试")
    except Exception as e:
        msg = _strip_ansi(str(e))
        raise HTTPException(status_code=400, detail=f"字幕提取失败: {msg}")


@router.post("/summarize")
async def api_summarize_video(req: SummarizeRequest):
    """AI 生成视频总结（SSE 流式返回）"""
    if not req.subtitle_text.strip():
        raise HTTPException(status_code=400, detail="字幕内容为空，无法生成总结")

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
async def api_chat_about_video(req: ChatRequest):
    """AI 视频问答（SSE 流式返回）"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="请输入问题")

    async def _event_stream():
        try:
            async for chunk in chat_about_video(
                req.title, req.subtitle_text, req.history, req.question
            ):
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
