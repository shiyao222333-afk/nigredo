"""
⚗️ Nigredo — 字幕提取与 ASR

策略：
1. 优先使用平台 CC 字幕（快速、免费）
2. CC 不可用时回退到 faster-whisper（慢、吃资源、但兜底）

Whisper 模型下载说明：
- 默认走 HuggingFace。某些网络环境（受限代理）会掐断到 huggingface.co 的 TLS 连接，
  可在 .env 设 HF_ENDPOINT=https://hf-mirror.com 改用国内镜像绕过（已默认开启）。
- huggingface_hub 的并发下载器(thread_map) 在 Python3.14 下会段错误，故这里改用
  单文件顺序下载（hf_hub_download），更稳。
- 模型下载到 data/models/faster-whisper-{size}，faster-whisper 直接加载本地目录，
  不走 huggingface_hub 缓存结构，避免二次下载。
"""
import os
from pathlib import Path
import inspect
import logging
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, HF_TOKEN

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# 模型只加载一次，避免每次调用都重新初始化（medium/large 加载很慢）
_whisper_model = None
_whisper_model_path = None


def whisper_model_repo(model_size: str = None) -> str:
    """返回 faster-whisper 模型在 HuggingFace 上的仓库名"""
    return f"Systran/faster-whisper-{model_size or WHISPER_MODEL_SIZE}"


def _model_local_dir(model_size: str) -> Path:
    """模型本地目录：data/models/faster-whisper-{size}"""
    return PROJECT_ROOT / "data" / "models" / f"faster-whisper-{model_size}"


def is_model_cached(model_size: str = None) -> bool:
    """检查模型是否已下载到本地目录（避免重复下载）"""
    size = model_size or WHISPER_MODEL_SIZE
    return (_model_local_dir(size) / "model.bin").exists()


def download_whisper_model(model_size: str = None, token: str = None,
                           progress_cb=None) -> str:
    """
    单文件顺序下载 Whisper 模型到 data/models/faster-whisper-{size}。

    不用 huggingface_hub 的 snapshot_download（其 thread_map 并发在 Py3.14 段错误），
    改用 hf_hub_download 逐个文件下载，更稳。
    返回本地目录路径，faster-whisper 可直接加载该目录。
    progress_cb(done_bytes, total_bytes) 可选，用于界面进度条（按单文件进度转发）。
    """
    from huggingface_hub import list_repo_files, hf_hub_download
    size = model_size or WHISPER_MODEL_SIZE
    repo = whisper_model_repo(size)
    use_token = token if token is not None else HF_TOKEN
    local = _model_local_dir(size)
    local.mkdir(parents=True, exist_ok=True)

    logger.info(f"开始下载 Whisper 模型: {repo} -> {local}")
    files = list_repo_files(repo, repo_type="model")
    # 进度回调兼容：旧版 huggingface_hub 的 hf_hub_download 无 progress_callback 参数
    _supports_cb = "progress_callback" in inspect.signature(hf_hub_download).parameters
    for fname in files:
        dl_kwargs = dict(
            repo_id=repo,
            filename=fname,
            local_dir=str(local),
            token=use_token or None,
        )
        if progress_cb is not None and _supports_cb:
            dl_kwargs["progress_callback"] = _wrap_progress(progress_cb, fname)
        hf_hub_download(**dl_kwargs)
    logger.info(f"Whisper 模型下载完成: {local}")
    return str(local)


def _wrap_progress(ui_cb, fname):
    """把 hf_hub_download 的 ProgressInfo 转发给 UI 回调（单文件粒度）"""
    def _cb(progress):
        if ui_cb is not None and getattr(progress, "total", 0):
            ui_cb(progress.completed, progress.total)
    return _cb


class NotAudioError(ValueError):
    """传给 Whisper 的不是合法音频文件（如误传字幕 .srt / .txt）。"""


def _looks_like_audio(path: str) -> bool:
    """快速判定文件是否为合法音频容器，避免把字幕/文本误当音频喂给 Whisper。

    优先看魔法字节（WAV / MP3(ID3) / OGG·Opus / FLAC / M4A·MP4），
    兜底用 soundfile（faster-whisper 已依赖）试读头识别未知容器。
    """
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return False
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return True
    if head[:4] in (b"ID3", b"OggS", b"fLaC"):
        return True
    if head[4:8] == b"ftyp":
        return True
    try:
        import soundfile as sf
        with sf.SoundFile(path) as f:
            _ = f.frames
        return True
    except Exception:
        return False


def transcribe_with_whisper(audio_path: str, language: str = "zh") -> list[dict]:
    """
    使用 faster-whisper 进行 ASR。
    返回: [{"start": float, "end": float, "text": str}, ...]
    """
    if not _looks_like_audio(audio_path):
        raise NotAudioError(
            f"传入 Whisper 的不是合法音频文件: {audio_path}\n"
            f"很可能缓存目录里同前缀的字幕/文本副产品被误当音频。"
            f"下载器应按扩展名取音频（见 bilibili.download_audio）。"
        )
    global _whisper_model, _whisper_model_path
    size = WHISPER_MODEL_SIZE
    if not is_model_cached(size):
        local = download_whisper_model(size)
    else:
        local = str(_model_local_dir(size))

    if _whisper_model is None or _whisper_model_path != local:
        from faster_whisper import WhisperModel
        logger.info(f"加载 Whisper 模型: {local} / {WHISPER_DEVICE}")
        _whisper_model = WhisperModel(
            local,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        _whisper_model_path = local

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
