"""
⚗️ Nigredo — 配置页面
"""
import streamlit as st

st.title("⚙️ 引擎配置")

tab1, tab2, tab3 = st.tabs(["🔗 LLM 配置", "🎤 Whisper 配置", "📡 熔知联动"])

with tab1:
    st.markdown("### LLM API 配置")
    st.text_input("Base URL", value="https://api.deepseek.com/v1", key="llm_base_url")
    st.text_input("API Key", type="password", key="llm_api_key")
    st.text_input("Model", value="deepseek-chat", key="llm_model")

with tab2:
    st.markdown("### Whisper ASR 配置")
    st.selectbox("模型大小", ["tiny", "base", "small", "medium", "large-v3"], index=3, key="whisper_size")
    st.selectbox("推理设备", ["cpu", "cuda"], key="whisper_device")
    st.selectbox("计算精度", ["int8", "float16"], key="whisper_compute")

with tab3:
    st.markdown("### Citrinitas / Qdrant 联动")
    st.text_input("Qdrant URL", value="http://localhost:6333", key="qdrant_url")
    st.text_input("视频文档集合", value="video_docs", key="qdrant_video")
    st.text_input("分析报告集合", value="video_analysis", key="qdrant_analysis")
    st.button("🔗 测试连接")
