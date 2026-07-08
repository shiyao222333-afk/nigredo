# Nigredo 竞品分析报告

> 调研日期：2026-06-23 | 调研范围：多平台视频下载 + 字幕提取 + AI文档化工具

---

## 1. 竞品全景图

### 1.1 AI-Video-Transcriber

| 维度 | 详情 |
|------|------|
| **GitHub** | wendy7756/AI-Video-Transcriber |
| **技术栈** | FastAPI + Faster-Whisper + OpenAI API |
| **支持平台** | 30+（通过 yt-dlp），包括 B站/YouTube/TikTok/播客/本地文件 |
| **字幕策略** | 优先原生字幕 → Faster-Whisper 兜底 |
| **AI功能** | 文本优化 + 翻译 + 摘要 |
| **部署方式** | Docker / 本地 Python |
| **优势** | 全平台覆盖、纯前端API配置、SSE实时进度、字幕优先设计 |
| **劣势** | 无弹幕分析、无知识库、无爆款对比、无视频数据分析 |

**核心管道**：
```
URL输入 → yt-dlp下载 → CC字幕提取 / Whisper ASR → LLM优化 → LLM翻译 → LLM摘要
```

### 1.2 BiliSum

| 维度 | 详情 |
|------|------|
| **GitHub** | lycohana/BiliSum |
| **技术栈** | Electron + React + FastAPI + SQLite |
| **支持平台** | B站 + YouTube + 本地文件 |
| **字幕策略** | SiliconFlow ASR / FunASR / 多模态ASR / Whisper（四选一） |
| **AI功能** | 文本笔记 + VLM图文笔记 + 思维导图 + 知识库RAG |
| **部署方式** | Windows/macOS桌面端 + Docker浏览器版 |
| **优势** | FunASR中文优化（比Whisper快13倍）、VLM图文笔记、知识库、数据全本地、多模型灵活组合 |
| **劣势** | 平台支持有限（无小红书/抖音）、重客户端（Electron）、竞品功能在非中文平台意义不大 |

**核心功能链路**：
```
视频输入 → ASR转写 → 文本笔记 → 图文笔记 → 思维导图 → 知识库(RAG问答)
```

### 1.3 下载工具对比

| 工具 | 类型 | 支持平台 | 技术 | 扩展性 |
|------|------|----------|------|--------|
| **yt-dlp** | CLI/Python库 | 1700+ | Python | ⭐⭐⭐⭐⭐ |
| **cobalt** | Web/API | 20+ | Node.js | ⭐⭐⭐ |
| **MediaGo** | GUI | 多平台 | Electron | ⭐⭐ |
| **Res-Downloader** | GUI | 国内主流 | Go+Wails | ⭐⭐ |

> **结论**：yt-dlp 是无可争议的行业标准，已内置小红书（xiaohongshu.py）和抖音（douyin.py）提取器。

---

## 2. 功能矩阵对比

| 功能 | AI-Video-Transcriber | BiliSum | **Nigredo (当前)** | **Nigredo (目标)** |
|------|:---:|:---:|:---:|:---:|
| **B站支持** | ✅ | ✅ | ✅ | ✅ |
| **YouTube支持** | ✅ | ✅ | ❌ | ✅ |
| **抖音/TikTok** | ✅ | ❌ | ❌ | ✅ |
| **小红书** | ❌ | ❌ | ❌ | ✅ |
| **CC字幕提取** | ✅ | ✅ | ✅ | ✅ |
| **Whisper ASR** | ✅ Faster | ✅ | ✅ | ✅ |
| **FunASR ASR** | ❌ | ✅ | ❌ | 📋 远期 |
| **AI学习笔记** | ✅ 摘要 | ✅ | ✅ 结构化 | ✅ |
| **脚本模仿** | ❌ | ❌ | ✅ | ✅ |
| **爆款对比分析** | ❌ | ❌ | ✅ | ✅ |
| **弹幕分析** | ❌ | ✅ 基础 | ✅ 完整 | ✅ |
| **评论分析** | ❌ | ❌ | ✅ | ✅ |
| **知识库联动** | ❌ | ✅ RAG | ✅ Citrinitas | ✅ |
| **VLM图文笔记** | ❌ | ✅ | ❌ | 📋 远期 |
| **思维导图** | ❌ | ✅ | ❌ | 📋 远期 |
| **M3U8直播流** | ❌ | ❌ | ❌ | ✅ |
| **数据全本地** | ❌ (API) | ✅ | ✅ | ✅ |

