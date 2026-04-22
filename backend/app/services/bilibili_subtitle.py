"""
B站字幕提取服务 — 通过 B站 dm/view API 直接获取创作者上传字幕 / AI 自动生成字幕
参考: https://github.com/liyupi/free-video-downloader
无需 WBI 签名、无需登录即可获取字幕。
"""
import re
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("bilibili_subtitle")

# ───────── 常量 ─────────
_BILI_DOMAINS = ("bilibili.com", "b23.tv")

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

_VIEW_API = "https://api.bilibili.com/x/web-interface/view"
_DM_VIEW_API = "https://api.bilibili.com/x/v2/dm/view"

# 字幕语言优先级
_SUBTITLE_LANG_PRIORITY = ["zh-CN", "zh", "zh-Hans", "ai-zh", "en", "ai-en", "ja", "ko"]


# ───────── URL 解析 ─────────

def is_bilibili_url(url: str) -> bool:
    """判断是否为 B 站链接"""
    try:
        host = urlparse(url).hostname or ""
        return any(d in host for d in _BILI_DOMAINS)
    except Exception:
        return False


def _extract_bvid(url: str) -> str:
    """从 B 站 URL 中提取 BV 号"""
    m = re.search(r"(BV[a-zA-Z0-9]{10,12})", url)
    if m:
        return m.group(1)
    return ""


def _extract_aid_from_url(url: str) -> int | None:
    """从 URL 中提取 aid"""
    m = re.search(r"av(\d+)", url, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _resolve_short_url(client: httpx.Client, url: str) -> str:
    """解析 B 站短链接 b23.tv"""
    if "b23.tv" not in url:
        return url
    resp = client.get(url, follow_redirects=True, timeout=10)
    return str(resp.url)


# ───────── API 调用 ─────────

def _get_video_info(client: httpx.Client, bvid: str = "", aid: int = 0) -> dict:
    """通过 x/web-interface/view 获取视频基本信息（aid, cid 等）"""
    params = {}
    if bvid:
        params["bvid"] = bvid
    elif aid:
        params["aid"] = aid
    else:
        raise ValueError("需要 bvid 或 aid")

    resp = client.get(_VIEW_API, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise ValueError(f"B站视频信息获取失败: {data.get('message', '未知错误')}")

    return data["data"]


def _get_subtitles_via_dm(client: httpx.Client, aid: int, cid: int) -> list[dict]:
    """
    通过 dm/view 接口获取字幕列表。
    此接口无需 WBI 签名、无需登录即可返回 CC 字幕和 AI 字幕。
    """
    resp = client.get(
        _DM_VIEW_API,
        params={"aid": aid, "oid": cid, "type": 1},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        logger.warning("dm/view API code=%s: %s", data.get("code"), data.get("message"))
        return []

    return data.get("data", {}).get("subtitle", {}).get("subtitles", [])


# ───────── 字幕选择与下载 ─────────

def _select_best_subtitle(subtitles: list[dict]) -> dict | None:
    """从字幕列表中按优先级选择最佳字幕"""
    if not subtitles:
        return None
    for lang in _SUBTITLE_LANG_PRIORITY:
        for sub in subtitles:
            if sub.get("lan") == lang:
                return sub
    return subtitles[0]


def _download_subtitle_json(client: httpx.Client, subtitle_url: str) -> list[dict]:
    """下载 B 站字幕 JSON 并解析为标准 segments"""
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    if subtitle_url.startswith("http://"):
        subtitle_url = "https://" + subtitle_url[7:]

    resp = client.get(subtitle_url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    segments = []
    for item in data.get("body", []):
        text = item.get("content", "").strip()
        if not text:
            continue
        segments.append({
            "start": round(item.get("from", 0), 2),
            "end": round(item.get("to", 0), 2),
            "text": text,
        })
    return segments


# ───────── 主入口 ─────────

def extract_bilibili_subtitles(url: str) -> dict:
    """
    通过 B 站 dm/view API 提取视频字幕。

    流程:
    1. 解析 URL → bvid / aid
    2. x/web-interface/view → aid, cid
    3. x/v2/dm/view → 字幕列表（含 subtitle_url）
    4. 下载字幕 JSON → segments
    """
    _empty = {
        "available": False,
        "language": "",
        "source": "bilibili_api",
        "segments": [],
        "full_text": "",
    }

    with httpx.Client(headers=_DEFAULT_HEADERS, follow_redirects=True, timeout=30) as client:
        try:
            # 1. 解析短链接
            resolved_url = _resolve_short_url(client, url)

            # 2. 提取 bvid / aid
            bvid = _extract_bvid(resolved_url)
            aid = _extract_aid_from_url(resolved_url) if not bvid else 0

            if not bvid and not aid:
                return {**_empty, "message": "无法从 B 站链接中提取视频 ID"}

            # 3. 获取视频基本信息
            video_info = _get_video_info(client, bvid=bvid, aid=aid)
            real_aid = video_info.get("aid", 0)
            cid = video_info.get("cid", 0)

            if not real_aid or not cid:
                return {**_empty, "message": "无法获取 B 站视频 ID 信息"}

            # 4. 通过 dm/view 接口获取字幕列表
            subtitles_list = _get_subtitles_via_dm(client, real_aid, cid)

            if not subtitles_list:
                return {**_empty, "message": "该 B 站视频没有可用的字幕（创作者未上传字幕且无 AI 字幕）"}

            # 5. 选择最佳字幕
            best = _select_best_subtitle(subtitles_list)
            if not best:
                return {**_empty, "message": "未找到合适的字幕语言"}

            subtitle_url = best.get("subtitle_url", "")
            if not subtitle_url:
                return {**_empty, "message": "字幕 URL 为空"}

            sub_type = "auto" if best.get("lan", "").startswith("ai-") else "manual"

            # 6. 下载并解析字幕
            segments = _download_subtitle_json(client, subtitle_url)

            if not segments:
                return {**_empty, "message": "字幕内容为空"}

            full_text = "\n".join(seg["text"] for seg in segments)

            return {
                "available": True,
                "language": best.get("lan", ""),
                "language_doc": best.get("lan_doc", ""),
                "source": f"bilibili_api ({sub_type})",
                "segments": segments,
                "full_text": full_text,
            }

        except ValueError as e:
            return {**_empty, "message": str(e)}
        except Exception as e:
            logger.warning("B站字幕提取异常: %s", e)
            return {**_empty, "message": f"B 站字幕提取失败: {e}"}
