"""
⚗️ Nigredo — 文档输出页面

字幕查看 + LLM 文档生成 + 预览。
"""
import streamlit as st

st.title("📝 文档输出")

# 检查是否有处理结果
last_id = st.session_state.get("last_video_id")
if not last_id:
    st.info("👈 请先在「视频摄入」页面处理一个视频")
    st.stop()

st.caption(f"当前视频: {last_id}")

# ── 场景选择 ──
scene = st.selectbox(
    "选择输出场景",
    ["📖 学习笔记", "✍️ 脚本模仿", "🔥 爆款分析（单视频预览）"],
    key="doc_scene",
)

tab1, tab2 = st.tabs(["📋 生成文档", "📝 手动编辑"])

with tab1:
    st.caption("字幕文本预览")
    st.text_area(
        "字幕内容",
        value="（处理完成后自动填充）",
        height=200,
        disabled=True,
        key="subtitle_preview",
    )

    if st.button("🤖 生成文档", type="primary"):
        st.info("LLM 处理中...")

        # 模拟结果结构
        st.session_state.generated_doc = {
            "scene": scene,
            "content": "（文档内容将在 LLM 返回后显示）",
            "source": "bilibili",
            "timestamp": "...",
        }

with tab2:
    doc_content = st.session_state.get("generated_doc", {}).get("content", "")
    st.text_area("编辑文档", value=doc_content, height=400, key="doc_edit")
    st.button("💾 保存编辑")
