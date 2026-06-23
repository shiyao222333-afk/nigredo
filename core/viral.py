"""
⚗️ Nigredo — 爆款横向分析

对比多个视频，发现模式、规律、矛盾。
"""
from collections import Counter
from core.documenter import generate_viral_analysis


def cross_analyze(videos: list[dict]) -> dict:
    """
    横向对比多个视频。

    输入: videos = [
        {title, author, subtitles, view_count, like_count, ...},
        ...
    ]

    返回:
        - common_patterns: 共同模式
        - differences: 差异点
        - contradictions: 矛盾点（为 Albedo 准备）
        - ranking: 按指标排序
    """
    if not videos:
        return {"error": "没有视频可供分析"}

    # 1. LLM 深度分析
    llm_result = generate_viral_analysis(videos)

    # 2. 统计对比
    titles = [v.get("title", "") for v in videos]
    views = [v.get("view_count", 0) or 0 for v in videos]

    # 3. 标题关键词
    title_words = []
    for title in titles:
        title_words.extend([w for w in title.split() if len(w) > 1])
    title_keywords = Counter(title_words).most_common(10)

    # 4. 最优指标
    best_index = views.index(max(views)) if views else 0

    # 5. 收入差异标注（预留 Albedo 矛盾检测接口）
    contradictions = _detect_income_contradictions(videos)

    return {
        "video_count": len(videos),
        "title_keywords": [{"word": w, "count": c} for w, c in title_keywords],
        "top_viewed": {
            "title": titles[best_index] if titles else "",
            "views": max(views) if views else 0,
        },
        "avg_views": round(sum(views) / len(views)) if views else 0,
        "avg_engagement": round(
            sum(v.get("like_count", 0) or 0 for v in videos) / len(videos)
        ),
        "contradictions": contradictions,
        "llm_analysis": llm_result,
    }


def _detect_income_contradictions(videos: list[dict]) -> list[dict]:
    """
    检测收入/变现相关的矛盾声明。
    这是 Albedo 的输入数据接口。
    """
    income_triggers = ["收入", "赚钱", "月入", "日入", "万", "变现", "副业", "收益"]
    contradictions = []

    for v in videos:
        subtitles = v.get("subtitles", "")
        if any(t in subtitles for t in income_triggers):
            contradictions.append({
                "video_title": v.get("title", ""),
                "author": v.get("author", ""),
                "match": [t for t in income_triggers if t in subtitles][:3],
                # Albedo 接口：crucible.add_claim(text, source_metadata)
                "crucible_hook": True,
            })

    return contradictions
