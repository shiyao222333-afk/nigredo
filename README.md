# ⚗️ Nigredo · 馏析 — 内容提炼 · 学习模仿引擎

> *Ex tenebris, lumen scientiae.* — 从混沌中提炼知识之光

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Phase](https://img.shields.io/badge/Phase-Alpha-orange)]()

**Nigredo**（馏析）是一人公司工坊的**学习模仿引擎**。它将网络上成功者的内容——B站视频、小红书笔记——蒸馏为可分析的结构化知识。

核心逻辑：**副业最快的方式就是模仿成功的人**。Nigredo 负责"拆解"——把别人怎么做的、怎么说的、怎么写的，变成可以研究的原材料。

```
🔗 内容链接 → 🎵 内容下载 → 📝 文本提取 → 🤖 LLM结构化 → 📊 模式分析 → 📚 Citrinitas 注入
```

---

## 🎯 为什么叫"学习模仿引擎"

| 场景 | 输入 | 输出 | 目的 |
|------|------|------|------|
| 📖 一人公司案例学习 | B站"一人公司"类视频 | 结构化笔记：商业模式、收入来源、关键决策 | 模仿成功路径 |
| ✍️ 小红书文案模仿 | 小红书爆款笔记 | 结构拆解、话术模板、情绪曲线 | 学习怎么写能火 |
| 🔥 竞品/同行分析 | 同类UP主视频合集 | 横向对比、因子分析、差异标注 | 找到自己的差异化角度 |

---

## 🏗️ 架构

```
nigredo/
├── app.py                      # Streamlit 入口
├── pages/                      # UI 页面（5页）
│   ├── 0_📹_关于.py
│   ├── 1_📥_视频摄入.py
│   ├── 2_📝_文档输出.py
│   ├── 3_📊_数据分析.py
│   └── 4_🔥_爆款分析.py
├── core/                       # 核心逻辑（Streamlit-free）
│   ├── __init__.py             # 通用工具
│   ├── downloader.py           # 统一下载管理器
│   ├── subtitle.py             # CC字幕 + Whisper ASR
│   ├── documenter.py           # LLM 文档化（3场景）
│   ├── data_fetcher.py         # 平台数据采集
│   ├── danmaku.py              # 弹幕分析
│   ├── comment.py              # 评论分析
│   ├── analyzer.py             # 单视频综合分析
│   ├── viral.py                # 爆款横向对比
│   └── kb_bridge.py            # Citrinitas 熔知联动
├── platforms/                  # 平台适配器
│   ├── __init__.py             # 抽象基类
│   └── bilibili.py             # B站实现
├── prompts/                    # LLM Prompt 模板
│   ├── study_note.md           # 学习笔记
│   ├── script_imitate.md       # 脚本模仿
│   └── viral_analysis.md       # 爆款分析
├── utils/                      # 工具
│   ├── __init__.py             # Cookie 管理
│   ├── queue.py                # 任务队列
│   └── cache.py                # 去重缓存
├── config/                     # 配置
│   ├── __init__.py             # 全局设置
├── data/                       # 本地数据
│   ├── cache/                  # 下载缓存
│   └── reports/                # 输出报告
├── .env.example                # 环境变量模板
├── requirements.txt
└── README.md
```

---

## ⚡ 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 填入你的 LLM API Key
```

### 3. 启动

```bash
streamlit run app.py
```

### 4. 命令行快速测试

```bash
# 下载单个视频的音频 + 字幕
python -c "
from core.downloader import DownloadManager
dm = DownloadManager()
result = dm.process('https://www.bilibili.com/video/BV1xx411c7mD')
print(result)
"
```

---

## 📊 处理管道

| 步骤 | 工具 | 说明 |
|------|------|------|
| 🔗 链接解析 | BV号正则 / URL路由 | 自动识别 B站/YouTube/小红书 |
| 🎵 音频下载 | yt-dlp | 优先最小编码，转 WAV |
| 📝 字幕提取 | CC → Whisper 兜底 | CC秒级，Whisper分钟级 |
| 🤖 文档化 | DeepSeek / Qwen / OpenAI | 三套 Prompt 模板 |
| 📊 数据采集 | bilibili-api-python | 播放/互动/弹幕/评论 |
| 🔥 爆款分析 | LLM 横向对比 | 模式发现 + 矛盾标注 |
| 📚 熔知联动 | Qdrant HTTP API | 自动注入 Citrinitas |

---

## 🎯 三种使用场景

| 场景 | Prompt 模板 | 输出 |
|------|-----------|------|
| 📖 学习笔记 | `study_note.md` | 概念/定义/案例/待查证 |
| ✍️ 脚本模仿 | `script_imitate.md` | 结构拆解/话术模板/情绪曲线 |
| 🔥 爆款分析 | `viral_analysis.md` | 横向对比/因子分析/矛盾标注 |

---

## 🛣️ 路线图

- [x] ✅ v0.1: B站下载 + CC字幕 + LLM 文档化 (当前)
- [ ] 📋 v0.2: Whisper ASR 兜底 + 弹幕分析 + 评论分析
- [ ] 📋 v0.3: YouTube 支持 + 爆款横向对比
- [ ] 📋 v0.4: 小红书支持 + 自动发布工作流
- [ ] 💭 v1.0: 全平台 + Citrinitas 深度联动 + Albedo 矛盾检测

---

## 🔗 OpusMagnum 生态

| 项目 | 状态 |
|------|------|
| ⚛️ [OpusMagnum · 巨作](https://github.com/shiyao222333-afk/opus-magnum) — 总蓝图 + 战略雷达 | ✅ |
| 🏭 [Citrinitas · 熔知](https://github.com/shiyao222333-afk/citrinitas) — 知识引擎（核心枢纽） | ✅ v0.8.0 |
| ⚗️ Nigredo · 馏析 — 学习模仿引擎（本仓库） | 📋 Alpha |
| 🔬 [Albedo · 炼真](https://github.com/shiyao222333-afk/albedo) — 虚假信息过滤 | 💭 规划 |
| ✨ [Rubedo · 凝华](https://github.com/shiyao222333-afk/rubedo) — 副业 SOP 自动化 | 🚧 v0.1 |

---

## 📄 License

MIT © [shiyao222333-afk](https://github.com/shiyao222333-afk)
