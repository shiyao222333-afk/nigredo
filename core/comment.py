"""
⚗️ Alembic — 评论分析

提取观众反馈的富矿。
"""
from collections import Counter


def analyze_comments(comments: list[dict]) -> dict:
    """
    评论分析 → 提取用户反馈信号

    返回:
        - top_comments: 高赞评论
        - consensus_themes: 共识主题
        - questions: 用户提问
        - link_signals: 导流/卖课信号
    """
    if not comments:
        return _empty_result()

    texts = [c["text"] for c in comments if c.get("text")]

    # 1. 高赞评论 Top 10
    top = sorted(comments, key=lambda c: c.get("likes", 0), reverse=True)[:10]

    # 2. 关键词统计
    all_words = []
    for text in texts:
        all_words.extend([w.strip() for w in text.split() if len(w.strip()) > 1])
    keyword_freq = Counter(all_words).most_common(15)

    # 3. 提问检测
    questions = [c for c in top if "?" in c["text"] or "？" in c["text"]]

    # 4. 卖课/导流信号检测
    link_triggers = ["微信", "VX", "vx", "wx", "加我", "私信", "私我",
                     "课程", "课", "报名", "付费", "星球", "群"]
    link_signals = []
    for c in comments:
        for trigger in link_triggers:
            if trigger in c["text"]:
                link_signals.append({"text": c["text"], "trigger": trigger})
                break

    return {
        "total_comments": len(comments),
        "top_comments": [{"text": c["text"][:100], "user": c["user"], "likes": c["likes"]} for c in top],
        "keyword_freq": [{"word": w, "count": c} for w, c in keyword_freq],
        "user_questions": [{"text": q["text"][:100], "user": q["user"]} for q in questions],
        "link_signals": link_signals,
        "link_signal_count": len(link_signals),
        "has_sales_signal": len(link_signals) > 2,
    }


def _empty_result() -> dict:
    return {
        "total_comments": 0,
        "top_comments": [],
        "keyword_freq": [],
        "user_questions": [],
        "link_signals": [],
        "link_signal_count": 0,
        "has_sales_signal": False,
    }
