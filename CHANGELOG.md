# Changelog

本文件记录 Nigredo（馏析）所有值得注意的变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### Added
- **B站结构化分析数据合并落盘（单文件）**（`core/downloader.py` + `platforms/bilibili.py`）：处理 B站视频时除字幕外，新增读取并落盘——
  - **弹幕**：全文读取后做去重 + 去废（纯符号 / 超短 / 打卡类水帖 / 重复刷屏，去掉大部分无用弹幕）；frontmatter 记录去重前后计数（`danmaku_total_before` / `danmaku_after_dedup_filter` / `_duplicates_removed` / `_junk_removed`）。
  - **高赞评论**：按点赞排序只取前 50 条关键评论（不再全量下载）。
  - **视频标签**：读取 topic tags，同时写入 frontmatter 的 `tags` 与 `keywords`（直供熔知关键词，免二次抽取）。
  - **B站 AI 摘要**（`get_ai_conclusion`）：写入正文 `# AI 摘要` 章节。
  - **高能进度条 / 高光时间点**（`get_pbp`）：转为 `[mm:ss] 内容` 列表写入 `# 高光时间点` 章节。
  - **互动率分析**：frontmatter 增加 `like_rate` / `favorite_rate` / `coin_rate` / `danmaku_density_per_min`；正文 `# 统计历史` 按抓取时间累加每次的播放 / 赞 / 币 / 藏 / 弹幕去重前后计数（多次抓取不覆盖）。
  - 所有字段合并写入唯一的中转①文件 `{bv}.md`（YAML frontmatter + `# 字幕 # AI 摘要 # 高光时间点 # 弹幕 # 高赞评论 # 统计历史` 结构化章节），**不再生成 `_danmaku.txt` / `_comments.txt` sidecar**，方便炼真整文件读取分析。frontmatter 含抓取时间 `fetched_at`（+08:00）。

### Fixed
- **评论接口修正**（`platforms/bilibili.py`）：`get_comments` 改用 `bilibili_api.comment.get_comments(oid=aid, type_=CommentResourceType.VIDEO, ...)`，先经 `video.get_info()` 取 av 号(aid) 作 oid。旧 `video.get_comments()` 在 bilibili-api v17+ 已不存在（`AttributeError`）。

### Changed
- 中转① frontmatter 增加统计 / 分析字段；架构上明确：馏析只负责"采集 + 结构化落盘"，数据经炼真精炼后才进熔知（无"馏析直供熔知"）；视频标签即熔知关键词，故 `keywords` 与 `tags` 同值。

## [0.1.1] - 2026-07-12

### Added
- v0.1.0 步骤3 ✅：影刀RPA社区版实测完成（结论：可用但排除——未来付费风险）
- v0.1.0 步骤4 ✅：深入分析两个免费可行方案
  - 方案 #12 wechat-decrypt：企微本地数据库解密（Windows 5.x支持，但封号风险高）
  - 方案 #13 UIA自动化：pywinauto控制企微窗口（低风险，MIT协议，可产品化）
  - 详细技术报告：`RESEARCH.md`
- 推荐方案：#13 UIA自动化为主，#12 wechat-decrypt 备用
- 下一步：搭建 UIA自动化原型（pywinauto + 企微窗口 + 实时监控）

### Added
- 字幕生成流程接入主流程（`core/downloader.py`）：下载音频后自动提取 CC 字幕，失败则 Whisper ASR 兜底
- UI 显示改进（`pages/1_📥_视频摄入.py`）：从原始 JSON 改为显示视频信息 + 字幕内容
- 异步 API 调用修复（`platforms/bilibili.py`）：添加 `_run_async()` 包装器，兼容 bilibili-api-python v17+ 异步 API
- Credential 传递修复：Cookie 现在正确传入 Video 构造函数
- 配置管理：Whisper 参数从 `config/__init__.py` 读取（已就绪）
- 日志系统：关键步骤添加 logging，方便调试

