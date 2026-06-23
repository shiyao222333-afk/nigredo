"""
⚗️ Nigredo — 数据分析引擎

整合字幕、弹幕、评论、统计数据，生成结构化分析报告。
"""
from dataclasses import dataclass
from core.danmaku import analyze_danmaku
from core.comment import analyze_comments


@dataclass
class VideoAnalysis:
    """视频完整分析结果"""
    video_id: str
    title: str
    author: str

    # 字幕
    subtitle_text: str = ""
    subtitle_source: str = ""   # cc / whisper

    # 文档
    study_notes: str = ""       # 学习笔记
    script_analysis: str = ""   # 脚本模仿
    doc_summary: str = ""       # 一句话摘要

    # 数据
    stats: dict = None
    danmaku_analysis: dict = None
    comment_analysis: dict = None

    # 质量标记
    subtitle_quality: str = "unknown"   # high / medium / low
    has_sales_signal: bool = False


def analyze_single_video(
    video_id: str,
    title: str,
    author: str,
    subtitle_text: str,
    subtitle_source: str,
    danmakus: list[dict] = None,
    comments: list[dict] = None,
    stats: dict = None,
) -> VideoAnalysis:
    """单视频完整分析"""
    return VideoAnalysis(
        video_id=video_id,
        title=title,
        author=author,
        subtitle_text=subtitle_text[:500],
        subtitle_source=subtitle_source,
        danmaku_analysis=analyze_danmaku(danmakus or []),
        comment_analysis=analyze_comments(comments or []),
        stats=stats or {},
        subtitle_quality=_judge_subtitle_quality(subtitle_source),
        has_sales_signal=(comment_analysis := analyze_comments(comments or []))["has_sales_signal"] if comments else False,
    )


def _judge_subtitle_quality(source: str) -> str:
    if source == "cc":
        return "high"
    elif source == "whisper":
        return "medium"
    return "low"
