"""
⚗️ Alembic — 数据分析页面

播放量 / 互动率 / 弹幕 / 评论 / 用户画像。
"""
import streamlit as st

st.title("📊 数据分析")

last_id = st.session_state.get("last_video_id")
if not last_id:
    st.info("👈 请先在「视频摄入」页面处理一个视频")
    st.stop()

# ── 数据采集 ──
st.markdown("### 视频统计")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("播放量", "--")
with col2:
    st.metric("互动率", "--")
with col3:
    st.metric("弹幕数", "--")
with col4:
    st.metric("评论数", "--")

# ── 弹幕分析 ──
st.divider()
st.markdown("### 💬 弹幕分析")

tab1, tab2, tab3 = st.tabs(["密度曲线", "高频词", "峰值时刻"])

with tab1:
    st.info("弹幕密度曲线将在数据加载后显示")
with tab2:
    st.info("高频弹幕词将在分析后显示")
with tab3:
    st.info("精彩片段峰值时刻")

# ── 评论分析 ──
st.divider()
st.markdown("### 📝 评论分析")

st.info("评论分析将在数据加载后显示")

# ── 利益冲突标记 ──
st.divider()
st.markdown("### ⚠️ 利益冲突检测")
st.caption("自动检测评论区中的导流 / 卖课信号")
st.checkbox("✅ 未检测到卖课信号", disabled=True)
