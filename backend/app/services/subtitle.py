"""字幕提取服务 — 通过 yt-dlp 提取视频平台内置字幕"""
import os
import re
import json
import tempfile
import logging
from pathlib import Path
from yt_dlp import YoutubeDL

from app.services.douyin import is_douyin_url
from app.services.bilibili_subtitle import is_bilibili_url, extract_bilibili_subtitles

logger = logging.getLogger("subtitle")

# 字幕语言优先级
_LANG_PRIORITY = ["zh-Hans", "zh-CN", "zh", "zh-TW", "en", "en-US", "ja", "ko"]


class _QuietLogger:
    """静默 logger"""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def _parse_vtt(content: str) -> list[dict]:
    """解析 VTT 格式字幕为结构化时间戳数组"""
    segments = []
    # 匹配时间戳行: 00:00:01.000 --> 00:00:05.000
    pattern = re.compile(
        r"(\d{1,2}:?\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:?\d{2}:\d{2}[.,]\d{3})"
    )
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        match = pattern.search(lines[i])
        if match:
            start = _timestamp_to_seconds(match.group(1))
            end = _timestamp_to_seconds(match.group(2))
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                line = lines[i].strip()
                # 去除 VTT 标签 <c>, </c>, <00:01:02.000> 等
                line = re.sub(r"<[^>]+>", "", line)
                if line:
                    text_lines.append(line)
                i += 1
            text = " ".join(text_lines)
            if text:
                segments.append({"start": start, "end": end, "text": text})
        i += 1
    return segments


def _parse_srt(content: str) -> list[dict]:
    """解析 SRT 格式字幕"""
    segments = []
    pattern = re.compile(
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
    )
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        for j, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                start = _timestamp_to_seconds(match.group(1).replace(",", "."))
                end = _timestamp_to_seconds(match.group(2).replace(",", "."))
                text = " ".join(
                    re.sub(r"<[^>]+>", "", l.strip())
                    for l in lines[j + 1:]
                    if l.strip()
                )
                if text:
                    segments.append({"start": start, "end": end, "text": text})
                break
    return segments


def _parse_json3(content: str) -> list[dict]:
    """解析 YouTube json3 格式字幕"""
    segments = []
    try:
        data = json.loads(content)
        events = data.get("events", [])
        for event in events:
            if "segs" not in event:
                continue
            start_ms = event.get("tStartMs", 0)
            duration_ms = event.get("dDurationMs", 0)
            text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
            if text and text != "\n":
                segments.append({
                    "start": start_ms / 1000,
                    "end": (start_ms + duration_ms) / 1000,
                    "text": text,
                })
    except (json.JSONDecodeError, KeyError):
        pass
    return segments


def _timestamp_to_seconds(ts: str) -> float:
    """将时间戳字符串转换为秒数: 00:01:30.500 -> 90.5"""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def _seconds_to_timestamp(seconds: float) -> str:
    """将秒数转换为时间戳: 90.5 -> 01:30"""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


# 需要跳过的"字幕"类型（如弹幕不是真正字幕）
_SKIP_LANGS = {"danmaku", "live_chat"}


def _select_best_subtitle(subtitles: dict, auto_subtitles: dict) -> tuple[str, str, dict]:
    """
    从可用字幕中选择最佳语言。
    返回 (language_code, source_type, subtitle_info)
    source_type: "manual" 或 "auto"
    """
    # 过滤掉弹幕等无效"字幕"
    clean_subs = {k: v for k, v in subtitles.items() if k not in _SKIP_LANGS}
    clean_auto = {k: v for k, v in auto_subtitles.items() if k not in _SKIP_LANGS}

    # 优先手动字幕
    for lang in _LANG_PRIORITY:
        if lang in clean_subs:
            return lang, "manual", clean_subs[lang]
    # 其次自动字幕
    for lang in _LANG_PRIORITY:
        if lang in clean_auto:
            return lang, "auto", clean_auto[lang]
    # 手动字幕中第一个可用
    if clean_subs:
        lang = next(iter(clean_subs))
        return lang, "manual", clean_subs[lang]
    # 自动字幕中第一个可用
    if clean_auto:
        lang = next(iter(clean_auto))
        return lang, "auto", clean_auto[lang]
    return "", "", {}


