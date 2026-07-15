"""
⚗️ Nigredo — 下载管理器

统一入口：URL 输入 → 平台识别 → 下载调度。
"""
from pathlib import Path
import re
import json
import logging
from datetime import datetime, timezone, timedelta

from platforms import SubtitleResult
from platforms.bilibili import BilibiliPlatform
from core.subtitle import transcribe_with_whisper, format_subtitle_srt
from utils.cache import VideoCache
from config import CACHE_DIR, BILIBILI_COOKIE, BILIBILI_BROWSER, OUTPUT_DIR, REQUIRE_HUMAN_REVIEW

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════
# URL 路由
# ═══════════════════════════════════════

PLATFORMS = [
    ("bilibili", re.compile(r"(bilibili\.com|b23\.tv|BV[a-zA-Z0-9]{10})")),
]


def detect_platform(url: str) -> str:
    """检测 URL 所属平台"""
    for platform, pattern in PLATFORMS:
        if pattern.search(url):
            return platform
    return "unknown"


# ═══════════════════════════════════════
# 下载工作流
# ═══════════════════════════════════════

class DownloadManager:
    """统一管理下载流程"""

    def __init__(self):
        self.cache = VideoCache(CACHE_DIR)
        self._bilibili = BilibiliPlatform(cookie=BILIBILI_COOKIE, browser=BILIBILI_BROWSER)
        logger.info("DownloadManager 初始化完成")

    def process(self, url: str, cookie: str = None, browser: str = None) -> dict:
        """
        完整处理流程：
        1. URL → 平台识别 → BV号提取
        2. 去重检查
        3. 获取视频元数据
        4. 下载音频
        5. 提取字幕
        6. 返回结果

        参数:
        - cookie / browser：运行时覆盖（来自「引擎配置」页面的 UI 设置）。
          不传则用初始化时的默认值（来自 .env）。
        """
        # 运行时覆盖：让界面里的 Cookie / 浏览器设置即时生效
        if cookie is not None:
            self._bilibili.cookie = cookie
        if browser is not None:
            self._bilibili.browser = browser

        platform = detect_platform(url)
        logger.info(f"检测到平台: {platform}, URL: {url[:50]}...")

        if platform == "bilibili":
            return self._process_bilibili(url)
        else:
            raise NotImplementedError(f"平台 '{platform}' 尚未支持。请在 GitHub issue 中提交需求。")

    def _process_bilibili(self, url: str) -> dict:
        """B站 完整处理（含字幕生成）"""
        bv_id = self._bilibili.parse_url(url)
        if not bv_id:
            raise ValueError(f"无法从 URL 提取 BV 号: {url}")

        # 去重
        if self.cache.is_processed(bv_id):
            metadata = self.cache.get_metadata(bv_id)
            logger.info(f"视频已缓存，跳过: {bv_id}")
            return {
                "status": "cached",
                "video_id": bv_id,
                "info": metadata.get("info", {}),
                "audio_path": metadata.get("audio_path", ""),
                "subtitle": metadata.get("subtitle"),
            }

        # 获取信息
        logger.info(f"获取视频信息: {bv_id}")
        info = self._bilibili.get_video_info(bv_id)

        # 下载音频
        logger.info(f"下载音频: {bv_id}")
        audio_path = self._bilibili.download_audio(bv_id, str(CACHE_DIR))
        logger.info(f"音频下载完成: {audio_path}")

        # 提取字幕（优先 CC，失败则用 Whisper）
        logger.info(f"提取字幕: {bv_id}")
        subtitle = self._extract_subtitle_with_fallback(bv_id, audio_path)
        if subtitle and subtitle.full_text:
            logger.info(f"字幕生成成功，来源: {subtitle.source}")
        else:
            logger.warning(f"字幕生成失败: {bv_id}")

        # 获取弹幕与评论（读取视频互动数据，供下游炼真/数据分析消费）
        logger.info(f"获取弹幕与评论: {bv_id}")
        danmakus = self._bilibili.get_danmaku(bv_id) or []
        comments = self._bilibili.get_comments(bv_id) or []
        pinned_comments = self._bilibili.get_pinned_comments(bv_id) or []
        # 增强：标签 / AI 摘要 / 高光时间点（结构化分析用，直供熔知 keywords）
        tags = self._bilibili.get_tags(bv_id) or []
        ai_conclusion = self._bilibili.get_ai_conclusion(bv_id) or ""
        pbp = self._bilibili.get_pbp(bv_id) or []
        # 播放分析（创作者私有：3秒退出率/平均时长/完播率；非自有视频返回空）
        play_analysis = self._bilibili.get_play_analysis(bv_id) or {}
        # 播放来源分布（创作者私有；按 bvid 递归找 per-video 行，否则退回频道聚合）
        play_source = self._bilibili.get_video_source(bv_id) or {"sources": {}, "scope": "none"}
        # 账号级创作者中心快照（频道级：概览/分区/粉丝/来源；按进程缓存）
        creator_center = self._bilibili.get_creator_center() or {}
        logger.info(
            f"弹幕 {len(danmakus)} 条 / 评论 {len(comments)} 条 / "
            f"置顶 {len(pinned_comments)} 条 / 标签 {len(tags)} 个 / "
            f"播放分析{'有' if play_analysis else '无'} / "
            f"播放来源(scope={play_source.get('scope')}) / "
            f"创作者中心快照{'有' if creator_center else '无'}"
        )

        # 构建结果
        result = {
            "status": "done",
            "video_id": bv_id,
            "info": info.__dict__,
            "audio_path": audio_path,
            "subtitle": subtitle.__dict__ if subtitle else None,
            "danmakus": danmakus,
            "comments": comments,
            "pinned_comments": pinned_comments,
            "tags": tags,
            "ai_conclusion": ai_conclusion,
            "pbp": pbp,
            "play_analysis": play_analysis,
        }
        self.cache.mark_processed(bv_id, result)
        # 字幕落盘：转写结果原本只留内存，刷新即丢。这里额外存文件，
        # 供下游（如 Albedo 炼真）直接「选文件」摄入。
        self._save_subtitle_files(bv_id, subtitle)
        # 中转①落盘（单文件结构化）：写 {bv}.md 供 Albedo 炼真监控消费
        self._save_transit_md(bv_id, info, subtitle, danmakus, comments,
                              tags, ai_conclusion, pbp,
                              pinned_comments=pinned_comments,
                              play_analysis=play_analysis,
                              play_source=play_source,
                              creator_center=creator_center)
        logger.info(f"处理完成: {bv_id}")

        return result

    def _save_subtitle_files(self, bv_id: str, subtitle) -> list:
        """
        字幕结果落盘（新增，2026-07-09）：
        转写/提取出的字幕原本只存在内存，刷新即丢。这里额外存成文件，
        供下游（如 Albedo 炼真）直接「选文件」摄入。
        - {bv_id}.txt : 纯文本（下游最干净的摄入格式）
        - {bv_id}.srt : 带时间轴（供人工校对）
        无内容则返回空列表，不影响主流程。
        """
        if not subtitle or not getattr(subtitle, "full_text", "").strip():
            return []
        cache_dir = self.cache.cache_dir
        saved = []
        try:
            txt_path = cache_dir / f"{bv_id}.txt"
            txt_path.write_text(subtitle.full_text, encoding="utf-8")
            saved.append(str(txt_path))
        except Exception as e:
            logger.warning(f"字幕 .txt 落盘失败: {e}")
        segs = getattr(subtitle, "segments", None)
        if segs:
            try:
                srt_path = cache_dir / f"{bv_id}.srt"
                srt_path.write_text(format_subtitle_srt(segs), encoding="utf-8")
                saved.append(str(srt_path))
            except Exception as e:
                logger.warning(f"字幕 .srt 落盘失败: {e}")
        if saved:
            logger.info(f"字幕已落盘({len(saved)}个): {bv_id}")
        return saved

    def _save_transit_md(self, bv_id: str, info, subtitle,
                         danmakus=None, comments=None,
                         tags=None, ai_conclusion="", pbp=None,
                         pinned_comments=None, play_analysis=None,
                         play_source=None, creator_center=None) -> list:
        """
        中转①落盘（合并单文件，2026-07-15 重写）：
        把「字幕 + 分析元数据 + 弹幕(去重过滤) + 置顶评论 + 高赞评论(去水) +
        标签(=keywords) + AI摘要 + 高光 + 播放分析 + 播放来源 + 统计历史」
        全部合并写成唯一的 {bv_id}.md（YAML frontmatter + 结构化正文），
        供下游 Albedo 炼真 直接整文件读取分析，无需再拼多个 sidecar。
        - REQUIRE_HUMAN_REVIEW=false：写进 OUTPUT_DIR 根（被 Albedo 监控）
        - REQUIRE_HUMAN_REVIEW=true：写进 OUTPUT_DIR/review_pending/
        元信息字段对齐下游 AlbedoInput：title / up_name / video_id / source_url / platform。
        frontmatter 含：计数 / 互动率(赞率·藏率·币率·弹幕密度) / 弹幕去重前后计数 /
        评论统计 / keywords(=视频标签, 直供熔知关键词, 不再另写 tags 避免混淆) /
        播放分析(创作者私有, 需UP主登录) / 播放来源(创作者私有, scope 标注 video/channel) /
        有无 AI 摘要 / 抓取时间 fetched_at。
        正文分节：# 字幕 # AI 摘要 # 高光时间点 # 弹幕(去重过滤后)
                 # 置顶评论 # 高赞评论 # 播放分析 # 播放来源 # 统计历史。
        另：账号级创作者中心快照(频道级)写入同目录 creator_center.md（与单视频无关）。
        """
        if not subtitle or not getattr(subtitle, "full_text", "").strip():
            return []

        def _scalar(v):
            return json.dumps(v, ensure_ascii=False)

        def _stat(attr):
            return getattr(info, attr, None)

        def _rate(part, whole):
            try:
                p = float(part); w = float(whole)
            except (TypeError, ValueError):
                return None
            if not w:
                return None
            return round(p / w * 100, 2)

        def _flow_list(items):
            if not items:
                return "[]"
            return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in items) + "]"

        # —— 计数 ——
        view = _stat("view_count")
        like = _stat("like_count")
        coin = _stat("coin_count")
        favorite = _stat("favorite_count")
        share = _stat("share_count")
        comment = _stat("comment_count")
        danmaku = _stat("danmaku_count")
        duration = _stat("duration")

        # —— 弹幕去重过滤 ——
        clean_dm, dup_n, junk_n = self._clean_danmakus(danmakus)
        dm_before = len(danmakus) if danmakus else 0
        dm_after = len(clean_dm)

        # —— 高赞评论（先去无意义水评，再取点赞排序前 50）——
        clean_comments = self._clean_comments(comments)
        top_comments = clean_comments[:50]

        # —— 置顶评论（与常规评论按 rpid 去重，避免重复）——
        comment_rpids = {c.get("rpid") for c in (comments or []) if c.get("rpid")}
        pinned = [p for p in (pinned_comments or [])
                  if p.get("rpid") not in comment_rpids]

        # —— 关键词（=视频标签，直供熔知关键词；不再另写 tags 字段）——
        tag_list = tags or []
        has_ai = bool(ai_conclusion and str(ai_conclusion).strip())

        # —— 播放分析（创作者私有；非自有视频/未登录则为空）——
        pa = play_analysis or {}
        pa_available = bool(pa)
        pa_three = pa.get("three_sec_retention")
        pa_avg = pa.get("avg_play_duration")
        pa_finish = pa.get("completion_rate")

        # —— 播放来源（创作者私有；scope=video 为本视频，channel 为频道聚合）——
        ps = play_source or {}
        ps_sources = ps.get("sources") or {}
        ps_scope = ps.get("scope") or "none"
        ps_is_video = (ps_scope == "video" and bool(ps_sources))

        # —— 高光时间点 ——
        highlights = []
        for p in (pbp or []):
            t = p.get("time")
            c = (p.get("content") or "").strip()
            if c:
                try:
                    mm = int(float(t) // 60); ss = int(float(t) % 60)
                    highlights.append(f"- [{mm:02d}:{ss:02d}] {c}")
                except (TypeError, ValueError):
                    highlights.append(f"- {c}")

        # —— 互动率 / 密度 ——
        like_rate = _rate(like, view)
        fav_rate = _rate(favorite, view)
        coin_rate = _rate(coin, view)
        dm_density = None
        if duration and view is not None:
            try:
                mins = float(duration) / 60.0
                if mins > 0:
                    dm_density = round(float(danmaku) / mins, 2) if danmaku is not None else None
            except (TypeError, ValueError):
                dm_density = None

        # —— 统计历史（合并历次抓取，不覆盖旧记录）——
        target_dir = OUTPUT_DIR
        if REQUIRE_HUMAN_REVIEW:
            target_dir = OUTPUT_DIR / "review_pending"
        target_dir.mkdir(parents=True, exist_ok=True)
        md_path = target_dir / f"{bv_id}.md"
        fetched_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +08:00")
        old_hist = self._read_history_lines(md_path)
        new_hist_line = (
            f"- {fetched_at} | 播放{view} 赞{like}({like_rate}%) "
            f"币{coin} 藏{favorite} 弹{dm_before}→{dm_after}"
        )
        history_lines = [new_hist_line] + old_hist

        # —— frontmatter ——
        fm = [
            "---",
            f"platform: {_scalar(getattr(info, 'platform', 'bilibili'))}",
            f"video_id: {_scalar(getattr(info, 'video_id', bv_id))}",
            f"title: {_scalar(getattr(info, 'title', ''))}",
            f"up_name: {_scalar(getattr(info, 'author', ''))}",
            f"source_url: {_scalar(getattr(info, 'url', ''))}",
            f"view_count: {_scalar(view)}",
            f"like_count: {_scalar(like)}",
            f"coin_count: {_scalar(coin)}",
            f"favorite_count: {_scalar(favorite)}",
            f"share_count: {_scalar(share)}",
            f"comment_count: {_scalar(comment)}",
            f"danmaku_count: {_scalar(danmaku)}",
            f"fetched_at: {_scalar(fetched_at)}",
            f"like_rate: {_scalar(like_rate)}",
            f"favorite_rate: {_scalar(fav_rate)}",
            f"coin_rate: {_scalar(coin_rate)}",
            f"danmaku_density_per_min: {_scalar(dm_density)}",
            f"danmaku_total_before: {_scalar(dm_before)}",
            f"danmaku_after_dedup_filter: {_scalar(dm_after)}",
            f"danmaku_duplicates_removed: {_scalar(dup_n)}",
            f"danmaku_junk_removed: {_scalar(junk_n)}",
            f"comments_order: {_scalar('like')}",
            f"comments_included: {_scalar(len(top_comments))}",
            f"pinned_comments_included: {_scalar(len(pinned))}",
            f"keywords: {_flow_list(tag_list)}",
            f"has_ai_conclusion: {_scalar(has_ai)}",
            f"play_analysis_available: {_scalar(pa_available)}",
            f"three_sec_retention: {_scalar(pa_three)}",
            f"avg_play_duration: {_scalar(pa_avg)}",
            f"completion_rate: {_scalar(pa_finish)}",
            f"play_source_scope: {_scalar(ps_scope)}",
            f"play_source_available: {_scalar(bool(ps_sources))}",
            "---",
        ]

        # —— 正文 ——
        body = []
        body.append("")
        body.append("# 字幕")
        body.append(subtitle.full_text)
        body.append("")
        if has_ai:
            body.append("# AI 摘要")
            body.append(str(ai_conclusion).strip())
            body.append("")
        if highlights:
            body.append("# 高光时间点")
            body.extend(highlights)
            body.append("")
        if clean_dm:
            body.append("# 弹幕（去重过滤后）")
            for d in clean_dm:
                t = d.get("time", 0) or 0
                txt = (d.get("text") or "").replace("\n", " ").strip()
                if txt:
                    body.append(f"[{t:.0f}s] {txt}")
            body.append("")
        if pinned:
            body.append("# 置顶评论")
            for c in pinned:
                user = c.get("user", "") or ""
                likes = c.get("likes", 0) or 0
                pin_tag = "UP主置顶" if c.get("pin_type") == "upper" else "管理员置顶"
                txt = (c.get("text") or "").replace("\n", " ").strip()
                if txt:
                    body.append(f"[{likes}赞 · {pin_tag}] {user}: {txt}")
            body.append("")
        if top_comments:
            body.append("# 高赞评论")
            for c in top_comments:
                user = c.get("user", "") or ""
                likes = c.get("likes", 0) or 0
                txt = (c.get("text") or "").replace("\n", " ").strip()
                if txt:
                    body.append(f"[{likes}赞] {user}: {txt}")
            body.append("")
        if pa_available:
            body.append("# 播放分析（创作者私有数据·需UP主登录）")
            body.append(f"- 三秒退出率 / 三秒播放率: {pa_three if pa_three is not None else '未提供'}")
            body.append(f"- 平均播放时长: {pa_avg if pa_avg is not None else '未提供'}")
            body.append(f"- 完播率: {pa_finish if pa_finish is not None else '未提供'}")
            body.append("")
        if ps_is_video:
            body.append("# 播放来源（本视频·创作者私有数据·需UP主登录）")
            for name, val in ps_sources.items():
                body.append(f"- {name}: {val}")
            body.append("")
        elif ps_scope == "channel" and ps_sources:
            body.append("# 播放来源（频道级聚合·详见同目录 creator_center.md）")
            body.append(f"- 本视频无独立来源数据；频道聚合共 {len(ps_sources)} 类来源")
            body.append("")
        body.append("# 统计历史")
        body.extend(history_lines)
        body.append("")

        content = "\n".join(fm + body)
        saved = []
        try:
            md_path.write_text(content, encoding="utf-8")
            saved.append(str(md_path))
            logger.info(
                f"中转①单文件已落盘: {md_path} "
                f"(弹幕 {dm_before}→{dm_after}, 评论 {len(top_comments)}, 标签 {len(tag_list)}, AI摘要={has_ai})"
            )
        except Exception as e:
            logger.warning(f"中转① .md 落盘失败: {e}")

        # —— 账号级创作者中心快照（频道级，与单视频无关，单独文件）——
        if creator_center:
            try:
                cc_path = target_dir / "creator_center.md"
                cc_content = self._format_creator_center(creator_center, fetched_at)
                cc_path.write_text(cc_content, encoding="utf-8")
                saved.append(str(cc_path))
                logger.info(f"创作者中心快照已落盘: {cc_path}")
            except Exception as e:
                logger.warning(f"创作者中心快照落盘失败: {e}")
        return saved

    def _format_creator_center(self, data: dict, fetched_at: str) -> str:
        """把账号级创作者中心快照格式化为 markdown（频道级，与单视频无关）。"""
        def _block(title, obj):
            if not obj:
                return f"## {title}\n\n（无数据）\n"
            return f"## {title}\n\n```json\n{json.dumps(obj, ensure_ascii=False, indent=2)}\n```\n"

        parts = [
            "---",
            "type: creator_center_snapshot",
            f"fetched_at: {fetched_at}",
            "scope: channel",
            "note: 账号级创作者数据中心快照，与单个视频无关；每次运行覆盖更新",
            "---",
            "",
            "# 创作者数据中心快照（账号级·需UP主登录）",
            "",
            "> 本文件汇总你账号的频道级数据。每跑一次覆盖更新。",
            ">",
            "> 其中「播放来源分布」为频道聚合；单视频播放来源见各 {bv}.md 的 # 播放来源 章节。",
            "",
            _block("概览（近一周）", data.get("overview")),
            _block("视频分区占比", data.get("survey")),
            _block("粉丝概览", data.get("fan")),
            _block("播放来源分布（频道聚合）", data.get("source")),
        ]
        return "\n".join(parts)

    def _clean_danmakus(self, danmakus):
        """
        弹幕去重 + 去废（2026-07-15）：
        去掉大部分无用弹幕——纯符号 / 超短 / 打卡类水帖 / 重复刷屏。
        返回 (清洗后列表[dict(time,text)], 重复数, 废帖数)。
        """
        if not danmakus:
            return [], 0, 0
        JUNK = {
            "前排", "前排占座", "打卡", "签到", "路过", "三连", "沙发", "板凳",
            "666", "233", "2333", "111", "顶", "赞", "哦", "啊", "马",
            "哈哈", "哈哈哈", "哈哈哈哈", "呵呵", "喵", "蹲", "来了",
        }
        seen = set()
        kept = []
        dup_n = 0
        junk_n = 0
        for d in danmakus:
            t = d.get("time", 0) or 0
            txt = (d.get("text") or "").strip()
            if not txt:
                junk_n += 1
                continue
            key = re.sub(r"\s+", "", txt).lower()
            if len(txt) <= 1:
                junk_n += 1
                continue
            if re.fullmatch(r"[\W_]+", txt):
                junk_n += 1
                continue
            if len(txt) <= 6 and txt in JUNK:
                junk_n += 1
                continue
            if key in seen:
                dup_n += 1
                continue
            seen.add(key)
            kept.append({"time": t, "text": txt})
        return kept, dup_n, junk_n

    def _clean_comments(self, comments):
        """
        高赞评论去水（2026-07-15）：
        在「按点赞排序」之后、截取前 N 之前，剔除无意义的高赞评论——
        纯符号 / 超短 / 低信息水帖（学到了/收藏了/666/前排/催更 等）。
        返回清洗后的列表（保留 time/user/likes/rpid/pinned 等原字段）。
        """
        if not comments:
            return []
        JUNK = {
            "学到了", "收藏了", "马住了", "码住了", "马克", "mark", "mark一下", "记下了",
            "前排", "沙发", "板凳", "三连", "已三连", "三连了", "补个三连",
            "666", "6666", "233", "2333", "哈哈", "哈哈哈", "哈哈哈哈", "笑死",
            "牛", "牛逼", "牛批", "博主牛", "up牛", "up主牛", "大佬牛",
            "赞", "好看", "支持", "来了", "打卡", "签到", "蹲", "蹲一个", "催更", "催更了",
            "顶", "沙发板凳", "前排占座", "抢前排", "路过", "围观", "占个楼",
            "已收藏", "已点赞", "已投币", "已关注", "关注了", "粉了", "路转粉",
            "感谢分享", "谢谢分享", "感谢up", "谢谢up", "辛苦了", "鼓掌", "爪巴",
        }
        kept = []
        for c in comments:
            txt = (c.get("text") or "").strip()
            if not txt:
                continue
            key = re.sub(r"\s+", "", txt).lower()
            # 超短（≤2 字）且无信息量
            if len(txt) <= 2:
                continue
            # 纯符号 / 表情
            if re.fullmatch(r"[\W_]+", txt):
                continue
            # 低信息水帖（短评且命中水词）
            if len(txt) <= 8 and key in JUNK:
                continue
            # 纯情绪词 + 标点（如 "哈哈哈哈！！！"）
            if re.fullmatch(r"[\W_]*[哈呵嘻哦哎咦额吼]+[\W_]*", txt):
                continue
            kept.append(c)
        return kept

    def _read_history_lines(self, md_path):
        """
        读取已有 {bv}.md 的「# 统计历史」章节，返回保留 '- ' 前缀的历史行列表。
        保留前缀是为了回写时可直接 extend，保证历次抓取能正确累积、
        不覆盖旧记录（下一轮读取仍能识别这些行）。
        """
        if not md_path.exists():
            return []
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            return []
        out = []
        in_hist = False
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("# 统计历史"):
                in_hist = True
                continue
            if in_hist:
                if s.startswith("# "):
                    break
                if s.startswith("- "):
                    out.append(s)
        return out

    def _extract_subtitle_with_fallback(self, bv_id: str, audio_path: str):
        """
        提取字幕三级策略：CC → AI 字幕 → Whisper ASR

        策略：
        1. 优先提取 B站 CC 字幕（人工校对，质量最高、最快）
        2. CC 不可用则直取 B站 AI 字幕（机器生成，纯网络、不需要 GPU）
        3. AI 字幕也不可用，回退 Whisper ASR（慢、吃资源、但兜底）
        """

        # 1. 尝试提取 CC 字幕
        try:
            subtitle = self._bilibili.extract_subtitle(bv_id)
            if subtitle and subtitle.full_text:
                logger.info(f"CC 字幕提取成功: {bv_id}")
                return subtitle
        except Exception as e:
            logger.warning(f"CC 字幕提取失败，尝试 AI 字幕: {e}")

        # 2. CC 字幕不可用，尝试直取 B站 AI 字幕（WBI 签名，纯网络请求）
        try:
            subtitle = self._bilibili.extract_ai_subtitle(bv_id)
            if subtitle and subtitle.full_text:
                logger.info(f"AI 字幕提取成功: {bv_id}")
                return subtitle
        except Exception as e:
            logger.warning(f"AI 字幕提取失败，将使用 Whisper ASR: {e}")

        # 3. AI 字幕不可用，尝试 Whisper ASR
        try:
            logger.info(f"启动 Whisper ASR: {bv_id}")
            whisper_segments = transcribe_with_whisper(audio_path)

            # whisper_segments 已经是 [{"start": ..., "end": ..., "text": ...}, ...]
            # 无需转换，直接用
            segments = whisper_segments
            full_text = "\n".join(s["text"] for s in whisper_segments)

            logger.info(f"Whisper ASR 完成，片段数: {len(segments)}")
            return SubtitleResult(
                source="whisper",
                language="zh",
                segments=segments,
                full_text=full_text,
            )
        except Exception as e:
            logger.error(f"Whisper ASR 也失败: {e}")
            # 两者都失败，返回空结果
            return SubtitleResult(source="error", language="", full_text="")