---

## 3. 技术选型分析

### 3.1 统一下载引擎：yt-dlp

**结论：必须采用，无替代方案。**

| 维度 | 评估 |
|------|------|
| 平台覆盖 | 1700+ 网站，已含小红书/抖音提取器 |
| 更新频率 | 每日更新，社区极活跃 |
| API稳定性 | Python可直接import使用 |
| 字幕支持 | 原生字幕提取 + 格式转换 |
| 视频元数据 | 标题/描述/UP主/播放量/时长等 |
| Cookie支持 | 浏览器Cookie导入（解决风控） |

**Nigredo现有实现**：`downloader.py`已调用yt-dlp CLI下载B站音频，但需要重构为Python API调用，避免subprocess开销。

### 3.2 语音转文字：FunASR vs Whisper

| 维度 | Faster-Whisper | FunASR |
|------|:---:|:---:|
| **中文准确率** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **推理速度** | 慢（GPU） | **快13倍**（CPU） |
| **GPU需求** | 需要 | CPU即可（Nano版250万参数） |
| **VAD** | 内置 | 内置 |
| **说话人分离** | 需额外插件 | ✅ 内置 |
| **部署复杂度** | 简单 | 中等 |
| **社区活跃度** | 极活跃 | 活跃（阿里系） |
| **模型大小** | 74M-3GB | 250万-数亿参数 |

**建议**：Nigredo v0.1 **保持 Faster-Whisper**（已实现），v0.2+ 可引入FunASR作为中文场景优化选项。

### 3.3 平台适配器模式

Nigredo现有的`BasePlatform`抽象基类设计非常正确，AI-Video-Transcriber和BiliSum都采用了类似的设计：

```
Nigredo (现有)：
  BasePlatform → BilibiliPlatform ✅
               → YouTubePlatform ❌ 待开发
               → XiaohongshuPlatform ❌ 待开发
               → DouyinPlatform ❌ 待开发

AI-Video-Transcriber：
  yt-dlp（统一处理）→ 不区分平台适配器

BiliSum：
  直接使用yt-dlp，无平台抽象层
```

**Nigredo优势**：平台适配器模式允许针对每个平台做深度定制（弹幕、评论、特有数据），而竞品只做通用处理。

---

## 4. Nigredo 现有实现评估

### 4.1 已实现（22个Python文件）

| 模块 | 文件 | 完成度 | 评价 |
|------|------|:---:|------|
| 抽象基类 | `platforms/__init__.py` | 100% | VideoInfo + SubtitleResult数据类设计优秀 |
| B站适配器 | `platforms/bilibili.py` | 95% | 完整实现，缺少短链接解析 |
| 下载管理 | `core/downloader.py` | 70% | B站完成，需扩展多平台路由 |
| 字幕提取 | `core/subtitle.py` | 90% | CC优先+Faster-Whisper兜底，完善 |
| LLM文档化 | `core/documenter.py` | 95% | 三套Prompt模板，结构清晰 |
| 弹幕分析 | `core/danmaku.py` | 80% | 有独立模块 |
| 评论分析 | `core/comment.py` | 70% | 有独立模块 |
| 视频分析 | `core/analyzer.py` | 60% | 单视频综合分析 |
| 爆款分析 | `core/viral.py` | 60% | 横向对比 |
| 知识库桥接 | `core/kb_bridge.py` | ❌ 已移除 | 提前耦合风险，待各项目可用后再整合（走 Citrinitas ingest 接口，不直写库） |
| 数据采集 | `core/data_fetcher.py` | 60% | 平台数据 |
| UI页面 | `pages/` (5页) | 80% | Streamlit界面 |
| 辅助模块 | `utils/` (3文件) | 70% | 缓存/队列/Cookie |

