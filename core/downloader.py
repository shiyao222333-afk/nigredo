"""
⚗️ Nigredo — 下载管理器

统一入口：URL 输入 → 平台识别 → 下载调度。
"""
from pathlib import Path
import re
import logging

from platforms import SubtitleResult
from platforms.bilibili import BilibiliPlatform
from core.subtitle import transcribe_with_whisper
from utils.cache import VideoCache
from config import CACHE_DIR, BILIBILI_COOKIE, BILIBILI_BROWSER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════
# URL 路由
# ═══════════════════════════════════════

PLATFORMS = [
    ("bilibili", re.compile(r"(bilibili\.com|b23\.tv|BV[a-zA-Z0-9]{10})")),
]


def detect_platform(url: str) -> str:
    """检测 URL 所属平台"""
    for platform, pattern in PLATFORMS:
        if pattern.search(url):
            return platform
    return "unknown"


# ═══════════════════════════════════════
# 下载工作流
# ═══════════════════════════════════════

class DownloadManager:
    """统一管理下载流程"""

    def __init__(self):
        self.cache = VideoCache(CACHE_DIR)
        self._bilibili = BilibiliPlatform(cookie=BILIBILI_COOKIE, browser=BILIBILI_BROWSER)
        logger.info("DownloadManager 初始化完成")

    def process(self, url: str, cookie: str = None, browser: str = None) -> dict:
        """
        完整处理流程：
        1. URL → 平台识别 → BV号提取
        2. 去重检查
        3. 获取视频元数据
        4. 下载音频
        5. 提取字幕
        6. 返回结果

        参数:
        - cookie / browser：运行时覆盖（来自「引擎配置」页面的 UI 设置）。
          不传则用初始化时的默认值（来自 .env）。
        """
        # 运行时覆盖：让界面里的 Cookie / 浏览器设置即时生效
        if cookie is not None:
            self._bilibili.cookie = cookie
        if browser is not None:
            self._bilibili.browser = browser

        platform = detect_platform(url)
        logger.info(f"检测到平台: {platform}, URL: {url[:50]}...")

        if platform == "bilibili":
            return self._process_bilibili(url)
        else:
            raise NotImplementedError(f"平台 '{platform}' 尚未支持。请在 GitHub issue 中提交需求。")

    def _process_bilibili(self, url: str) -> dict:
        """B站 完整处理（含字幕生成）"""
        bv_id = self._bilibili.parse_url(url)
        if not bv_id:
            raise ValueError(f"无法从 URL 提取 BV 号: {url}")

        # 去重
        if self.cache.is_processed(bv_id):
            metadata = self.cache.get_metadata(bv_id)
            logger.info(f"视频已缓存，跳过: {bv_id}")
            return {
                "status": "cached",
                "video_id": bv_id,
                "info": metadata.get("info", {}),
                "audio_path": metadata.get("audio_path", ""),
                "subtitle": metadata.get("subtitle"),
            }

        # 获取信息
        logger.info(f"获取视频信息: {bv_id}")
        info = self._bilibili.get_video_info(bv_id)

        # 下载音频
        logger.info(f"下载音频: {bv_id}")
        audio_path = self._bilibili.download_audio(bv_id, str(CACHE_DIR))
        logger.info(f"音频下载完成: {audio_path}")

        # 提取字幕（优先 CC，失败则用 Whisper）
        logger.info(f"提取字幕: {bv_id}")
        subtitle = self._extract_subtitle_with_fallback(bv_id, audio_path)
        if subtitle and subtitle.full_text:
            logger.info(f"字幕生成成功，来源: {subtitle.source}")
        else:
            logger.warning(f"字幕生成失败: {bv_id}")

        # 构建结果
        result = {
            "status": "done",
            "video_id": bv_id,
            "info": info.__dict__,
            "audio_path": audio_path,
            "subtitle": subtitle.__dict__ if subtitle else None,
        }
        self.cache.mark_processed(bv_id, result)
        logger.info(f"处理完成: {bv_id}")

        return result

    def _extract_subtitle_with_fallback(self, bv_id: str, audio_path: str):
        """
        提取字幕：优先 CC，失败则用 Whisper ASR

        策略：
        1. 尝试提取 B站 CC 字幕（快速、免费）
        2. 如果 CC 字幕不可用，用 Whisper ASR（慢、吃资源、但兜底）
        """

        # 1. 尝试提取 CC 字幕
        try:
            subtitle = self._bilibili.extract_subtitle(bv_id)
            if subtitle and subtitle.full_text:
                logger.info(f"CC 字幕提取成功: {bv_id}")
                return subtitle
        except Exception as e:
            logger.warning(f"CC 字幕提取失败，将使用 Whisper ASR: {e}")

        # 2. CC 字幕不可用，尝试 Whisper ASR
        try:
            logger.info(f"启动 Whisper ASR: {bv_id}")
            whisper_segments = transcribe_with_whisper(audio_path)

            # whisper_segments 已经是 [{"start": ..., "end": ..., "text": ...}, ...]
            # 无需转换，直接用
            segments = whisper_segments
            full_text = "\n".join(s["text"] for s in whisper_segments)

            logger.info(f"Whisper ASR 完成，片段数: {len(segments)}")
            return SubtitleResult(
                source="whisper",
                language="zh",
                segments=segments,
                full_text=full_text,
            )
        except Exception as e:
            logger.error(f"Whisper ASR 也失败: {e}")
            # 两者都失败，返回空结果
            return SubtitleResult(source="error", language="", full_text="")