### Changed
- PROJECT_PLAN.md：更新至 v0.1.1，反映步骤3/4完成状态
- 排除方案清单更新：付费或不可行的全部标注
- 代码清理：删除 `core/__init__.py` 中的旧下载器函数（与 `core/downloader.py` 功能重叠）
- 蓝图更新（BLUEPRINT.md）：当前重心从「企微调研」改为「B站字幕流程跑通」
- 可维护性改进：`_run_async()` 添加详细注释；变量命名改进（v → video）
- **Whisper 显卡加速 + 默认 large-v3**（`config/__init__.py` + `.env`）：检测到 CUDA 设备则默认 `device=cuda` / `compute_type=float16`，否则退回 `cpu`/`int8`；`WHISPER_MODEL_SIZE` 默认改为 `large-v3`（中文最强）；`.env` 同步更新为中文注释版。
- **Whisper 模型下载进度条**（`core/subtitle.py` + `pages/4_⚙️_引擎配置.py`）：新增 `download_whisper_model()` / `is_model_cached()` / `_HfProgressTqdm`（把 HuggingFace 下载进度转发给 Streamlit 进度条）。配置页「🎤 Whisper 配置」页签改为：显示 GPU 状态、当前模型、HuggingFace 令牌输入与保存、预下载按钮（后台线程 + `st.rerun` 轮询，显示真实 MB 进度），解决"静默卡在 0 字节"问题。
- **新增 HF_TOKEN 配置项**：匿名下载大模型常被限速导致卡住，支持填写免费只读令牌提速。
- **Whisper 模型下载重写**（`core/subtitle.py`）：原 `snapshot_download` 并发下载器在 Python 3.14 下段错误（进程直接崩）。改为 `hf_hub_download` 单文件顺序下载到 `data/models/faster-whisper-{size}`，faster-whisper 直接加载本地目录（不走缓存结构，避免二次下载）。`progress_callback` 做版本兼容：检测当前 huggingface_hub 是否支持该参数，不支持则自动跳过（新版仍可在配置页显示进度条）。
- **HuggingFace 镜像源默认开启**（`config/__init__.py`）：代码层 `os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")`——绕过受限网络 / 免墙，下载更稳更快；用户可在 `.env` 用 `HF_ENDPOINT=` 覆盖为官方源。`.gitignore` 已忽略 `data/models/`（模型不进仓库）。

### Fixed
- **缓存状态 bug**（`core/downloader.py`）：缓存命中时 `**metadata` 会覆盖 `"status": "cached"` 为 `"done"`，导致"已缓存"分支永不触发。改为显式提取字段。
- **Cookie 未传给 yt-dlp**（`platforms/bilibili.py`）：原代码在检测到 cookie 时错误地加 `--cookies-from-browser edge`（读浏览器 cookie），用户的 `BILIBILI_COOKIE` 字符串从未被使用。新增 `_write_cookie_file()` 将 HTTP cookie 转 Netscape 格式并用 `--cookies` 传入。
- **b23.tv 短链解析崩溃**（`platforms/bilibili.py`）：原 `parse_url()` 只认 `BV` 直链与 `bilibili.com`，`b23.tv` 短链返回 `None` 导致上层抛 `ValueError: 无法从 URL 提取 BV 号`（`detect_platform` 却认短链，自相矛盾）。新增 `_resolve_b23_url()` 跟随 302 重定向提取真实 BV 号（实测 `https://b23.tv/gag6wSb` → `BV1BXQABNE4y`）。

### Removed
- 死依赖 `qdrant-client`（`requirements.txt`）：移除提前的 Citrinitas 直写桥接后已无任何引用，删 `# === 熔知联动 ===` 段
- 命名漂移清理：`config/__init__.py` 的 `ALEMBIC_LLM_*` / `ALEMBIC_DEBUG` 环境变量改名为 `NIGREDO_LLM_*` / `NIGREDO_DEBUG`；`app.py` 的 `.alembic-card` / `.alembic-progress` CSS 类改名为 `.nigredo-card` / `.nigredo-progress`（项目早期代号 Alembic 改名 Nigredo 的残留）
- `FLOWCHART.md` 删除已随桥接移除的「Citrinitas 注入」节点（H），流程图不再画虚假连线
- **`_run_async` 事件循环崩溃**（`platforms/bilibili.py`）：原 `get_event_loop()+run_until_complete()` 在 Streamlit 已有运行中的循环时会抛 RuntimeError。改为检测运行中循环则丢到独立线程跑新循环。
- **CC 字幕字段映射错误**（`platforms/bilibili.py`）：`has_cc_subtitle` 误用 `allow_submit`（是否允许观众投稿字幕），改为检查 `subtitle.list` 是否非空。
- **Whisper 模型重复加载**（`core/subtitle.py`）：每次调用都重新加载模型，改为模块级缓存只加载一次。
- **下载路径硬编码**（`platforms/bilibili.py`）：`download_audio` 固定返回 `.wav`，改为用 glob 找实际输出文件；并 `capture_output` 以便报错时打印 stderr。
- **异常被静默吞掉**（多处）：`get_video_info` / `extract_subtitle` / `get_danmaku` / `get_comments` 的 `except` 现在 `logger.warning` 记录真实错误，便于排查。
- **DownloadManager 每次重建**（`pages/1_📥_视频摄入.py`）：改用 `@st.cache_resource` 复用实例。
- **死代码清理**：删除 `core/subtitle.py` 未使用的 `full_text_parts`；删除 `core/downloader.py` 方法内重复的 `from platforms import SubtitleResult`。
- **报错信息吞掉真实原因**（`platforms/bilibili.py`）：`subprocess.CalledProcessError` 默认只暴露命令行和 exit code，真实 stderr（如 `HTTP Error 412`）看不到。改为在异常中带上 stderr，并对 412 / 缺 Cookie 给出中文指引。
- **yt-dlp 兜底路径未传 Cookie**（`_get_info_via_ytdlp`）：信息兜底之前也没带 Cookie，现已统一复用 `_write_cookie_file()`。
- **根因说明**：B站现在对元数据请求强制要求登录 Cookie（SESSDATA），否则返回 `HTTP Error 412: Precondition Failed`。项目此前无 `.env`，`BILIBILI_COOKIE` 为空 → 所有下载失败。
- **新增 `.env` 模板**：含 `BILIBILI_COOKIE` 等全部配置项及获取 Cookie 的图文步骤（已被 .gitignore 忽略，不会泄露）。
- **Cookie 自动获取（免手动）**（`platforms/bilibili.py` + `config/__init__.py`）：新增 `BILIBILI_BROWSER` 配置与 `_resolve_cookie()` 方法。优先级：`.env` 的 `BILIBILI_COOKIE` 手动覆盖 > 自动读浏览器(Edge/Chrome/Firefox)已登录的 B站 Cookie > 匿名。默认留空即自动读浏览器，用户无需复制 Cookie。测试确认 bilibili-api 的 get_info 无需 Cookie，仅 yt-dlp 下载需 Cookie，故浏览器 Cookie 自动读取已足够打通下载流程。

