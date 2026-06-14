"""
⚗️ Alembic — B站 平台适配器
"""
import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from . import VideoInfo, SubtitleResult

# BV 号正则
BV_PATTERN = re.compile(r"(BV[a-zA-Z0-9]{10})")
# 短链接匹配
B23_PATTERN = re.compile(r"(b23\.tv/[a-zA-Z0-9]+)")


class BilibiliPlatform:
    """B站平台适配器"""

    PLATFORM = "bilibili"

    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self._api = None  # 惰性加载 bilibili-api

    # ── URL 解析 ──────────────────────────

    def parse_url(self, url: str) -> Optional[str]:
        """从 URL 中提取 BV 号"""
        m = BV_PATTERN.search(url)
        if m:
            return m.group(1)
        # TODO: 短链接 b23.tv 解析
        return None

    # ── 视频信息 ──────────────────────────

    def get_video_info(self, video_id: str) -> VideoInfo:
        """通过 bilibili-api-python 获取视频元数据"""
        self._ensure_api()
        try:
            v = self._api.video.Video(bvid=video_id)
            info = v.get_info()
        except Exception:
            # API 不工作时用 yt-dlp 兜底
            return self._get_info_via_ytdlp(video_id)

        stat = info.get("stat", {})
        owner = info.get("owner", {})
        return VideoInfo(
            platform="bilibili",
            video_id=video_id,
            title=info.get("title", ""),
            description=info.get("desc", ""),
            author=owner.get("name", ""),
            author_id=str(owner.get("mid", "")),
            duration_seconds=info.get("duration", 0),
            cover_url=info.get("pic", ""),
            published_at=self._ts_to_iso(info.get("pubdate", 0)),
            url=f"https://www.bilibili.com/video/{video_id}",
            view_count=stat.get("view", 0),
            like_count=stat.get("like", 0),
            coin_count=stat.get("coin", 0),
            favorite_count=stat.get("favorite", 0),
            share_count=stat.get("share", 0),
            comment_count=stat.get("reply", 0),
            danmaku_count=stat.get("danmaku", 0),
            has_cc_subtitle=info.get("subtitle", {}).get("allow_submit", False),
        )

    def _get_info_via_ytdlp(self, video_id: str) -> VideoInfo:
        """yt-dlp 兜底获取信息"""
        url = f"https://www.bilibili.com/video/{video_id}"
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-playlist", url],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)
            return VideoInfo(
                platform="bilibili",
                video_id=video_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                author=data.get("uploader", ""),
                author_id=data.get("uploader_id", ""),
                duration_seconds=int(data.get("duration", 0)),
                cover_url=data.get("thumbnail", ""),
                published_at=data.get("upload_date", ""),
                url=url,
                view_count=data.get("view_count", 0),
                like_count=data.get("like_count", 0),
                comment_count=data.get("comment_count", 0),
            )
        except Exception:
            return VideoInfo(
                platform="bilibili",
                video_id=video_id,
                title="获取失败",
                description="",
                author="",
                author_id="",
                duration_seconds=0,
                cover_url="",
                published_at="",
                url=f"https://www.bilibili.com/video/{video_id}",
            )

    # ── 下载音频 ──────────────────────────

    def download_audio(self, video_id: str, output_dir: str) -> str:
        """使用 yt-dlp 下载音频"""
        url = f"https://www.bilibili.com/video/{video_id}"
        output_path = Path(output_dir) / f"{video_id}"
        cmd = [
            "yt-dlp",
            "-f", "worstaudio",       # 最小音频（够用）
            "-x", "--audio-format", "wav",
            "-o", f"{output_path}.%(ext)s",
            "--no-playlist",
            url,
        ]
        if self.cookie:
            cmd.extend(["--cookies-from-browser", "edge"])
        subprocess.run(cmd, check=True, timeout=120)
        return f"{output_path}.wav"

    # ── 字幕提取 ──────────────────────────

    def extract_subtitle(self, video_id: str) -> SubtitleResult:
        """优先提取 B站 CC 字幕"""
        self._ensure_api()
        try:
            v = self._api.video.Video(bvid=video_id)
            info = v.get_info()
            subtitle_list = info.get("subtitle", {}).get("list", [])
            if not subtitle_list:
                return SubtitleResult(source="cc_not_found", language="", full_text="")

            # 取第一个中文字幕
            sub_url = subtitle_list[0]["subtitle_url"]
            if not sub_url.startswith("http"):
                sub_url = "https:" + sub_url

            import requests
            resp = requests.get(sub_url, timeout=10)
            data = resp.json()
            segments = []
            full_text_parts = []
            for item in data.get("body", []):
                text = item.get("content", "")
                segments.append({
                    "start": item.get("from", 0),
                    "end": item.get("to", 0),
                    "text": text,
                })
                full_text_parts.append(text)

            return SubtitleResult(
                source="cc",
                language="zh",
                segments=segments,
                full_text="\n".join(full_text_parts),
            )
        except Exception:
            return SubtitleResult(source="error", language="", full_text="")

    # ── 弹幕 ─────────────────────────────

    def get_danmaku(self, video_id: str) -> list[dict]:
        """获取视频弹幕列表"""
        self._ensure_api()
        try:
            v = self._api.video.Video(bvid=video_id)
            danmakus = v.get_danmakus(page_index=0)
            return [
                {
                    "text": d.text,
                    "time": d.dm_time,        # 弹幕出现时间(秒)
                    "send_time": d.send_time,  # 发送时间戳
                    "mode": d.mode,            # 1-滚动 4-底部 5-顶部
                    "color": d.color,
                }
                for d in danmakus
            ]
        except Exception:
            return []

    # ── 评论 ─────────────────────────────

    def get_comments(self, video_id: str, max_count: int = 200) -> list[dict]:
        """获取视频评论"""
        self._ensure_api()
        comments = []
        try:
            v = self._api.video.Video(bvid=video_id)
            page = 1
            while len(comments) < max_count:
                resp = v.get_comments(page_index=page)
                if not resp.get("replies"):
                    break
                for r in resp["replies"]:
                    comments.append({
                        "text": r.get("content", {}).get("message", ""),
                        "user": r.get("member", {}).get("uname", ""),
                        "likes": r.get("like", 0),
                        "time": r.get("ctime", 0),
                    })
                    if len(comments) >= max_count:
                        break
                page += 1
        except Exception:
            pass
        return comments

    # ── 辅助 ─────────────────────────────

    def _ensure_api(self):
        if self._api is None:
            import bilibili_api
            if self.cookie:
                bilibili_api.credential.Credential(sessdata=self._parse_sessdata())
            self._api = bilibili_api

    def _parse_sessdata(self) -> str:
        """从 cookie 字符串中提取 SESSDATA"""
        for item in self.cookie.split(";"):
            item = item.strip()
            if item.startswith("SESSDATA="):
                return item.split("=", 1)[1]
        return ""

    @staticmethod
    def _ts_to_iso(ts: int) -> str:
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=8))
        return datetime.fromtimestamp(ts, tz=tz).isoformat()
