"""
⚗️ Nigredo — 下载管理器

统一入口：URL 输入 → 平台识别 → 下载调度。
"""
from pathlib import Path
import re

from platforms.bilibili import BilibiliPlatform
from utils.cache import VideoCache
from config import CACHE_DIR, BILIBILI_COOKIE


# ═══════════════════════════════════════════
# URL 路由
# ═══════════════════════════════════════════

PLATFORMS = [
    ("bilibili", re.compile(r"(bilibili\.com|b23\.tv|BV[a-zA-Z0-9]{10})")),
    # 未来扩展:
    # ("youtube", re.compile(r"(youtube\.com|youtu\.be)")),
    # ("xiaohongshu", re.compile(r"xiaohongshu\.com")),
]


def detect_platform(url: str) -> str:
    """检测 URL 所属平台"""
    for platform, pattern in PLATFORMS:
        if pattern.search(url):
            return platform
    return "unknown"


# ═══════════════════════════════════════════
# 下载工作流
# ═══════════════════════════════════════════

class DownloadManager:
    """统一管理下载流程"""

    def __init__(self):
        self.cache = VideoCache(CACHE_DIR)
        self._bilibili = BilibiliPlatform(cookie=BILIBILI_COOKIE)

    def process(self, url: str) -> dict:
        """
        完整处理流程：
        1. URL → 平台识别 → BV号提取
        2. 去重检查
        3. 获取视频元数据
        4. 下载音频
        5. 返回结果
        """
        platform = detect_platform(url)

        if platform == "bilibili":
            return self._process_bilibili(url)
        else:
            raise NotImplementedError(f"平台 '{platform}' 尚未支持。请在 GitHub issue 中提交需求。")

    def _process_bilibili(self, url: str) -> dict:
        """B站 完整处理"""
        bv_id = self._bilibili.parse_url(url)
        if not bv_id:
            raise ValueError(f"无法从 URL 提取 BV 号: {url}")

        # 去重
        if self.cache.is_processed(bv_id):
            metadata = self.cache.get_metadata(bv_id)
            return {"status": "cached", "video_id": bv_id, **metadata}

        # 获取信息
        info = self._bilibili.get_video_info(bv_id)

        # 下载音频
        audio_path = self._bilibili.download_audio(bv_id, str(CACHE_DIR))

        # 缓存
        result = {
            "status": "done",
            "video_id": bv_id,
            "info": info.__dict__,
            "audio_path": audio_path,
        }
        self.cache.mark_processed(bv_id, result)

        return result
