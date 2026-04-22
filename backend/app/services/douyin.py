"""
抖音专用解析与下载服务 — 无需 Cookie
参考: https://github.com/rathodpratham-dev/douyin_video_downloader
"""
from __future__ import annotations

import base64
import json
import re
import time
import logging
from hashlib import sha256
from urllib.parse import urlparse, parse_qs

import httpx

logger = logging.getLogger("douyin")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_DOUYIN_DOMAINS = (
    "douyin.com",
    "iesdouyin.com",
    "v.douyin.com",
)

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/json,*/*",
    "Referer": "https://www.douyin.com/",
}

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.douyin.com/",
}

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

_ITEM_API = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"

MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0
TIMEOUT = (10, 30)


# ---------------------------------------------------------------------------
# 公共工具
# ---------------------------------------------------------------------------

def is_douyin_url(url: str) -> bool:
    """判断是否为抖音链接"""
    try:
        host = urlparse(url).hostname or ""
        return any(d in host for d in _DOUYIN_DOMAINS)
    except Exception:
        return False


def _extract_first_url(text: str) -> str:
    m = _URL_RE.search(text)
    if not m:
        raise ValueError("未找到有效的 URL")
    candidate = m.group(0).strip().strip('"').strip("'")
    return candidate.rstrip(").,;!?")


def _extract_video_id(url: str) -> str:
    """从抖音 URL 中提取视频 ID"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("modal_id", "item_ids", "group_id", "aweme_id"):
        values = query.get(key)
        if not values:
            continue
        m = re.search(r"(\d{8,24})", values[0])
        if m:
            return m.group(1)
    for pattern in (r"/video/(\d{8,24})", r"/note/(\d{8,24})", r"/(\d{8,24})(?:/|$)"):
        m = re.search(pattern, parsed.path)
        if m:
            return m.group(1)
    fallback = re.search(r"(?<!\d)(\d{8,24})(?!\d)", url)
    if fallback:
        return fallback.group(1)
    raise ValueError("无法从链接中提取视频 ID")


# ---------------------------------------------------------------------------
# WAF Challenge 求解
# ---------------------------------------------------------------------------

def _decode_urlsafe_b64(value: str) -> bytes:
    normalized = value.replace("-", "+").replace("_", "/")
    normalized += "=" * (-len(normalized) % 4)
    return base64.b64decode(normalized)


def _is_waf_challenge(html: str) -> bool:
    return "Please wait..." in html and 'wci="' in html and 'cs="' in html


def _solve_waf_cookie(html: str, page_url: str, client: httpx.Client) -> bool:
    m = re.search(r'wci="([^"]+)"\s*,\s*cs="([^"]+)"', html)
    if not m:
        return False
    cookie_name, challenge_blob = m.groups()
    try:
        challenge_data = json.loads(_decode_urlsafe_b64(challenge_blob).decode("utf-8"))
        prefix = _decode_urlsafe_b64(challenge_data["v"]["a"])
        expected_digest = _decode_urlsafe_b64(challenge_data["v"]["c"]).hex()
    except (KeyError, ValueError, TypeError):
        return False

    solved_value = None
    for candidate in range(1_000_001):
        digest = sha256(prefix + str(candidate).encode("utf-8")).hexdigest()
        if digest == expected_digest:
            solved_value = candidate
            break

    if solved_value is None:
        return False

    challenge_data["d"] = base64.b64encode(str(solved_value).encode("utf-8")).decode("utf-8")
    cookie_value = base64.b64encode(
        json.dumps(challenge_data, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8")

    domain = urlparse(page_url).hostname or "www.iesdouyin.com"
    client.cookies.set(cookie_name, cookie_value, domain=domain)
    logger.info("WAF challenge solved for %s", domain)
    return True


# ---------------------------------------------------------------------------
# 核心解析
# ---------------------------------------------------------------------------

def _resolve_redirect(client: httpx.Client, share_url: str) -> str:
    """解析短链接重定向"""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(share_url, follow_redirects=True, timeout=TIMEOUT[1])
            resp.raise_for_status()
            return str(resp.url)
        except Exception as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
    raise ValueError(f"无法解析抖音短链接: {last_error}")


def _fetch_item_from_api(client: httpx.Client, video_id: str) -> dict | None:
    """尝试通过公开 API 获取视频信息"""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(_ITEM_API, params={"item_ids": video_id}, timeout=TIMEOUT[1])
            if resp.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status_code") not in (0, None):
                return None
            items = data.get("item_list") or []
            if items:
                return items[0]
            return None
        except Exception as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
    logger.warning("API fetch failed for %s: %s", video_id, last_error)
    return None


def _extract_router_data(html: str) -> dict:
    """从 HTML 中提取 window._ROUTER_DATA JSON"""
    marker = "window._ROUTER_DATA = "
    start = html.find(marker)
    if start < 0:
        return {}
    index = start + len(marker)
    while index < len(html) and html[index].isspace():
        index += 1
    if index >= len(html) or html[index] != "{":
        return {}

    depth = 0
    in_string = False
    escaped = False
    for cursor in range(index, len(html)):
        char = html[cursor]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                payload = html[index: cursor + 1]
                try:
                    return json.loads(payload)
                except ValueError:
                    return {}
    return {}


def _get_item_from_router_data(router_data: dict) -> dict | None:
    """从 router data 中提取 item info"""
    loader_data = router_data.get("loaderData", {})
    if not isinstance(loader_data, dict):
        return None
    for node in loader_data.values():
        if not isinstance(node, dict):
            continue
        video_info_res = node.get("videoInfoRes", {})
        if not isinstance(video_info_res, dict):
            continue
        item_list = video_info_res.get("item_list", [])
        if item_list and isinstance(item_list[0], dict):
            return item_list[0]
    return None


def _fetch_item_from_share_page(client: httpx.Client, video_id: str, resolved_url: str) -> dict | None:
    """通过 share page HTML 解析获取视频信息（fallback）"""
    parsed = urlparse(resolved_url)
    if parsed.netloc and "iesdouyin.com" in parsed.netloc:
        share_url = resolved_url
    else:
        share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

    resp = client.get(share_url, headers=_MOBILE_HEADERS, timeout=TIMEOUT[1])
    resp.raise_for_status()
    html = resp.text or ""

    # 处理 WAF challenge
    if _is_waf_challenge(html):
        if _solve_waf_cookie(html, share_url, client):
            resp = client.get(share_url, headers=_MOBILE_HEADERS, timeout=TIMEOUT[1])
            resp.raise_for_status()
            html = resp.text or ""

    router_data = _extract_router_data(html)
    if not router_data:
        return None
    return _get_item_from_router_data(router_data)


# ---------------------------------------------------------------------------
# 公开接口: 解析
# ---------------------------------------------------------------------------

def parse_douyin_video(url: str) -> dict:
    """
    解析抖音视频链接，返回与 yt-dlp parse_video 兼容的格式。
    无需 Cookie，无需登录。
    """
    with httpx.Client(headers=_DEFAULT_HEADERS, follow_redirects=True, timeout=30) as client:
        # 1. 解析短链接
        share_url = _extract_first_url(url) if "v.douyin.com" in url else url
        resolved_url = _resolve_redirect(client, share_url)
        video_id = _extract_video_id(resolved_url)
        logger.info("Douyin video ID: %s", video_id)

        # 2. 获取视频元信息 (API 优先, share page fallback)
        item = _fetch_item_from_api(client, video_id)
        if not item:
            item = _fetch_item_from_share_page(client, video_id, resolved_url)
        if not item:
            raise ValueError("无法获取抖音视频信息，视频可能已被删除或不可用")

    # 3. 提取视频信息
    title = item.get("desc") or f"douyin_{video_id}"
    author = (item.get("author") or {}).get("nickname", "")

    video_data = item.get("video", {})
    duration = video_data.get("duration", 0)
    # 抖音 duration 单位是 毫秒
    duration_sec = duration // 1000 if duration > 1000 else duration

    # 缩略图
    cover = video_data.get("cover", {}).get("url_list", [])
    origin_cover = video_data.get("origin_cover", {}).get("url_list", [])
    thumbnail = (origin_cover or cover or [""])[0]

    # 视频尺寸
    width = video_data.get("width", 0)
    height = video_data.get("height", 0)

    # 4. 提取下载链接
    play_urls = video_data.get("play_addr", {}).get("url_list", [])
    if not play_urls:
        raise ValueError("未找到抖音视频播放地址")

    # 去水印: playwm -> play
    video_url = play_urls[0].replace("playwm", "play")

    # 5. 构造格式列表 (抖音通常只有一种格式 — 无水印原视频)
    formats = [{
        "format_id": "douyin_best",
        "ext": "mp4",
        "resolution": f"{width}x{height}" if width and height else "",
        "height": height or 720,
        "filesize": None,
        "note": f"无水印原视频{' (' + str(height) + 'p)' if height else ''}",
        "category": "best",
    }]

    # 音频
    music = item.get("music", {})
    audio_urls = music.get("play_url", {}).get("url_list", [])
    if audio_urls:
        formats.append({
            "format_id": "douyin_audio",
            "ext": "mp3",
            "resolution": "",
            "height": 0,
            "filesize": None,
            "note": f"音频 - {music.get('title', '原声')}",
            "category": "audio",
        })

    # duration_string
    if duration_sec:
        mins = duration_sec // 60
        secs = duration_sec % 60
        dur_str = f"{mins}:{secs:02d}"
    else:
        dur_str = ""

    return {
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration_sec or None,
        "duration_string": dur_str,
        "uploader": author,
        "platform": "douyin",
        "webpage_url": resolved_url if resolved_url else url,
        "formats": formats,
        # 抖音专用字段，下载时需要
        "_douyin_video_url": video_url,
        "_douyin_audio_url": audio_urls[0] if audio_urls else "",
    }


# ---------------------------------------------------------------------------
# 公开接口: 下载
# ---------------------------------------------------------------------------

def download_douyin_file(
    video_url: str,
    target_path: str,
    on_progress=None,
) -> str:
    """
    下载抖音视频文件到指定路径，支持进度回调。
    on_progress(percent: float, downloaded: int, total: int)
    返回最终文件路径。
    """
    headers = {
        **_MOBILE_HEADERS,
        "Accept": "*/*",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(follow_redirects=True, timeout=120) as client:
                with client.stream("GET", video_url, headers=headers) as resp:
                    if resp.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError(
                            f"HTTP {resp.status_code}", request=resp.request, response=resp
                        )
                    resp.raise_for_status()

                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0

                    with open(target_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded += len(chunk)
                            if on_progress and total > 0:
                                percent = min(downloaded * 100 / total, 99)
                                on_progress(percent, downloaded, total)

            # 验证文件大小
            import os
            file_size = os.path.getsize(target_path)
            if file_size < 1024:
                raise ValueError(f"下载文件异常小 ({file_size} bytes)，可能不是有效视频")

            if on_progress:
                on_progress(100, total, total)
            return target_path

        except Exception as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            wait = BACKOFF_FACTOR * (2 ** (attempt - 1))
            logger.warning("Download attempt %s failed: %s, retry in %.1fs", attempt, exc, wait)
            time.sleep(wait)

    raise ValueError(f"抖音视频下载失败: {last_error}")