### 4.2 缺失功能

| 优先级 | 功能 | 说明 |
|:---:|------|------|
| 🔴 P0 | **YouTube平台适配器** | 最优先，yt-dlp已支持，只需实现BasePlatform接口 |
| 🔴 P0 | **小红书平台适配器** | yt-dlp有xiaohongshu.py提取器 |
| 🔴 P0 | **抖音平台适配器** | yt-dlp有douyin.py提取器 |
| 🟡 P1 | **下载器Python API化** | 当前用subprocess调用yt-dlp CLI，重构为Python API调用 |
| 🟡 P1 | **M3U8直播流** | 某些平台/直播内容需要 |
| 🟢 P2 | **FunASR集成** | 中文场景更好的准确率和速度 |
| 🟢 P2 | **VLM图文笔记** | 视觉模型理解视频画面 |

---

## 5. Nigredo v0.1 技术方案

### 5.1 架构优化建议

**当前架构**（保持，只需扩展）：
```
platforms/
├── __init__.py      # BasePlatform 抽象基类 ✅
├── bilibili.py      # B站适配器 ✅
├── youtube.py       # YouTube适配器 ❌ 新增
├── xiaohongshu.py   # 小红书适配器 ❌ 新增
├── douyin.py        # 抖音适配器 ❌ 新增
└── adapter_factory.py  # 平台适配器工厂 ❌ 新增
```

**下载器重构**：从subprocess CLI调用 → Python API调用
```python
# 现有实现（subprocess）
subprocess.run(["yt-dlp", "-f", "worstaudio", ...])

# 建议改为（Python API）
from yt_dlp import YoutubeDL
opts = {"format": "worstaudio", "outtmpl": ...}
with YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=True)
```

### 5.2 实施步骤

| 阶段 | 任务 | 工作量 | 依赖 |
|:---:|------|:--:|------|
| **v0.1.1** | YouTube适配器 | 3h | yt-dlp |
| **v0.1.2** | 小红书适配器 | 3h | yt-dlp xiaohongshu提取器 |
| **v0.1.3** | 抖音适配器 | 2h | yt-dlp douyin提取器 |
| **v0.1.4** | 下载器Python API化 | 2h | 上述适配器完成后 |
| **v0.1.5** | 全平台端到端测试 | 2h | 所有适配器完成 |
| **v0.1.6** | 管理文件补全 | 2h | 独立 |

### 5.3 Nigredo 差异化优势

相比竞品，Nigredo拥有以下不可替代的优势：

1. **弹幕分析** — 竞品（AI-Video-Transcriber）完全没有，BiliSum只有基础功能
2. **脚本模仿** — 唯一提供视频脚本结构拆解+话术模板提取的工具
3. **爆款横向对比** — 跨视频模式发现，竞品缺失
4. **炼金工坊生态** — 与Citrinitas知识库深度联动，形成数据飞轮
5. **平台深度定制** — 不仅下载视频，还抓取弹幕/评论/数据分析，竞品只做通用处理

---

## 6. 参考来源

- [AI-Video-Transcriber](https://github.com/wendy7756/AI-Video-Transcriber) — 30+平台音视频转录摘要
- [BiliSum](https://github.com/lycohana/BiliSum) — B站+YouTube视频知识提取
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 1700+网站视频下载引擎
- [FunASR](https://www.funasr.com/) — 阿里达摩院开源语音识别
- [cobalt](https://github.com/imputnet/cobalt) — Web端多平台下载工具
