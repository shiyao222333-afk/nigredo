"""
⚗️ Nigredo — 学习模仿引擎

链接 → 音频 → 字幕 → 文档 → 数据 → 分析
"""
import sys
from pathlib import Path

# 确保 core 等模块可导入
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Nigredo — 学习模仿引擎",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局 CSS ──────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    .stApp h1, .stApp h2, .stApp h3 { color: #58a6ff; }
    .alembic-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .alembic-progress {
        color: #d2a8ff;
    }
</style>
""", unsafe_allow_html=True)

# ── 页面导航 ──────────────────────────────

PAGES = {
    "关于": [
        st.Page("pages/0_📹_关于.py", title="📹 关于 Nigredo"),
    ],
    "核心工作流": [
        st.Page("pages/1_📥_视频摄入.py", title="📥 视频摄入"),
        st.Page("pages/2_📝_文档输出.py", title="📝 文档输出"),
    ],
    "深度分析": [
        st.Page("pages/3_📊_数据分析.py", title="📊 数据分析"),
        st.Page("pages/4_🔥_爆款分析.py", title="🔥 爆款分析"),
    ],
    "配置": [
        st.Page("pages/5_⚙️_引擎配置.py", title="⚙️ 引擎配置"),
    ],
}

pg = st.navigation(PAGES)
pg.run()
