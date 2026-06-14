"""
⚗️ Alembic — 弹幕分析

B站独有的互动数据维度。
"""
from collections import Counter


def analyze_danmaku(danmakus: list[dict]) -> dict:
    """
    弹幕分析 → 提取洞察

    返回:
        - density_curve: 弹幕密度时间曲线
        - hot_keywords: 高频弹幕词
        - peak_moments: 精彩片段定位
        - sentiment: 情绪分布
    """
    if not danmakus:
        return _empty_result()

    texts = [d["text"] for d in danmakus if d.get("text")]

    # 1. 密度曲线（按秒聚合）
    density = {}
    for d in danmakus:
        sec = int(d.get("time", 0))
        density[sec] = density.get(sec, 0) + 1

    # 峰值时刻（top 5）
    peaks = sorted(density.items(), key=lambda x: x[1], reverse=True)[:5]

    # 2. 高频词（排除常见弹幕词）
    stop_words = {"1", "2", "3", "？", "！", "。", "哈哈", "来了", "打卡", "前排", "第一"}
    words = []
    for text in texts:
        for w in text.strip().split():
            w = w.strip()
            if w and w not in stop_words and len(w) > 1:
                words.append(w)

    keyword_freq = Counter(words).most_common(20)

    # 3. 简单情绪分析（基于关键词）
    positive_words = {"好", "好看", "精彩", "厉害", "优秀", "不错", "爱了", "喜欢"}
    negative_words = {"差", "烂", "无聊", "不行", "不好看", "尬", "尴尬"}

    pos_count = sum(1 for t in texts if any(w in t for w in positive_words))
    neg_count = sum(1 for t in texts if any(w in t for w in negative_words))
    total = len(texts) or 1

    return {
        "total_danmaku": len(danmakus),
        "density_curve": sorted(density.items())[:100],  # 前100秒
        "peak_moments": [{"second": s, "count": c} for s, c in peaks],
        "hot_keywords": [{"word": w, "count": c} for w, c in keyword_freq],
        "sentiment": {
            "positive_pct": round(pos_count / total * 100, 1),
            "negative_pct": round(neg_count / total * 100, 1),
            "neutral_pct": round(100 - (pos_count + neg_count) / total * 100, 1),
        },
    }


def _empty_result() -> dict:
    return {
        "total_danmaku": 0,
        "density_curve": [],
        "peak_moments": [],
        "hot_keywords": [],
        "sentiment": {"positive_pct": 0, "negative_pct": 0, "neutral_pct": 100},
    }