### Added
- **B站设置界面（免改文件）**（`pages/4_⚙️_引擎配置.py`）：新增「📺 B站配置」页签，可在界面里选择自动读取 Cookie 的浏览器（火狐/Chrome/Edge，默认 firefox）并手动粘贴 Cookie，「保存」按钮把配置写回 `.env`（`config.save_to_env`），重启后依然保留。
- **B站超链接**（`pages/1_📥_视频摄入.py` + `pages/4_⚙️_引擎配置.py`）：界面内新增「🔗 打开 B站」按钮，一键在浏览器打开 bilibili.com 登录页，无需手动输网址。
- **界面 Cookie 即时生效**（`core/downloader.py` + `pages/1_📥_视频摄入.py`）：`DownloadManager.process()` 新增可选 `cookie` / `browser` 参数，摄入页从 `session_state` 读取界面配置并传入，设置改动当前会话立即生效（无需重启）。

### Changed
- **默认浏览器改为 firefox**（`config/__init__.py` + `.env`）：使用者使用火狐，故 `BILIBILI_BROWSER` 默认值由 `edge` 改为 `firefox`。

### Added
- **B站 AI 字幕直取**（`platforms/bilibili.py`）：新增 `extract_ai_subtitle()`，通过 `player/wbi/v2` 接口（WBI 签名）直取 B站 机器生成的 AI 字幕——纯网络请求、匿名即可、不需 GPU，比 Whisper ASR 快且免费。签名复用 `bilibili_api.utils.network` 内部权威 `_enc_wbi` / `_get_mixin_key`（绕过强制登录的 `Credential` 类）。实测匿名调用返回 `code=0`，签名正确。
- **字幕三级策略**（`core/downloader.py`）：fallback 链由「CC → Whisper」升级为「CC → AI 字幕 → Whisper」。无人工 CC 字幕时先直取 B站 AI 字幕，仍无则回退 Whisper ASR。
- **方案A：任务队列**（`core/queue.py` + `run_queue.py` + `run.bat`）：AI 或外部程序调用 `enqueue(url)` 把地址写入 `data/queue.json`；用户双击 `run.bat` 时 `run_queue.py` 在启动 UI 前 drain 队列自动处理，无需手动粘贴。单地址失败不影响后续与 UI 启动。

---

## [0.3.0] — 2026-06-26（已废弃）

> 此版本管理文件已全部推倒重建。蓝图和计划以 v1.0 / v0.1.0 为准。

### Changed
- 角色从"视频分析引擎"扩展为"外部数据采集与摄入引擎"
- 企微自动化采集纳入 Nigredo

---

## [0.2.0] — 2026-06-22

### Added
- Whisper ASR 字幕兜底
- 弹幕分析 + 评论分析

---

## [0.1.0] — 2026-06-19

### Added
- B站视频下载 + CC 字幕提取
- LLM 文档化（学习笔记 / 脚本模仿 / 爆款分析）
- Streamlit Web UI
