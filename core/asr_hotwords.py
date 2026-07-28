"""
⚗️ Nigredo — ASR 纠错词表（引擎无关，采集层统一纠错点）

在「字幕原文流出前」把已知/可推测的错误写法纠正为正确写法，
压低英文专名音译（够呆 → Godot）等噪声。**只改文字、不动时间轴**。

两类来源：
1. 静态词表（人工维护）：data/asr_hotwords.json，格式 {"错误写法": "正确写法"}。
2. 半自动来源：从视频标题/简介/标签/评论抽取英文专名候选，写入
   data/asr_hotwords_suggestions.json 供人工确认后并入静态词表
   （半自动 = 自动抽候选、人工确认，避免不可控的误改）。

设计原则（对齐用户红线）：
- 不做「评分/数字管控」拦截疑似音译，只做确定的字符串纠正。
- 不向下游（炼真/熔知）增殖新模块——纠错只在采集层发生一次。
- 时间轴（start/end）原样保留，形式轴 G2 保真自检不受影响。
"""
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MAP_PATH = _PROJECT_ROOT / "data" / "asr_hotwords.json"
_SUGGEST_PATH = _PROJECT_ROOT / "data" / "asr_hotwords_suggestions.json"

# 英文停用词（半自动抽取时排除 the/and/of… 这类不是专名的词）
# 注意：ai/ml/api/gpu/cpu/ui/ux/llm/sdk 等是用户领域（AI/游戏）的真实术语，
# 不放入停用词，应作为候选正确词被抽取。
_EN_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "it", "its", "as", "at", "by", "from", "we", "you", "they",
    "he", "she", "i", "me", "us", "them", "his", "her", "their",
    "my", "your", "our", "ui", "ux", "app", "apps", "vs", "com", "www",
    "http", "https", "new", "how", "what", "why", "not", "no", "yes", "ok",
    "old", "top", "best", "free", "pro", "max", "mini", "one", "do", "does",
    "did", "have", "has", "had", "will", "would", "can", "could", "should",
    "get", "got", "use", "using", "like", "just", "follow", "game", "fun",
    "video", "tutorial", "make", "making", "watch", "see", "now", "here",
}

_static_map_cache = None


def load_static_map(path: str = None) -> dict:
    """加载静态纠错词表 {错误写法: 正确写法}。

    缓存机制：无 path 参数时复用进程内缓存（词表不常变，避免每次重读）。
    加载失败则返回空 dict（不影响主流程）。
    """
    global _static_map_cache
    p = Path(path) if path else _DEFAULT_MAP_PATH
    if path is None and _static_map_cache is not None:
        return _static_map_cache
    mp: dict = {}
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                mp = {str(k): str(v) for k, v in raw.items() if k and v}
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 ASR 纠错词表失败(%s): %s", p, e)
    if path is None:
        _static_map_cache = mp
    return mp


def extract_candidates_from_metadata(title: str = "", description: str = "",
                                     tags: list = None,
                                     comments: list = None) -> set:
    """从视频元数据抽取英文专名候选（半自动词表的「正确词」来源）。

    返回集合：连续英文字母/数字、长度>=2、非停用词。用于补全纠错词表的「正确侧」。
    注意：这里只产出「正确写法」——模型会把专名音译成什么中文字无法预判，
    故候选主要作为人工维护词表的提示 / 已正确词的白名单，不直接改字幕。
    """
    parts = [title or "", description or ""]
    parts += [str(t) for t in (tags or [])]
    parts += [str(c) for c in (comments or [])]
    text_blob = " ".join(parts)
    cands: set = set()
    for m in re.findall(r"[A-Za-z][A-Za-z0-9\+#\-\.]{1,}", text_blob):
        w = m.strip()
        wl = w.lower()
        if len(w) < 2 or wl in _EN_STOPWORDS or w.isdigit():
            continue
        cands.add(w)
    return cands


def suggest_from_metadata(title: str = "", description: str = "",
                          tags: list = None, comments: list = None) -> int:
    """半自动：把元数据抽出的英文候选（且在静态词表里不存在的）写入建议文件，
    供人工确认后并入静态词表。返回新增候选数（0 表示无需新增）。

    不自动改字幕——避免不可控误改。文件不存在则创建。
    """
    static = load_static_map()
    cands = extract_candidates_from_metadata(title, description, tags, comments)
    existing_right = {v.lower() for v in static.values()}
    existing_left = {k.lower() for k in static.keys()}
    new = sorted(
        c for c in cands
        if c.lower() not in existing_right and c.lower() not in existing_left
    )
    if not new:
        return 0
    try:
        old = []
        if _SUGGEST_PATH.exists():
            try:
                old = json.loads(_SUGGEST_PATH.read_text(encoding="utf-8")) or []
            except Exception:  # noqa: BLE001
                old = []
        merged = old + new
        # 去重保序
        seen = set()
        merged = [x for x in merged if not (x in seen or seen.add(x))]
        _SUGGEST_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("ASR 半自动候选建议已写入 %s（+%d）", _SUGGEST_PATH, len(new))
        return len(new)
    except Exception as e:  # noqa: BLE001
        logger.warning("ASR 半自动候选建议写入失败(%s): %s", _SUGGEST_PATH, e)
        return 0


def _keep_case(orig: str, repl: str) -> str:
    """尽量保留原词大小写风格：原词全大写→全大写；首字母大写→首字母大写；否则原样。"""
    if orig.isupper():
        return repl.upper()
    if orig and orig[0].isupper() and orig[1:].islower():
        return repl[:1].upper() + repl[1:]
    return repl


def _apply_map(text: str, mapping: dict) -> str:
    """对一段文字应用 {错误: 正确} 映射（按错误串长度降序，避免短串提前覆盖长串）。"""
    if not mapping or not text:
        return text
    for wrong in sorted(mapping.keys(), key=len, reverse=True):
        right = mapping[wrong]
        if not wrong:
            continue
        text = re.sub(
            re.escape(wrong),
            lambda m: _keep_case(m.group(0), right),
            text,
            flags=re.IGNORECASE,
        )
    return text


def correct_segments(segments: list, extra_map: dict = None) -> list:
    """对 ASR 片段列表逐段纠错，保留时间轴。返回新列表（不原地改）。

    segments: [{"start": float, "end": float, "text": str}, ...]
    纠错只作用于每段的 text 字段；start/end 原样保留。
    """
    mapping = dict(load_static_map())
    if extra_map:
        mapping.update({str(k): str(v) for k, v in extra_map.items() if k})
    if not mapping:
        return [dict(s) for s in segments]
    out = []
    for s in segments:
        ns = dict(s)
        t = s.get("text", "")
        if t:
            ns["text"] = _apply_map(t, mapping)
        out.append(ns)
    return out
