"""
⚗️ Alembic — 数据采集器

统一从各平台获取视频统计数据。
"""
from platforms.bilibili import BilibiliPlatform
from config import BILIBILI_COOKIE


class DataFetcher:
    """统一数据获取接口"""

    def __init__(self):
        self._bilibili = BilibiliPlatform(cookie=BILIBILI_COOKIE)

    def fetch_stats(self, platform: str, video_id: str) -> dict:
        """获取视频统计数据"""
        if platform == "bilibili":
            info = self._bilibili.get_video_info(video_id)
            return {
                "view_count": info.view_count,
                "like_count": info.like_count,
                "coin_count": info.coin_count,
                "favorite_count": info.favorite_count,
                "share_count": info.share_count,
                "comment_count": info.comment_count,
                "danmaku_count": info.danmaku_count,
                # 计算指标
                "engagement_rate": self._calc_engagement_rate(info),
                "estimated_value": self._estimate_value(info),
            }
        raise NotImplementedError(f"平台 '{platform}' 数据采集尚未实现")

    @staticmethod
    def _calc_engagement_rate(info) -> float:
        """互动率 = (点赞+投币+收藏+分享) / 播放量"""
        views = info.view_count or 1
        interactions = (info.like_count or 0) + (info.coin_count or 0) + \
                       (info.favorite_count or 0) + (info.share_count or 0)
        return round(interactions / views * 100, 2)

    @staticmethod
    def _estimate_value(info) -> dict:
        """估算价值（基于播放量和互动率的粗略公式）"""
        views = info.view_count or 0
        # B站千次播放估值（仅供参考，实际取决于商业合作）
        cpm = 30  # ¥/千次
        return {
            "estimated_income": round(views / 1000 * cpm, 2),
            "currency": "CNY",
            "disclaimer": "基于 CPM 估算，实际收入取决于商业合作和创作者激励",
        }
