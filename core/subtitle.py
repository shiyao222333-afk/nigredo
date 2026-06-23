"""
⚗️ Nigredo — 字幕提取与 ASR

策略：
1. 优先使用平台 CC 字幕（快速、免费）
2. CC 不可用时回退到 faster-whisper（慢、吃资源、但兜底）
"""
from pathlib import Path
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


def transcribe_with_whisper(audio_path: str, language: str = "zh") -> list[dict]:
    """
    使用 faster-whisper 进行 ASR。
    返回: [{"start": float, "end": float, "text": str}, ...]
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )
    segments_result = []
    full_text_parts = []

    segments, info = model.transcribe(
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
        full_text_parts.append(seg.text.strip())

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
