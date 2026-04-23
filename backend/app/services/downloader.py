"""yt-dlp 下载服务封装 + 抖音专用通道"""
import os
import re
import uuid
import time
import shutil
import threading
from pathlib import Path
from yt_dlp import YoutubeDL

from app.services.douyin import is_douyin_url, parse_douyin_video, download_douyin_file

# 下载目录
DOWNLOADS_DIR = Path(__file__).parent.parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# 任务状态存储（内存，无数据库）
_tasks: dict[str, dict] = {}

# 文件清理配置
CLEANUP_INTERVAL = 600  # 每10分钟检查一次
MAX_FILE_AGE = 3600  # 文件最大保存1小时


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    """去除 ANSI 转义码"""
    return _ANSI_RE.sub("", s).strip() if s else ""


class _QuietLogger:
    """静默 logger，避免 yt-dlp 输出到 stdout"""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def parse_video(url: str) -> dict:
    """
    解析视频链接，返回视频元信息和可用格式列表。
    抖音链接走专用解析通道（无需 Cookie），其他平台走 yt-dlp。
    在线程池中同步调用，外层用 asyncio.to_thread 包装。
    """
    # 抖音专用通道
    if is_douyin_url(url):
        return parse_douyin_video(url)

    # 其他平台走 yt-dlp
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "logger": _QuietLogger(),
        "extract_flat": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        info = ydl.sanitize_info(info)

    # 提取有用的格式列表（过滤掉无效格式）
    formats = []
    seen = set()
    max_height = 0

    for f in info.get("formats", []):
        ext = f.get("ext", "")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        height = f.get("height") or 0
        format_id = f.get("format_id", "")

        # 跳过纯 storyboard / mhtml 格式
        if ext in ("mhtml",) or "storyboard" in f.get("format_note", "").lower():
            continue

        # 构造显示标签
        if vcodec != "none" and acodec != "none":
            # 视频+音频合并格式（平台直接提供的，通常画质较低）
            note = f"{height}p (视频+音频)" if height else f.get("format_note", ext)
            category = "merged"
        elif vcodec != "none":
            # 仅视频流 — 下载时会自动合并最佳音频
            note = f"{height}p" if height else f.get("format_note", "video only")
            category = "video"
            # 为仅视频格式自动拼接最佳音频，下载时 yt-dlp 会自动合并
            format_id = f"{format_id}+bestaudio"
        elif acodec != "none":
            note = f.get("format_note", "仅音频")
            category = "audio"
        else:
            continue

        if height > max_height:
            max_height = height

        # 去重：按 (height, category) 去重，同高度优先保留 video（会合并音频）
        key = (height, category)
        if key in seen:
            continue
        seen.add(key)

        formats.append({
            "format_id": format_id,
            "ext": ext,
            "resolution": f.get("resolution", ""),
            "height": height,
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "note": note,
            "category": category,
        })

    # 始终在最前面添加"最佳画质"选项（bestvideo+bestaudio 自动选最高画质+最佳音频）
    formats.insert(0, {
        "format_id": "bestvideo+bestaudio/best",
        "ext": "mp4",
        "resolution": "",
        "height": max_height if max_height else 9999,
        "filesize": None,
        "note": f"最佳画质 {'(' + str(max_height) + 'p) ' if max_height else ''}(自动合并视频+音频)",
        "category": "best",
    })

    # 排序：best 最前，然后 video（带音频合并）按高度降序，merged 次之，audio 最后
    category_order = {"best": 0, "video": 1, "merged": 2, "audio": 3}
    formats.sort(key=lambda x: (category_order.get(x["category"], 9), -x["height"]))

    return {
        "title": info.get("title", "未知标题"),
        "thumbnail": info.get("thumbnail", ""),
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string", ""),
        "uploader": info.get("uploader", info.get("channel", "")),
        "platform": info.get("extractor_key", info.get("extractor", "")).lower(),
        "webpage_url": info.get("webpage_url", url),
        "formats": formats,
    }


