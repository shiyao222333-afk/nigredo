"""
⚗️ Nigredo — 视频摄入页面

粘贴视频链接 → 队列处理 → 进度反馈。
"""
import streamlit as st
from config import BILIBILI_COOKIE, BILIBILI_BROWSER


@st.cache_resource
def get_download_manager():
    """复用同一个 DownloadManager 实例（缓存/适配器只初始化一次）"""
    from core.downloader import DownloadManager
    return DownloadManager()


# 界面配置（「引擎配置」页写入 session_state；这里读取并兜底默认值）
if "bili_cookie_input" not in st.session_state:
    st.session_state.bili_cookie_input = BILIBILI_COOKIE
if "bili_browser_input" not in st.session_state:
    st.session_state.bili_browser_input = BILIBILI_BROWSER


st.title("📥 视频摄入")

st.markdown("### 粘贴视频链接")

# 当前 B站 Cookie 来源提示 + 一键打开 B站
col_link, col_status = st.columns([1, 2])
with col_link:
    st.link_button("🔗 打开 B站", "https://www.bilibili.com", use_container_width=True)
with col_status:
    if st.session_state.bili_cookie_input:
        st.caption("🔐 当前：使用手动填写的 Cookie")
    else:
        st.caption(f"🔓 当前：自动读取浏览器（{st.session_state.bili_browser_input}）的登录态")

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
            dm = get_download_manager()
            result = dm.process(
                url,
                cookie=st.session_state.bili_cookie_input,
                browser=st.session_state.bili_browser_input,
            )

        if result.get("status") == "cached":
            st.success(f"♻️ 视频已缓存 (BV: {result['video_id']})")
            st.info(f"标题: {result.get('info', {}).get('title', '未知')}")
        elif result.get("status") == "done":
            st.success(f"✅ 蒸馏完成！")
            
            # 显示视频信息
            info = result.get("info", {})
            st.markdown(f"**标题**：{info.get('title', '')}")
            st.markdown(f"**作者**：{info.get('author', '')}")
            st.markdown(f"**时长**：{info.get('duration_seconds', 0)} 秒")
            
            # 显示字幕
            subtitle = result.get("subtitle")
            if subtitle and subtitle.get("full_text"):
                st.markdown("### 📜 字幕内容")
                st.text_area(
                    "字幕文本",
                    subtitle["full_text"],
                    height=300,
                    key="subtitle_display"
                )
                st.caption(f"字幕来源：{subtitle.get('source', 'unknown')}")
            else:
                st.warning("⚠️ 未生成字幕（CC 字幕不可用，Whisper ASR 也失败）")
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
