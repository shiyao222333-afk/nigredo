# Nigredo · 馏析 — 外部数据采集引擎

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Nigredo**（馏析）是一人公司工坊的**外部数据采集引擎**。职能：从互联网获取有价值的信息——企微群消息、视频内容、平台数据——蒸馏为结构化知识，自动注入 Citrinitas 知识引擎。

分两大块：**第一层数据采集**，**第二层采集数据处理**。采集先做。

```
外部世界 → Nigredo 采集 → Citrinitas 知识存储 → Rubedo 变现执行
              ↑                                       │
              └──────── Rubedo 调用 API ──────────────┘
```

---

## 当前重心

**企微群消息采集——从零调研。** 详见 [BLUEPRINT.md](BLUEPRINT.md)。

---

## 已有能力

| 功能 | 说明 |
|------|------|
| B站视频下载 | yt-dlp 多格式下载 |
| 字幕提取 | CC 字幕 + Whisper ASR 兜底 |
| LLM 文档化 | 学习笔记 / 脚本模仿 / 爆款分析 三套模板 |
| 弹幕 + 评论分析 | 数据采集 + LLM 语义分析 |
| 自动入知识库 | 结构化数据注入 Citrinitas（Qdrant） |

---

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 LLM API Key
streamlit run app.py   # http://127.0.0.1:8502
```

---

## 项目结构

```
nigredo/
├── app.py              # Streamlit 入口
├── pages/              # UI 页面
├── core/               # 核心逻辑（下载/字幕/文档化/分析）
├── platforms/          # 平台适配器（一平台一文件）
├── prompts/            # LLM Prompt 模板
├── BLUEPRINT.md        # 项目宪法
├── PROJECT_PLAN.md     # 版本路线图
├── FLOWCHART.md        # 流程框图
└── CHANGELOG.md        # 变更记录
```

---

## OpusMagnum 生态

| 项目 | 职能 |
|------|------|
| [OpusMagnum](https://github.com/shiyao222333-afk/opus-magnum) | 总蓝图 |
| [Citrinitas](https://github.com/shiyao222333-afk/citrinitas) | 知识引擎——Nigredo 数据最终注入此处 |
| [Rubedo](https://github.com/shiyao222333-afk/rubedo) | SOP 自动化——通过 API 调用 Nigredo |
| [Albedo](https://github.com/shiyao222333-afk/albedo) | 矛盾检测 |

---

MIT © [shiyao222333-afk](https://github.com/shiyao222333-afk)