def start_download(url: str, format_id: str) -> str:
    """
    启动后台下载任务，返回 task_id。
    抖音走专用下载通道，其他平台走 yt-dlp。
    下载在独立线程中进行，进度通过 _tasks 字典共享。
    """
    task_id = uuid.uuid4().hex[:12]
    task_dir = DOWNLOADS_DIR / task_id
    task_dir.mkdir(exist_ok=True)

    _tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "speed": "",
        "eta": "",
        "filename": "",
        "error": "",
    }

    # 抖音专用下载通道
    if is_douyin_url(url):
        def _do_douyin_download():
            try:
                _tasks[task_id]["status"] = "downloading"

                # 解析获取下载链接（从缓存或重新解析）
                info = parse_douyin_video(url)
                if format_id == "douyin_audio":
                    media_url = info.get("_douyin_audio_url", "")
                    ext = "M4A"
                else:
                    media_url = info.get("_douyin_video_url", "")
                    ext = "mp4"

                if not media_url:
                    raise ValueError("未找到抖音媒体下载地址")

                title = info.get("title", "douyin_video")
                # 清理文件名
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:100]
                target_path = str(task_dir / f"{safe_title}.{ext}")

                def _on_progress(percent, downloaded, total):
                    speed = ""
                    _tasks[task_id].update({
                        "progress": min(percent, 99),
                        "speed": speed,
                        "eta": "",
                    })

                download_douyin_file(
                    video_url=media_url,
                    target_path=target_path,
                    on_progress=_on_progress,
                )

                _tasks[task_id].update({
                    "status": "complete",
                    "progress": 100,
                    "filename": target_path,
                })
            except Exception as e:
                _tasks[task_id].update({
                    "status": "error",
                    "error": _strip_ansi(str(e)),
                })

        thread = threading.Thread(target=_do_douyin_download, daemon=True)
        thread.start()
        return task_id

    # 其他平台走 yt-dlp
    def _do_download():
        try:
            _tasks[task_id]["status"] = "downloading"

            def _progress_hook(d):
                if d["status"] == "downloading":
                    # 提取进度百分比
                    percent_str = d.get("_percent_str", "0%").strip().replace("%", "")
                    try:
                        percent = float(percent_str)
                    except ValueError:
                        percent = 0
                    _tasks[task_id].update({
                        "progress": min(percent, 99),
                        "speed": _strip_ansi(d.get("_speed_str", "")),
                        "eta": _strip_ansi(d.get("_eta_str", "")),
                    })
                elif d["status"] == "finished":
                    # 注意：合并格式时 finished 会对每个流分别触发
                    # 不在这里标记 complete，等 ydl.download 返回后再标记
                    _tasks[task_id].update({
                        "progress": 99,
                        "speed": "",
                        "eta": "",
                    })

            ydl_opts = {
                "format": format_id,
                "outtmpl": str(task_dir / "%(title)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "logger": _QuietLogger(),
                "progress_hooks": [_progress_hook],
                # 合并为 mp4 容器
                "merge_output_format": "mp4",
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # 下载完成（包括 merge），查找最终文件
            files = list(task_dir.iterdir())
            # 优先选择 mp4 文件（合并后的），排除临时文件
            mp4_files = [f for f in files if f.suffix == ".mp4" and f.is_file()]
            final_file = mp4_files[0] if mp4_files else (files[0] if files else None)

            if final_file:
                _tasks[task_id].update({
                    "status": "complete",
                    "progress": 100,
                    "filename": str(final_file),
                })
            else:
                _tasks[task_id].update({
                    "status": "error",
                    "error": "下载完成但未找到文件",
                })
        except Exception as e:
            _tasks[task_id].update({
                "status": "error",
                "error": _strip_ansi(str(e)),
            })

    thread = threading.Thread(target=_do_download, daemon=True)
    thread.start()
    return task_id


def get_task(task_id: str) -> dict | None:
    """获取任务状态"""
    return _tasks.get(task_id)


def get_task_file(task_id: str) -> Path | None:
    """获取已下载文件的路径"""
    task = _tasks.get(task_id)
    if not task or task["status"] != "complete":
        return None

    # 优先使用 hook 记录的 filename
    if task.get("filename") and os.path.isfile(task["filename"]):
        return Path(task["filename"])

    # 回退：扫描任务目录
    task_dir = DOWNLOADS_DIR / task_id
    if task_dir.exists():
        files = [f for f in task_dir.iterdir() if f.is_file()]
        if files:
            return files[0]
    return None


def cleanup_old_files():
    """清理过期的下载文件和已完成/失败的任务"""
    now = time.time()
    try:
        for task_dir in DOWNLOADS_DIR.iterdir():
            if not task_dir.is_dir():
                continue
            # 检查目录修改时间
            dir_mtime = task_dir.stat().st_mtime
            if now - dir_mtime > MAX_FILE_AGE:
                task_id = task_dir.name
                # 只清理已完成或失败的任务
                task = _tasks.get(task_id)
                if task is None or task["status"] in ("complete", "error"):
                    shutil.rmtree(task_dir, ignore_errors=True)
                    _tasks.pop(task_id, None)
    except Exception:
        pass  # 清理失败不影响主流程


def _cleanup_loop():
    """后台清理循环"""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cleanup_old_files()


# 启动后台清理线程
_cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
_cleanup_thread.start()
