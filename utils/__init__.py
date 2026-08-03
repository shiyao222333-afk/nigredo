"""
⚗️ Nigredo — Cookie 自动读取
"""
import subprocess
import sys
from pathlib import Path


def extract_cookies_from_edge() -> str:
    """尝试从 Edge 浏览器自动提取 B站 cookies"""
    try:
        # yt-dlp 内置浏览器 cookie 提取
        result = subprocess.run(
            ["yt-dlp", "--cookies-from-browser", "edge",
             "--print", "cookies"],
            capture_output=True, text=True, timeout=30,
            env={"HOME": str(Path.home())},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            return parse_ytdlp_cookie_header(result.stdout.strip())
    except Exception:
        pass
    return ""


def extract_cookies_from_firefox() -> str:
    """尝试从 Firefox 提取"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--cookies-from-browser", "firefox",
             "--print", "cookies"],
            capture_output=True, text=True, timeout=30,
            env={"HOME": str(Path.home())},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0 and result.stdout.strip():
            return parse_ytdlp_cookie_header(result.stdout.strip())
    except Exception:
        pass
    return ""


def parse_ytdlp_cookie_header(raw: str) -> str:
    """解析 yt-dlp 输出的 cookie 格式"""
    cookies = {}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                name, value = parts[5], parts[6]
                cookies[name] = value
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def auto_detect_cookie() -> str:
    """自动检测并返回可用 cookie"""
    cookie = extract_cookies_from_edge()
    if cookie:
        return cookie
    cookie = extract_cookies_from_firefox()
    if cookie:
        return cookie
    return ""
