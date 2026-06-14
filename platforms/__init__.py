"""
⚗️ Alembic — 平台适配器抽象基类

所有平台（B站/YouTube/小红书等）必须实现此接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VideoInfo:
    """平台无关的视频元数据"""
    platform: str                 # bilibili / youtube / xiaohongshu
    video_id: str                 # BV号 / YouTube ID
    title: str
    description: str
    author: str
    author_id: str
    duration_seconds: int
    cover_url: str
    published_at: str             # ISO 8601
    url: str

    # 统计数据（可能为 None，表示未获取）
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    coin_count: Optional[int] = None   # B站特有
    favorite_count: Optional[int] = None
    share_count: Optional[int] = None
    comment_count: Optional[int] = None
    danmaku_count: Optional[int] = None  # B站特有

    # 字幕
    has_cc_subtitle: bool = False
    cc_subtitle_url: Optional[str] = None


@dataclass
class SubtitleResult:
    """字幕提取结果"""
    source: str                   # cc / whisper
    language: str
    segments: list = field(default_factory=list)
    # 每个 segment: {"start": float, "end": float, "text": str}
    full_text: str = ""


class BasePlatform(ABC):
    """平台适配器基类"""

    @abstractmethod
    def parse_url(self, url: str) -> Optional[str]:
        """从 URL 中提取视频 ID"""
        ...

    @abstractmethod
    def get_video_info(self, video_id: str) -> VideoInfo:
        """获取视频元数据"""
        ...

    @abstractmethod
    def download_audio(self, video_id: str, output_dir: str) -> str:
        """下载音频，返回音频文件路径"""
        ...

    @abstractmethod
    def extract_subtitle(self, video_id: str) -> SubtitleResult:
        """提取字幕（优先CC，否则返回空）"""
        ...

    @abstractmethod
    def get_comments(self, video_id: str, max_count: int = 200) -> list[dict]:
        """获取评论列表"""
        ...

    @abstractmethod
    def get_danmaku(self, video_id: str) -> list[dict]:
        """获取弹幕（仅B站有效；其他平台返回空列表）"""
        ...
