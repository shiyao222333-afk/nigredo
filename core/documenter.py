"""
⚗️ Nigredo — LLM 文档化引擎

将字幕文本转换为结构化文档。
三种场景对应三套 Prompt 模板。
"""
from pathlib import Path
import json

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(template_name: str) -> str:
    """加载 Prompt 模板"""
    path = PROMPTS_DIR / f"{template_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def call_llm(system_prompt: str, user_content: str,
             temperature: float = 0.3) -> str:
    """通用 LLM 调用（OpenAI 兼容）"""
    import requests

    resp = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        },
        timeout=120,
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ═══════════════════════════════════════════
# 场景一：学习笔记
# ═══════════════════════════════════════════

def generate_study_notes(subtitle_text: str, video_title: str = "",
                         video_author: str = "") -> str:
    """将字幕转为结构化学习笔记"""
    system_prompt = load_prompt("study_note")
    user_prompt = f"""# 视频信息
标题: {video_title}
作者: {video_author}

# 字幕文本
{subtitle_text[:12000]}"""
    return call_llm(system_prompt, user_prompt, temperature=0.2)


# ═══════════════════════════════════════════
# 场景二：脚本模仿
# ═══════════════════════════════════════════

def generate_script_analysis(subtitle_text: str, video_title: str = "") -> str:
    """分析视频脚本结构，提取可模仿的元素"""
    system_prompt = load_prompt("script_imitate")
    user_prompt = f"""# 视频标题
{video_title}

# 字幕（含时间轴参考）
{subtitle_text[:12000]}"""
    return call_llm(system_prompt, user_prompt, temperature=0.4)


# ═══════════════════════════════════════════
# 场景三：爆款分析
# ═══════════════════════════════════════════

def generate_viral_analysis(
    videos: list[dict],  # 每个元素: {title, author, subtitles, stats}
) -> str:
    """横向对比多个视频，分析爆款规律"""
    system_prompt = load_prompt("viral_analysis")

    # 构建对比数据
    comparison = []
    for i, v in enumerate(videos, 1):
        comparison.append(f"""
### 视频 {i}: {v.get('title', '')}
- UP主: {v.get('author', '')}
- 播放量: {v.get('view_count', 0):,}
- 互动率: 点赞 {v.get('like_count', 0):,} | 评论 {v.get('comment_count', 0):,} | 弹幕 {v.get('danmaku_count', 0):,}
- 时长: {v.get('duration', 0)}秒

字幕摘要:
{v.get('subtitles', '')[:3000]}
""")

    user_prompt = "\n".join(comparison)
    return call_llm(system_prompt, user_prompt, temperature=0.5)
