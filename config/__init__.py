"""
⚗️ Nigredo 全局配置文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === 路径 ===
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
REPORTS_DIR = DATA_DIR / "reports"

# === LLM ===
LLM_BASE_URL = os.getenv("ALEMBIC_LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("ALEMBIC_LLM_API_KEY", "")
LLM_MODEL = os.getenv("ALEMBIC_LLM_MODEL", "deepseek-chat")

# === B站 ===
BILIBILI_COOKIE = os.getenv("BILIBILI_COOKIE", "")
# Cookie 来源：默认自动读取浏览器里已登录的 B站 Cookie（firefox / chrome / edge）
# 仅当 BILIBILI_COOKIE 为空时才用浏览器；两者都为空则匿名（多数视频会 412）
# 默认 firefox：因使用者使用火狐浏览器
BILIBILI_BROWSER = os.getenv("BILIBILI_BROWSER", "firefox")

# === Qdrant ===
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION_VIDEO = os.getenv("QDRANT_COLLECTION_VIDEO", "video_docs")
QDRANT_COLLECTION_ANALYSIS = os.getenv("QDRANT_COLLECTION_ANALYSIS", "video_analysis")

# === Whisper ===
# GPU 自动探测：检测到 CUDA 设备就用显卡（转录快 5~10 倍），否则退回 CPU
try:
    import ctranslate2
    _CUDA_AVAILABLE = ctranslate2.get_cuda_device_count() > 0
except Exception:
    _CUDA_AVAILABLE = False

if _CUDA_AVAILABLE:
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
else:
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")  # tiny/base/small/medium/large-v3
# HuggingFace 访问令牌（免费）：匿名下载大模型常被限速而卡住，填令牌可显著提速
HF_TOKEN = os.getenv("HF_TOKEN", "")

# === 调试 ===
DEBUG = os.getenv("ALEMBIC_DEBUG", "false").lower() == "true"

# 创建必要目录
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_to_env(key: str, value: str) -> None:
    """
    把配置项写回 .env 文件，使修改在程序重启后仍生效。

    用于「引擎配置」页面：用户在界面里改了 Cookie / 浏览器后，
    既要立刻在当前会话生效（通过 session_state），也要持久化到 .env。
    """
    from dotenv import set_key

    env_path = PROJECT_ROOT / ".env"
    set_key(str(env_path), key, value)
