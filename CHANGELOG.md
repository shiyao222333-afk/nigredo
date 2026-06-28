# Changelog

本文件记录 Nigredo（馏析）所有值得注意的变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### Added
- v0.1.0 步骤3 ✅：影刀RPA社区版实测完成（结论：可用但排除——未来付费风险）
- v0.1.0 步骤4 ✅：深入分析两个免费可行方案
  - 方案 #12 wechat-decrypt：企微本地数据库解密（Windows 5.x支持，但封号风险高）
  - 方案 #13 UIA自动化：pywinauto控制企微窗口（低风险，MIT协议，可产品化）
  - 详细技术报告：`RESEARCH.md`
- 推荐方案：#13 UIA自动化为主，#12 wechat-decrypt 备用
- 下一步：搭建 UIA自动化原型（pywinauto + 企微窗口 + 实时监控）

### Changed
- PROJECT_PLAN.md：更新至 v0.1.1，反映步骤3/4完成状态
- 排除方案清单更新：付费或不可行的全部标注

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