def _deduplicate_segments(segments: list[dict]) -> list[dict]:
    """去除连续重复的字幕行"""
    if not segments:
        return segments
    result = [segments[0]]
    for seg in segments[1:]:
        if seg["text"] != result[-1]["text"]:
            result.append(seg)
        else:
            # 合并时间范围
            result[-1]["end"] = seg["end"]
    return result


def extract_subtitles(url: str) -> dict:
    """
    提取视频字幕，返回结构化数据。

    Returns:
        {
            "available": True/False,
            "language": "zh-Hans",
            "source": "manual" | "auto",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "字幕文本"},
                ...
            ],
            "full_text": "完整字幕文本（用于 AI 总结）"
        }
    """
    # 抖音暂不支持字幕提取
    if is_douyin_url(url):
        return {
            "available": False,
            "language": "",
            "source": "",
            "segments": [],
            "full_text": "",
            "message": "抖音视频暂不支持字幕提取",
        }

    # B 站优先使用平台 API 提取字幕（创作者字幕 / AI 字幕）
    if is_bilibili_url(url):
        result = extract_bilibili_subtitles(url)
        if result.get("available"):
            return result
        # B 站平台 API 失败，fallback 到 yt-dlp
        logger.info("B站平台API未获取到字幕，fallback到yt-dlp: %s", result.get("message", ""))

    # 通用 yt-dlp 字幕提取（fallback）
    with tempfile.TemporaryDirectory() as tmp_dir:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": _QuietLogger(),
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "json3/vtt/srt/best",
            "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            info = ydl.sanitize_info(info)

        subtitles = info.get("subtitles") or {}
        auto_subtitles = info.get("automatic_captions") or {}

        if not subtitles and not auto_subtitles:
            return {
                "available": False,
                "language": "",
                "source": "",
                "segments": [],
                "full_text": "",
                "message": "该视频没有可用的字幕",
            }

        lang, source, sub_info = _select_best_subtitle(subtitles, auto_subtitles)
        if not sub_info:
            return {
                "available": False,
                "language": "",
                "source": "",
                "segments": [],
                "full_text": "",
                "message": "未找到合适的字幕语言",
            }

        # sub_info 是一个格式列表，选择最佳格式
        # 优先 json3 > vtt > srt
        sub_content = None
        sub_ext = None
        format_priority = {"json3": 0, "vtt": 1, "srv3": 2, "srt": 3}

        # 尝试下载字幕内容
        sorted_formats = sorted(
            sub_info,
            key=lambda x: format_priority.get(x.get("ext", ""), 99),
        )

        for fmt in sorted_formats:
            sub_url = fmt.get("url")
            if not sub_url:
                continue
            try:
                import httpx
                with httpx.Client(timeout=15, follow_redirects=True) as client:
                    resp = client.get(sub_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    })
                    resp.raise_for_status()
                    sub_content = resp.text
                    sub_ext = fmt.get("ext", "vtt")
                    break
            except Exception as e:
                logger.warning("Failed to download subtitle from %s: %s", sub_url, e)
                continue

        if not sub_content:
            return {
                "available": False,
                "language": lang,
                "source": source,
                "segments": [],
                "full_text": "",
                "message": "字幕下载失败",
            }

        # 解析字幕内容
        if sub_ext == "json3" or sub_ext == "srv3":
            segments = _parse_json3(sub_content)
        elif sub_ext == "srt":
            segments = _parse_srt(sub_content)
        else:
            segments = _parse_vtt(sub_content)

        # 去重
        segments = _deduplicate_segments(segments)

        # 生成完整文本（用于 AI 总结）
        full_text = "\n".join(seg["text"] for seg in segments)

        return {
            "available": True,
            "language": lang,
            "source": source,
            "segments": segments,
            "full_text": full_text,
        }
