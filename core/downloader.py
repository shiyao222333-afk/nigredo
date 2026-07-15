"""
⚗️ Nigredo — 下载管理器

统一入口：URL 输入 → 平台识别 → 下载调度。
"""
from pathlib import Path
import re
import logging

from platforms import SubtitleResult
from platforms.bilibili import BilibiliPlatform
from core.subtitle import transcribe_with_whisper, format_subtitle_srt
from utils.cache import VideoCache
from config import CACHE_DIR, BILIBILI_COOKIE, BILIBILI_BROWSER, OUTPUT_DIR, REQUIRE_HUMAN_REVIEW

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

        # 获取弹幕与评论（读取视频互动数据，供下游炼真/数据分析消费）
        logger.info(f"获取弹幕与评论: {bv_id}")
        danmakus = self._bilibili.get_danmaku(bv_id) or []
        comments = self._bilibili.get_comments(bv_id) or []
        logger.info(f"弹幕 {len(danmakus)} 条 / 评论 {len(comments)} 条")

        # 构建结果
        result = {
            "status": "done",
            "video_id": bv_id,
            "info": info.__dict__,
            "audio_path": audio_path,
            "subtitle": subtitle.__dict__ if subtitle else None,
            "danmakus": danmakus,
            "comments": comments,
        }
        self.cache.mark_processed(bv_id, result)
        # 字幕落盘：转写结果原本只留内存，刷新即丢。这里额外存文件，
        # 供下游（如 Albedo 炼真）直接「选文件」摄入。
        self._save_subtitle_files(bv_id, subtitle)
        # 中转①落盘（文件夹契约）：写 {bv}.md 供 Albedo 炼真监控消费
        self._save_transit_md(bv_id, info, subtitle, danmakus, comments)
        logger.info(f"处理完成: {bv_id}")

        return result

    def _save_subtitle_files(self, bv_id: str, subtitle) -> list:
        """
        字幕结果落盘（新增，2026-07-09）：
        转写/提取出的字幕原本只存在内存，刷新即丢。这里额外存成文件，
        供下游（如 Albedo 炼真）直接「选文件」摄入。
        - {bv_id}.txt : 纯文本（下游最干净的摄入格式）
        - {bv_id}.srt : 带时间轴（供人工校对）
        无内容则返回空列表，不影响主流程。
        """
        if not subtitle or not getattr(subtitle, "full_text", "").strip():
            return []
        cache_dir = self.cache.cache_dir
        saved = []
        try:
            txt_path = cache_dir / f"{bv_id}.txt"
            txt_path.write_text(subtitle.full_text, encoding="utf-8")
            saved.append(str(txt_path))
        except Exception as e:
            logger.warning(f"字幕 .txt 落盘失败: {e}")
        segs = getattr(subtitle, "segments", None)
        if segs:
            try:
                srt_path = cache_dir / f"{bv_id}.srt"
                srt_path.write_text(format_subtitle_srt(segs), encoding="utf-8")
                saved.append(str(srt_path))
            except Exception as e:
                logger.warning(f"字幕 .srt 落盘失败: {e}")
        if saved:
            logger.info(f"字幕已落盘({len(saved)}个): {bv_id}")
        return saved

    def _save_transit_md(self, bv_id: str, info, subtitle,
                         danmakus=None, comments=None) -> list:
        """
        中转①落盘（文件夹契约，2026-07-12）：
        把处理结果写成 {bv_id}.md（YAML frontmatter 带元数据 + 正文=字幕），
        供下游 Albedo 炼真 的监控模块直接消费。
        - REQUIRE_HUMAN_REVIEW=false：写进 OUTPUT_DIR 根（被 Albedo 监控）
        - REQUIRE_HUMAN_REVIEW=true：写进 OUTPUT_DIR/review_pending/（待人工/总管晋级）
        元信息字段对齐 Albedo 的 AlbedoInput：title / up_name / video_id / source_url / platform。
        正文 = 字幕 full_text。
        2026-07-15 增强：frontmatter 写入播放/点赞/投币/收藏/分享/评论/弹幕计数；
        弹幕与评论全文写入 sidecar 文件 {bv}_danmaku.txt / {bv}_comments.txt（同目录），
        供炼真/数据分析消费，不污染字幕正文语义。
        """
        if not subtitle or not getattr(subtitle, "full_text", "").strip():
            return []
        import json

        def _scalar(v):
            return json.dumps(v, ensure_ascii=False)

        def _stat(attr):
            return getattr(info, attr, None)

        lines = [
            "---",
            f"platform: {_scalar(getattr(info, 'platform', 'bilibili'))}",
            f"video_id: {_scalar(getattr(info, 'video_id', bv_id))}",
            f"title: {_scalar(getattr(info, 'title', ''))}",
            f"up_name: {_scalar(getattr(info, 'author', ''))}",
            f"source_url: {_scalar(getattr(info, 'url', ''))}",
            f"view_count: {_scalar(_stat('view_count'))}",
            f"like_count: {_scalar(_stat('like_count'))}",
            f"coin_count: {_scalar(_stat('coin_count'))}",
            f"favorite_count: {_scalar(_stat('favorite_count'))}",
            f"share_count: {_scalar(_stat('share_count'))}",
            f"comment_count: {_scalar(_stat('comment_count'))}",
            f"danmaku_count: {_scalar(_stat('danmaku_count'))}",
            "---",
            "",
            subtitle.full_text,
        ]
        content = "\n".join(lines)
        target_dir = OUTPUT_DIR
        if REQUIRE_HUMAN_REVIEW:
            target_dir = OUTPUT_DIR / "review_pending"
        saved = []
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            md_path = target_dir / f"{bv_id}.md"
            md_path.write_text(content, encoding="utf-8")
            saved.append(str(md_path))
            logger.info(
                f"中转①已落盘: {md_path} (人审={'开' if REQUIRE_HUMAN_REVIEW else '关'})"
            )
        except Exception as e:
            logger.warning(f"中转① .md 落盘失败: {e}")
            return saved

        # 弹幕 sidecar（全文，[时间] 文本）
        if danmakus:
            try:
                dm_path = target_dir / f"{bv_id}_danmaku.txt"
                dm_lines = []
                for d in danmakus:
                    t = d.get("time", 0) or 0
                    txt = (d.get("text") or "").replace("\n", " ").strip()
                    if txt:
                        dm_lines.append(f"[{t:.0f}s] {txt}")
                if dm_lines:
                    dm_path.write_text("\n".join(dm_lines), encoding="utf-8")
                    saved.append(str(dm_path))
            except Exception as e:
                logger.warning(f"弹幕 sidecar 落盘失败: {e}")

        # 评论 sidecar（全文，[赞数] 用户: 文本）
        if comments:
            try:
                cm_path = target_dir / f"{bv_id}_comments.txt"
                cm_lines = []
                for c in comments:
                    user = c.get("user", "") or ""
                    likes = c.get("likes", 0) or 0
                    txt = (c.get("text") or "").replace("\n", " ").strip()
                    if txt:
                        cm_lines.append(f"[{likes}赞] {user}: {txt}")
                if cm_lines:
                    cm_path.write_text("\n".join(cm_lines), encoding="utf-8")
                    saved.append(str(cm_path))
            except Exception as e:
                logger.warning(f"评论 sidecar 落盘失败: {e}")

        return saved

    def _extract_subtitle_with_fallback(self, bv_id: str, audio_path: str):
        """
        提取字幕三级策略：CC → AI 字幕 → Whisper ASR

        策略：
        1. 优先提取 B站 CC 字幕（人工校对，质量最高、最快）
        2. CC 不可用则直取 B站 AI 字幕（机器生成，纯网络、不需要 GPU）
        3. AI 字幕也不可用，回退 Whisper ASR（慢、吃资源、但兜底）
        """

        # 1. 尝试提取 CC 字幕
        try:
            subtitle = self._bilibili.extract_subtitle(bv_id)
            if subtitle and subtitle.full_text:
                logger.info(f"CC 字幕提取成功: {bv_id}")
                return subtitle
        except Exception as e:
            logger.warning(f"CC 字幕提取失败，尝试 AI 字幕: {e}")

        # 2. CC 字幕不可用，尝试直取 B站 AI 字幕（WBI 签名，纯网络请求）
        try:
            subtitle = self._bilibili.extract_ai_subtitle(bv_id)
            if subtitle and subtitle.full_text:
                logger.info(f"AI 字幕提取成功: {bv_id}")
                return subtitle
        except Exception as e:
            logger.warning(f"AI 字幕提取失败，将使用 Whisper ASR: {e}")

        # 3. AI 字幕不可用，尝试 Whisper ASR
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
