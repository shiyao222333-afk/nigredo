"""
⚗️ Alembic 全局配置文件
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

# === Qdrant ===
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION_VIDEO = os.getenv("QDRANT_COLLECTION_VIDEO", "video_docs")
QDRANT_COLLECTION_ANALYSIS = os.getenv("QDRANT_COLLECTION_ANALYSIS", "video_analysis")

# === Whisper ===
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")  # tiny/base/small/medium/large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu / cuda
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8 / float16

# === 调试 ===
DEBUG = os.getenv("ALEMBIC_DEBUG", "false").lower() == "true"

# 创建必要目录
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
