"""
⚗️ Alembic — 视频摄入页面

粘贴视频链接 → 队列处理 → 进度反馈。
"""
import streamlit as st

st.title("📥 视频摄入")

st.markdown("### 粘贴视频链接")

url = st.text_input(
    "支持 B站视频链接（未来：YouTube / 小红书）",
    placeholder="例如: https://www.bilibili.com/video/BV1xx411c7mD",
    key="url_input",
)

col1, col2 = st.columns([1, 3])
with col1:
    submit = st.button("🚀 开始蒸馏", type="primary", use_container_width=True, disabled=not url)

if submit and url:
    st.info("🧪 蒸馏管道启动中...")

    try:
        with st.spinner("🔍 解析链接..."):
            from core.downloader import DownloadManager
            dm = DownloadManager()
            result = dm.process(url)

        if result.get("status") == "cached":
            st.success(f"♻️ 视频已缓存 (BV: {result['video_id']})")
            st.info(f"标题: {result.get('info', {}).get('title', '未知')}")
        elif result.get("status") == "done":
            st.success(f"✅ 蒸馏完成！")
            st.json(result, expanded=False)
        else:
            st.warning(f"⚠️ 状态: {result.get('status')}")

        # 存储到 session
        st.session_state.last_result = result
        st.session_state.last_video_id = result.get("video_id")

    except Exception as e:
        st.error(f"❌ 蒸馏失败: {e}")

# 历史记录
if st.session_state.get("last_video_id"):
    st.divider()
    st.caption(f"📌 上一次处理: {st.session_state.last_video_id}")
