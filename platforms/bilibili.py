"""
⚗️ Nigredo — B站 平台适配器
"""
import re
import os
import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

from . import VideoInfo, SubtitleResult

logger = logging.getLogger(__name__)

# BV 号正则
BV_PATTERN = re.compile(r"(BV[a-zA-Z0-9]{10})")
# 短链接匹配
B23_PATTERN = re.compile(r"(b23\.tv/[a-zA-Z0-9]+)")


class BilibiliPlatform:
    """B站平台适配器"""

    PLATFORM = "bilibili"

    def __init__(self, cookie: str = "", browser: str = "firefox"):
        self.cookie = cookie
        self.browser = browser
        self._api = None  # 惰性加载 bilibili-api

    # ── URL 解析 ──────────────────────────

    def parse_url(self, url: str) -> Optional[str]:
        """从 URL 中提取 BV 号（支持 BV 直链与 b23.tv 短链）"""
        m = BV_PATTERN.search(url)
        if m:
            return m.group(1)
        # 短链接 b23.tv：跟随 302 重定向拿到真实地址再提取 BV 号
        if B23_PATTERN.search(url):
            real_url = self._resolve_b23_url(url)
            if real_url:
                m = BV_PATTERN.search(real_url)
                if m:
                    return m.group(1)
        return None

    def _resolve_b23_url(self, url: str) -> Optional[str]:
        """跟随 b23.tv 短链 302 重定向，返回真实视频 URL（失败时返回 None）"""
        import requests

        try:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            return resp.url
        except Exception as e:
            logger.warning(f"b23.tv 短链解析失败: {e}")
            return None

    # ── 视频信息 ──────────────────────────

    def get_video_info(self, video_id: str) -> VideoInfo:
        """通过 bilibili-api-python 获取视频元数据"""
        self._ensure_api()
        try:
            video = self._api.video.Video(bvid=video_id, credential=self._credential)
            info = self._run_async(video.get_info())
        except Exception as e:
            logger.warning(f"bilibili-api 获取信息失败，回退 yt-dlp: {e}")
            # API 不工作时用 yt-dlp 兜底
            return self._get_info_via_ytdlp(video_id)

        stat = info.get("stat", {})
        owner = info.get("owner", {})
        return VideoInfo(
            platform="bilibili",
            video_id=video_id,
            title=info.get("title", ""),
            description=info.get("desc", ""),
            author=owner.get("name", ""),
            author_id=str(owner.get("mid", "")),
            duration_seconds=info.get("duration", 0),
            cover_url=info.get("pic", ""),
            published_at=self._ts_to_iso(info.get("pubdate", 0)),
            url=f"https://www.bilibili.com/video/{video_id}",
            view_count=stat.get("view", 0),
            like_count=stat.get("like", 0),
            coin_count=stat.get("coin", 0),
            favorite_count=stat.get("favorite", 0),
            share_count=stat.get("share", 0),
            comment_count=stat.get("reply", 0),
            danmaku_count=stat.get("danmaku", 0),
            has_cc_subtitle=bool(info.get("subtitle", {}).get("list", [])),
        )

    def _get_info_via_ytdlp(self, video_id: str) -> VideoInfo:
        """yt-dlp 兜底获取信息"""
        import sys
        url = f"https://www.bilibili.com/video/{video_id}"
        cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-playlist", url]
        cookie_args, cookie_file = self._resolve_cookie()
        cmd.extend(cookie_args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"yt-dlp 兜底获取信息失败: {result.stderr}")
                raise RuntimeError(result.stderr)
            data = json.loads(result.stdout)
            return VideoInfo(
                platform="bilibili",
                video_id=video_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                author=data.get("uploader", ""),
                author_id=data.get("uploader_id", ""),
                duration_seconds=int(data.get("duration", 0)),
                cover_url=data.get("thumbnail", ""),
                published_at=data.get("upload_date", ""),
                url=url,
                view_count=data.get("view_count", 0),
                like_count=data.get("like_count", 0),
                comment_count=data.get("comment_count", 0),
            )
        except Exception as e:
            logger.warning(f"yt-dlp 兜底获取信息失败: {e}")
            return VideoInfo(
                platform="bilibili",
                video_id=video_id,
                title="获取失败",
                description="",
                author="",
                author_id="",
                duration_seconds=0,
                cover_url="",
                published_at="",
                url=f"https://www.bilibili.com/video/{video_id}",
            )
        finally:
            if cookie_file:
                try:
                    Path(cookie_file).unlink()
                except OSError:
                    pass

    # ── 下载音频 ──────────────────────────

    def download_audio(self, video_id: str, output_dir: str) -> str:
        """使用 yt-dlp 下载音频"""
        import sys
        url = f"https://www.bilibili.com/video/{video_id}"
        output_path = Path(output_dir) / f"{video_id}"
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "worstaudio",       # 最小音频（够用）
            "-x", "--audio-format", "wav",
            "-o", f"{output_path}.%(ext)s",
            "--no-playlist",
            url,
        ]
        cookie_args, cookie_file = self._resolve_cookie()
        cmd.extend(cookie_args)
        try:
            subprocess.run(cmd, check=True, timeout=120, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip() or (e.stdout or "").strip() or "（yt-dlp 无输出）"
            logger.error(f"yt-dlp 下载失败: {stderr}")
            # B站 412 几乎都是缺少登录 Cookie（反爬机制）
            hint = ""
            if "412" in stderr or "Precondition Failed" in stderr:
                if self.cookie:
                    hint = ("\n💡 B站返回 412：当前 .env 里的 BILIBILI_COOKIE 可能已失效，"
                            "请重新从浏览器复制最新 Cookie 后重启程序。")
                else:
                    hint = (f"\n💡 B站返回 412：自动读取浏览器({self.browser})的 B站 Cookie 失败。"
                            "请确认：① 已在该浏览器登录 bilibili.com；"
                            "② 浏览器处于登录状态（未退出）。\n"
                            "若仍失败，可在 .env 手动设置 BILIBILI_COOKIE=SESSDATA=xxx; bili_jct=yyy 后重启。")
            raise RuntimeError(f"yt-dlp 下载失败:\n{stderr}{hint}") from e
        finally:
            if cookie_file:
                try:
                    Path(cookie_file).unlink()
                except OSError:
                    pass
        # 找到实际下载的文件（扩展名可能因转码而变化）
        matches = sorted(Path(output_dir).glob(f"{video_id}.*"))
        if not matches:
            raise FileNotFoundError(f"yt-dlp 未生成音频文件: {output_path}.*")
        return str(matches[0])

    # ── 字幕提取 ──────────────────────────

    def extract_subtitle(self, video_id: str) -> SubtitleResult:
        """优先提取 B站 CC 字幕"""
        self._ensure_api()
        try:
            video = self._api.video.Video(bvid=video_id, credential=self._credential)
            info = self._run_async(video.get_info())
            subtitle_list = info.get("subtitle", {}).get("list", [])
            if not subtitle_list:
                return SubtitleResult(source="cc_not_found", language="", full_text="")

            # 取第一个中文字幕
            sub_url = subtitle_list[0]["subtitle_url"]
            if not sub_url.startswith("http"):
                sub_url = "https:" + sub_url

            import requests
            resp = requests.get(sub_url, timeout=10)
            data = resp.json()
            segments = []
            full_text_parts = []
            for item in data.get("body", []):
                text = item.get("content", "")
                segments.append({
                    "start": item.get("from", 0),
                    "end": item.get("to", 0),
                    "text": text,
                })
                full_text_parts.append(text)

            return SubtitleResult(
                source="cc",
                language="zh",
                segments=segments,
                full_text="\n".join(full_text_parts),
            )
        except Exception as e:
            logger.warning(f"CC 字幕提取失败: {e}")
            return SubtitleResult(source="error", language="", full_text="")

    # ── 弹幕 ─────────────────────────────

    def get_danmaku(self, video_id: str) -> list[dict]:
        """获取视频弹幕列表"""
        self._ensure_api()
        try:
            video = self._api.video.Video(bvid=video_id, credential=self._credential)
            danmakus = self._run_async(video.get_danmakus(page_index=0))
            return [
                {
                    "text": d.text,
                    "time": d.dm_time,        # 弹幕出现时间(秒)
                    "send_time": d.send_time,  # 发送时间戳
                    "mode": d.mode,            # 1-滚动 4-底部 5-顶部
                    "color": d.color,
                }
                for d in danmakus
            ]
        except Exception as e:
            logger.warning(f"弹幕获取失败: {e}")
            return []

    # ── 评论 ─────────────────────────────

    def get_comments(self, video_id: str, max_count: int = 200) -> list[dict]:
        """获取视频评论"""
        self._ensure_api()
        comments = []
        try:
            video = self._api.video.Video(bvid=video_id, credential=self._credential)
            page = 1
            while len(comments) < max_count:
                resp = self._run_async(video.get_comments(page_index=page))
                if not resp.get("replies"):
                    break
                for r in resp["replies"]:
                    comments.append({
                        "text": r.get("content", {}).get("message", ""),
                        "user": r.get("member", {}).get("uname", ""),
                        "likes": r.get("like", 0),
                        "time": r.get("ctime", 0),
                    })
                    if len(comments) >= max_count:
                        break
                page += 1
        except Exception as e:
            logger.warning(f"评论获取失败（已返回部分结果）: {e}")
        return comments

    # ── 辅助 ─────────────────────────────

    def _ensure_api(self):
        if self._api is None:
            import bilibili_api
            self._credential = None
            if self.cookie:
                self._credential = bilibili_api.credential.Credential(
                    sessdata=self._parse_sessdata()
                )
            self._api = bilibili_api

    def _run_async(self, coroutine):
        """
        运行异步方法（同步包装）

        为什么不用 asyncio.run()？
        → Streamlit 在部分场景下已有自己的事件循环在运行，
          asyncio.run() 会报错 "cannot be called from a running event loop"

        策略：
        - 若当前没有运行中的循环：直接在本线程新建循环执行（最快）
        - 若已有循环在运行：丢到独立线程里跑新循环，避免冲突
        """
        import asyncio
        import concurrent.futures

        def _run_in_new_loop(coro):
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 没有运行中的循环，直接跑
            return _run_in_new_loop(coroutine)

        # 已有运行中的循环，用新线程隔离
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_run_in_new_loop, coroutine).result()

    def _write_cookie_file(self, cookie_str: str) -> Optional[str]:
        """
        将 HTTP cookie 字符串转为 Netscape 格式临时文件，供 yt-dlp 使用。

        yt-dlp 的 --cookies 需要 Netscape 格式（domain<TAB>flag<TAB>path...），
        而 .env 里存的是 HTTP header 格式（SESSDATA=xxx; bili_jct=yyy），
        两者不兼容，必须转换。
        """
        try:
            fd, path = tempfile.mkstemp(suffix=".txt", prefix="nigredo_cookie_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for item in cookie_str.split(";"):
                    item = item.strip()
                    if not item or "=" not in item:
                        continue
                    key, _, value = item.partition("=")
                    # 格式: domain | flag | path | secure | expiration | name | value
                    f.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{key}\t{value}\n")
            return path
        except Exception as e:
            logger.warning(f"写入 cookie 文件失败，yt-dlp 将匿名下载: {e}")
            return None

    def _resolve_cookie(self) -> tuple[list, Optional[str]]:
        """
        返回 yt-dlp 的 cookie 参数，以及需要清理的临时文件路径（若有）。

        优先级：
        1. .env 的 BILIBILI_COOKIE（手动覆盖，最高优先级）
        2. 自动读取浏览器里已登录的 B站 Cookie（--cookies-from-browser）
        3. 都不行 → 返回空列表（匿名，多数视频会 412）

        返回: (cmd_args, temp_file_path_or_None)
        """
        if self.cookie:
            cookie_file = self._write_cookie_file(self.cookie)
            if cookie_file:
                return ["--cookies", cookie_file], cookie_file
        if self.browser:
            return ["--cookies-from-browser", self.browser], None
        return [], None

    def _parse_sessdata(self) -> str:
        """从 cookie 字符串中提取 SESSDATA"""
        for item in self.cookie.split(";"):
            item = item.strip()
            if item.startswith("SESSDATA="):
                return item.split("=", 1)[1]
        return ""

    @staticmethod
    def _ts_to_iso(ts: int) -> str:
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=8))
        return datetime.fromtimestamp(ts, tz=tz).isoformat()
