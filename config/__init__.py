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
CACHE_AUDIO_DIR = CACHE_DIR / "audio"      # 下载音频（ASR 输入），与字幕副产品物理隔离
CACHE_OUTPUT_DIR = CACHE_DIR / "outputs"   # 字幕等生成物（.txt / .srt）
REPORTS_DIR = DATA_DIR / "reports"

# === 中转输出（文件夹契约） ===
# 馏析把处理结果写成「中转①」（{bv}.md，带 YAML frontmatter）到 OUTPUT_DIR；
# 炼真(Albedo) 的监控目录默认也指向这里。三器各自可改（env 覆盖）。
OUTPUT_DIR = Path(os.getenv("NIGREDO_OUTPUT_DIR", r"D:\opus-magnum\front_half\transit\nigredo_out"))
# 人审闸门：true 时 中转① 先写进 OUTPUT_DIR/review_pending/，需晋级才进入下游；默认关（调试优先）
REQUIRE_HUMAN_REVIEW = os.getenv("NIGREDO_REQUIRE_HUMAN_REVIEW", "false").lower() == "true"

# === LLM ===
LLM_BASE_URL = os.getenv("NIGREDO_LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("NIGREDO_LLM_API_KEY", "")
LLM_MODEL = os.getenv("NIGREDO_LLM_MODEL", "deepseek-chat")

# === B站 ===
BILIBILI_COOKIE = os.getenv("BILIBILI_COOKIE", "")
# Cookie 来源：默认自动读取浏览器里已登录的 B站 Cookie（firefox / chrome / edge）
# 仅当 BILIBILI_COOKIE 为空时才用浏览器；两者都为空则匿名（多数视频会 412）
# 默认 firefox：因使用者使用火狐浏览器
BILIBILI_BROWSER = os.getenv("BILIBILI_BROWSER", "firefox")

# === Whisper ===
# ⚠️ 本机 ctranslate2 的 CUDA 路径在 7/18 系统更新后偶发段错误（0xC0000005 @ ucrtbase），
# 且段错误无法被 try/except 捕获会直接杀进程。原代码在 import 时执行
# `import ctranslate2` + `get_cuda_device_count()` 触发崩溃，导致整个 Nigredo 无法 import。
# 故**不在 import 时探测 CUDA**，默认走 CPU；真正需要 GPU 时由 whisper 后端按需调用
# probe_cuda()（失败/崩溃则回退 CPU）。当前默认 ASR_BACKEND=funasr 走 CPU 即可用。
_CUDA_AVAILABLE = False


def probe_cuda() -> bool:
    """按需探测 CUDA（可能崩，调用方需自己包在子进程/容错里）。返回是否有可用显卡。"""
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


if _CUDA_AVAILABLE:
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
else:
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")  # tiny/base/small/medium/large-v3
# HuggingFace 访问令牌（免费）：匿名下载大模型常被限速而卡住，填令牌可显著提速
HF_TOKEN = os.getenv("HF_TOKEN", "")
# HuggingFace 镜像源：默认走国内镜像 hf-mirror.com，绕过受限网络/免墙，下载更稳更快。
# 用户若想用官方源，在 .env 设 HF_ENDPOINT=https://huggingface.co 覆盖即可。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# === ASR 后端选择（模块化语音识别） ===
# 同一套调用可切换不同语音识别引擎，切换只改这里，不动业务代码。
# 可选值：whisper（faster-whisper / ctranslate2，原兜底引擎）
#        funasr（阿里 FunASR SenseVoiceSmall，中文更准，MIT）
#        fireredasr（小红书 FireRedASR，中文最强，预留未实现）
# 各引擎依赖与硬件要求不同：whisper 依赖 ctranslate2（CUDA 部分本机崩，暂不可用）；
# funasr 依赖 PyTorch（本机用 CPU 版可跑，中文更准）。切换只改这里，不动业务代码。
# 注：whisper 的 CUDA 崩是显卡运行时被 7/18 系统更新影响，与系统是否“损坏”无关。
ASR_BACKEND = os.getenv("ASR_BACKEND", "funasr").strip().lower()

# === 调试 ===
DEBUG = os.getenv("NIGREDO_DEBUG", "false").lower() == "true"

# 创建必要目录
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CACHE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_to_env(key: str, value: str) -> None:
    """
    把配置项写回 .env 文件，使修改在程序重启后仍生效。

    用于「引擎配置」页面：用户在界面里改了 Cookie / 浏览器后，
    既要立刻在当前会话生效（通过 session_state），也要持久化到 .env。
    """
    from dotenv import set_key

    env_path = PROJECT_ROOT / ".env"
    set_key(str(env_path), key, value)
