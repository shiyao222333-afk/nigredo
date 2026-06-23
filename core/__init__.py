"""
⚗️ Nigredo — 统一下载层

封装 yt-dlp，支持多平台音频下载。
"""
import subprocess
from pathlib import Path
from config import DEBUG


def download_audio(video_url: str, output_dir: str,
                   cookie: str = "") -> str:
    """
    使用 yt-dlp 下载视频音频。
    返回 WAV 文件路径。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "worstaudio",
        "-x", "--audio-format", "wav",
        "-o", output_template,
        "--no-playlist",
        video_url,
    ]

    if cookie:
        # 使用浏览器 cookie
        cmd.extend(["--cookies-from-browser", "edge"])
    elif DEBUG:
        print("[Nigredo] 未提供 cookie，使用游客模式下载（可能受限）")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp 下载失败: {result.stderr}")

    # 找生成的 WAV 文件
    wav_files = list(output_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError("未找到下载的音频文件")

    # 返回最新的 WAV
    return str(max(wav_files, key=lambda f: f.stat().st_mtime))


def get_video_metadata(video_url: str) -> dict:
    """获取视频元数据（不下载）"""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", video_url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return {}
    try:
        import json
        return json.loads(result.stdout)
    except Exception:
        return {}
