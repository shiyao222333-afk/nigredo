"""
⚗️ Nigredo — 字幕提取与 ASR

策略：
1. 优先使用平台 CC 字幕（快速、免费）
2. CC 不可用时回退到 faster-whisper（慢、吃资源、但兜底）
"""
import os
from pathlib import Path
import logging
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, HF_TOKEN

logger = logging.getLogger(__name__)

# 模型只加载一次，避免每次调用都重新初始化（medium/large 加载很慢）
_whisper_model = None

# 下载进度回调（由界面设置；snapshot_download 通过自定义 tqdm 触发）
_download_progress_cb = None


class _HfProgressTqdm:
    """把 HuggingFace 的下载进度转发给 Streamlit 进度条。

    huggingface_hub 用 tqdm 显示进度，但不接受 progress_callback 参数。
    这里包一层：每次 update 时把 (已下字节, 总字节) 交给界面回调。
    """
    def __init__(self, *args, **kwargs):
        from huggingface_hub.utils import tqdm as _hf_tqdm
        self._inner = _hf_tqdm(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def update(self, n):
        self._inner.update(n)
        if _download_progress_cb is not None and self._inner.total:
            _download_progress_cb(self._inner.n, self._inner.total)

    def close(self):
        self._inner.close()


def whisper_model_repo(model_size: str = None) -> str:
    """返回 faster-whisper 模型在 HuggingFace 上的仓库名"""
    return f"Systran/faster-whisper-{model_size or WHISPER_MODEL_SIZE}"


def is_model_cached(model_size: str = None) -> bool:
    """检查模型是否已下载到 HF 缓存（避免重复下载）"""
    from huggingface_hub import try_to_load_from_cache
    repo = whisper_model_repo(model_size)
    try:
        path = try_to_load_from_cache(repo, "model.bin", revision="main")
    except Exception:
        return False
    return path is not None and os.path.exists(path)


def download_whisper_model(model_size: str = None, token: str = None,
                           progress_cb=None) -> str:
    """
    预下载 Whisper 模型到 HF 缓存（正确的缓存位置，faster-whisper 会自动复用）。
    progress_cb(done_bytes, total_bytes) 可选，用于界面进度条。
    返回本地缓存目录路径。
    """
    global _download_progress_cb
    from huggingface_hub import snapshot_download
    repo = whisper_model_repo(model_size)
    use_token = token if token is not None else HF_TOKEN
    _download_progress_cb = progress_cb
    try:
        logger.info(f"开始下载 Whisper 模型: {repo}")
        local_dir = snapshot_download(
            repo_id=repo,
            token=use_token or None,
            tqdm_class=_HfProgressTqdm,
        )
    finally:
        _download_progress_cb = None
    return local_dir


def transcribe_with_whisper(audio_path: str, language: str = "zh") -> list[dict]:
    """
    使用 faster-whisper 进行 ASR。
    返回: [{"start": float, "end": float, "text": str}, ...]
    """
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"加载 Whisper 模型: {WHISPER_MODEL_SIZE} / {WHISPER_DEVICE}")
        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    segments_result = []

    segments, info = _whisper_model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    for seg in segments:
        segments_result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    return segments_result


def merge_subtitles(cc_subtitle: list[dict],
                    whisper_segments: list[dict]) -> list[dict]:
    """
    智能合并 CC 字幕和 Whisper 结果。
    当前策略：接受 CC 字幕原样，Whisper 仅用于补充。
    未来可做精确时间轴对齐。
    """
    if cc_subtitle:
        return cc_subtitle
    return whisper_segments


def format_subtitle_text(segments: list[dict]) -> str:
    """将带时间轴的片段转为纯文本"""
    return "\n".join(seg.get("text", "") for seg in segments)


def format_subtitle_srt(segments: list[dict]) -> str:
    """将片段转为 SRT 格式（可选，用于人工校对）"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg.get("start", 0))
        end = _seconds_to_srt_time(seg.get("end", 0))
        text = seg.get("text", "")
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
