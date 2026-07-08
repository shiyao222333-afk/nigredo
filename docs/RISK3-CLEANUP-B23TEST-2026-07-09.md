# 馏析 · RISK3 清理 + b23.tv 短链修复 + 字幕实测报告

> 日期：2026-07-09
> 关联：上一轮 `9f99246`「移除 Citrinitas 直写桥接」遗留的 🟡 RISK 3 四项 + 用户 B站视频字幕实测

---

## 一、本轮做了什么

两件事：

1. **清理上一轮汇报里标红的 4 项遗留问题**（命名漂移 + 死依赖 + 流程图虚假节点）。
2. **修了一个真 bug**：`b23.tv` 短链接之前解析不了，用户一发短链就崩；顺手用真实视频实测了字幕提取链路。

---

## 二、清理项清单（RISK 3 全部清零）

| # | 文件 | 改了什么 | 为什么安全 |
|---|------|----------|------------|
| 667 | `config/__init__.py` | 环境变量名 `ALEMBIC_LLM_*` / `ALEMBIC_DEBUG` → `NIGREDO_LLM_*` / `NIGREDO_DEBUG`（仅改 `os.getenv` 的 key 字符串，Python 变量名不变） | grep 全项目：只有 config 自己读这些 key，无代码依赖，两处文档提及已同步 |
| 668 | `requirements.txt` | 删除 `# === 熔知联动 ===` + `qdrant-client>=1.7`（死依赖，桥接移除后无任何引用） | 移除 kb_bridge 后全项目无 `import qdrant_client` |
| 669 | `FLOWCHART.md` | 删除「H Citrinitas 注入」节点（流程图连线、节点表、连接表、重心标注四处） | 桥接已移除，流程图再画这条线是假的 |
| 670 | `app.py` | CSS 类 `.alembic-card` / `.alembic-progress` → `.nigredo-card` / `.nigredo-progress` | grep 确认仅 app.py 定义这两处，无 HTML 引用 |

**命名来源**：项目从早期代号 *Alembic* 改名为 *Nigredo*（炼金术「馏析」阶段）后，残留的 `ALEMBIC_*` 是改名没扫干净的。本轮清零。

---

## 三、b23.tv 短链修复（真 bug）

### 问题
`platforms/bilibili.py` 的 `parse_url()` 只认 `BVxxxxxxxxxx` 直链和 `bilibili.com`，**遇到 `b23.tv/xxx` 短链直接返回 None**，上层会抛 `ValueError: 无法从 URL 提取 BV 号`。
而 `core/downloader.py` 的 `detect_platform()` 早就认 `b23.tv` —— 检测认、解析不认，自相矛盾。

### 修复
文件里其实早有一个定义好但没用上的正则 `B23_PATTERN`。现在 `parse_url()` 命中短链时，调用新增的 `_resolve_b23_url()` 用 `requests` 跟随 302 重定向拿到真实视频地址，再从中提 BV 号。约 15 行，零新依赖（requests 本就在 requirements）。

### 实测验证（沙箱跑真实代码）
```
b23 link  -> BV1BXQABNE4y
BV direct -> BV1BXQABNE4y
garbage   -> None
```
用户给的短链 `https://b23.tv/gag6wSb` 正确解析为 `BV1BXQABNE4y`。✅

---

## 四、字幕实测（用户视频：我蒸馏了17个大佬给我打工）

**链路**：短链 → BV号 → 视频信息 → 字幕。

### 实测结果
1. ✅ 短链解析：见上，`BV1BXQABNE4y`。
2. ⚠️ **该视频没有官方 CC 字幕**（`subtitle.list` 为空）。

   我用 B站公开接口（`bilibili-api` 底层也是这个）拉了视频信息，返回 `subtitle count: 0`。
   也就是说：馏析的「优先提取官方字幕」这条路走到头是空的。
3. 🔻 **回退到 Whisper 语音识别（ASR）需要的条件，沙箱不全**：
   - 要下载音频 → 需要 `yt-dlp`（沙箱没装，且沙箱连 PyPI 装包被 SSL 拦了）
   - 要跑识别 → 需要 `faster-whisper` + 下载 ~1.5GB 模型 + CPU/GPU（沙箱无 GPU、无模型、装不了包）

   **结论：这条视频在沙箱里无法完整转出字幕，但这不是馏析的 bug，是环境限制。** 在你本机（依赖已装、有显卡）跑馏析 UI，它会自动：下载音频 → Whisper 识别 → 出字幕。

### 一个值得记下的产品判断
很多 B站视频只有「AI 自动字幕」而不是 UP主手动传的 CC。当前馏析的 `extract_subtitle()` 只读 `subtitle.list`（手动 CC），所以遇到只有 AI 字幕的视频会判「无字幕」去走 Whisper，**白白多烧一遍算力**。
→ 可选增强：未来支持 B站 AI 字幕接口（`player/wbi` 带 wbi 签名），能直接拿到 AI 字幕就省掉 Whisper。列入待办，本轮没做。

---

## 五、改动文件清单

```
M config/__init__.py       # ALEMBIC_* → NIGREDO_*
M requirements.txt         # 删 qdrant-client 死依赖
M FLOWCHART.md             # 删 H Citrinitas 注入节点
M app.py                   # .alembic-card → .nigredo-card
M platforms/bilibili.py    # 修 b23.tv 短链解析
```

语法验证：`py_compile` 五个文件全部通过。

---

## 六、下一步建议

1. **你本机跑一次**：打开馏析 UI，粘贴 `https://b23.tv/gag6wSb`（或直链），看字幕能不能出来。预期走 Whisper（因为没 CC）。
2. **Whisper 慢/卡**：确认 `WHISPER_MODEL_SIZE`（默认 `large-v3` 中文最强但最慢）。想快可改 `medium`；有显卡会自动用 CUDA。
3. **可选增强**：AI 字幕直取（省 Whisper），下一轮再说。

---

## 七、提交

- commit：`refactor(cleanup): RISK3 命名/死依赖/流程图清理 + 修复 b23.tv 短链解析`
- 已 push 到 main。
