"""
⚗️ Nigredo — 配置页面
"""
import streamlit as st
import threading
from config import (BILIBILI_COOKIE, BILIBILI_BROWSER, save_to_env,
                   WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, WHISPER_MODEL_SIZE, HF_TOKEN)

st.title("⚙️ 引擎配置")

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔗 LLM 配置", "🎤 Whisper 配置", "📡 熔知联动", "📺 B站配置"]
)

with tab1:
    st.markdown("### LLM API 配置")
    st.text_input("Base URL", value="https://api.deepseek.com/v1", key="llm_base_url")
    st.text_input("API Key", type="password", key="llm_api_key")
    st.text_input("Model", value="deepseek-chat", key="llm_model")

with tab2:
    st.markdown("### Whisper ASR 配置")

    # GPU 状态提示
    if WHISPER_DEVICE == "cuda":
        st.success(f"🎮 检测到显卡，已启用 GPU 加速（精度：{WHISPER_COMPUTE_TYPE}）")
    else:
        st.warning("⚠️ 未检测到可用显卡，将使用 CPU（转录较慢）。如需加速请确认 CUDA 驱动已安装。")

    st.info(f"当前模型：**{WHISPER_MODEL_SIZE}**（约 3GB，中文识别最强）")

    # HuggingFace 令牌（解决匿名下载限速）
    if "hf_token_input" not in st.session_state:
        st.session_state.hf_token_input = HF_TOKEN
    hf_token = st.text_input(
        "HuggingFace 令牌（可选，解决下载限速）",
        value=st.session_state.hf_token_input,
        type="password",
        key="hf_token_input",
        help="匿名下载大模型常被限速导致卡住。去 hf.co 免费注册，在 Settings → "
             "Access Tokens 生成一个『只读』令牌填这里，下载速度会明显提升。",
    )
    if st.button("💾 保存 HF 令牌"):
        save_to_env("HF_TOKEN", hf_token.strip())
        st.success("✅ 已保存，重启程序后也会保留。")

    # 模型预下载（带进度条，避免使用时静默卡住）
    st.markdown("---")
    st.markdown("#### 模型下载")
    from core.subtitle import is_model_cached, download_whisper_model

    holder = st.session_state.get("dl_holder")
    is_downloading = bool(holder and holder.get("status") == "downloading")

    if is_model_cached():
        st.success(f"✅ 模型 {WHISPER_MODEL_SIZE} 已缓存，可直接使用。")
    elif is_downloading:
        st.caption("下载进行中，请勿关闭窗口…")
    else:
        st.caption("首次使用需下载模型（约 3GB）。点下面按钮提前下载，可看到真实进度：")
        if st.button("⬇️ 预下载模型", type="primary", use_container_width=True):
            new_holder = {"done": 0, "total": 0, "status": "downloading", "path": "", "error": ""}
            st.session_state["dl_holder"] = new_holder

            def _run(h):
                def _cb(done, total):
                    h["done"] = done
                    h["total"] = total
                try:
                    local_dir = download_whisper_model(progress_cb=_cb)
                    h["done"] = h["total"]
                    h["status"] = "done"
                    h["path"] = local_dir
                except Exception as e:
                    h["status"] = "error"
                    h["error"] = str(e)

            threading.Thread(target=_run, args=(new_holder,), daemon=True).start()
            st.rerun()

    # 轮询下载状态并刷新进度条（线程在后台跑，这里反复刷新界面）
    if holder and holder.get("status") == "downloading":
        done, total = holder["done"], holder["total"]
        frac = (done / total) if total else 0.0
        st.progress(min(frac, 1.0), text=f"下载中 {done / 1e6:.0f} / {total / 1e6:.0f} MB")
        st.rerun()
    elif holder and holder.get("status") == "done":
        st.progress(1.0, text="下载完成 ✅")
        st.success(f"✅ 模型已下载到：{holder['path']}")
    elif holder and holder.get("status") == "error":
        st.error(f"❌ 下载失败：{holder['error']}")
        st.info("💡 若因限速失败，请在上方填写 HuggingFace 令牌后重试；"
                "或检查网络是否能访问 huggingface.co。")

with tab3:
    st.markdown("### Citrinitas / Qdrant 联动")
    st.text_input("Qdrant URL", value="http://localhost:6333", key="qdrant_url")
    st.text_input("视频文档集合", value="video_docs", key="qdrant_video")
    st.text_input("分析报告集合", value="video_analysis", key="qdrant_analysis")
    st.button("🔗 测试连接")

with tab4:
    st.markdown("### 📺 B站 登录配置")
    st.caption("下载大部分 B站视频需要登录态。两种方式任选其一，无需手动复制也能用。")

    st.link_button("🔗 在浏览器打开 B站并登录", "https://www.bilibili.com", use_container_width=True)

    # 界面配置来源：首次进入时用 .env 的默认值初始化
    if "bili_cookie_input" not in st.session_state:
        st.session_state.bili_cookie_input = BILIBILI_COOKIE
    if "bili_browser_input" not in st.session_state:
        st.session_state.bili_browser_input = BILIBILI_BROWSER

    if st.session_state.bili_browser_input not in ("firefox", "chrome", "edge"):
        st.session_state.bili_browser_input = "firefox"

    browser = st.selectbox(
        "自动读取哪个浏览器的登录 Cookie",
        ["firefox", "chrome", "edge"],
        index=["firefox", "chrome", "edge"].index(st.session_state.bili_browser_input),
        key="bili_browser_input",
        help="程序会尝试自动读取你在该浏览器里已登录的 B站 Cookie，无需手动复制。"
             "你用的是火狐，默认即为 firefox。",
    )

    cookie = st.text_input(
        "或手动粘贴 B站 Cookie（可选，留空则走上面浏览器自动读取）",
        key="bili_cookie_input",
        type="password",
        help="如果浏览器自动读取失败（例如没登录），可在这里手动粘贴。",
    )

    if st.button("💾 保存 B站配置", type="primary"):
        save_to_env("BILIBILI_COOKIE", cookie.strip())
        save_to_env("BILIBILI_BROWSER", browser)
        st.success("✅ 已保存。当前会话立即生效，重启程序后也会保留。")

    # 手动复制 Cookie 的方法（备用）
    with st.expander("❓ 手动复制 Cookie 的方法（浏览器自动读取失败时备用）"):
        st.markdown(
            "1. 点上方「打开 B站」按钮，在浏览器登录 bilibili.com\n"
            "2. 按 **F12** 打开开发者工具 → 切到「网络(Network)」\n"
            "3. 刷新页面，随便点一个请求\n"
            "4. 在「请求标头」里找到 **Cookie:** 那一行，复制整段（含 `SESSDATA=...; bili_jct=...`）\n"
            "5. 粘贴到上方输入框，点「保存」\n\n"
            "⚠️ Cookie 等于你的登录凭证，不要发给任何人、不要截图发群里。"
        )

    # 当前生效状态
    if st.session_state.bili_cookie_input:
        st.info("🔐 生效中：手动填写的 Cookie")
    else:
        st.info(f"🔓 生效中：自动读取浏览器（{st.session_state.bili_browser_input}）的登录态")
