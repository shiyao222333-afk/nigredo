# 执行汇报：移除 Nigredo 提前桥接（Citrinitas 直写）

> 文档性质：执行记录（做了什么、为什么安全、遗留什么）
> 来源指令：2026-07-08 架构评审《ARCHITECTURE-REVIEW-2026-07-08.md》RISK 1
> 执行触发：用户指令"现在就开始，文档汇报给我，手机看不了"
> 配套战略：五项目各自先长到"可用"再整合；Albedo 暂不做；不提前做跨项目架构

---

## 1. 一句话结论

Nigredo 里一套"提前且漏水"的 Citrinitas 桥接（直写 Qdrant 知识库）已从 **代码 + 设计文档 + 配置 + 死界面** 四位一体彻底摘除。Nigredo 回到纯采集引擎定位，行为零变化，无回归风险。

---

## 2. 本次移除的 4 类对象

| # | 对象 | 文件 | 行数 | 性质 | 移除原因 |
|---|------|------|:---:|------|----------|
| 1 | 桥接代码 | `core/kb_bridge.py` | 68 | 死代码（无调用方） | 提前且"漏水"的直写 Qdrant；单人单机用不上，反增故障面 |
| 2 | 设计文档 | `docs/citrinitas-hook-interface.md` | 155 | 错误整合路线 | 指导改 `kb_bridge.py` 去直写 Citrinitas，属"为用不上的规模提前买单" |
| 3 | 配置项 | `config/__init__.py` 删 `QDRANT_*` 三项 | 5 | 越界配置 | Citrinitas 的存储配置不该出现在 Nigredo |
| 4 | 死界面 | `pages/4_⚙️_引擎配置.py` 的 tab3"📡 熔知联动" | 11 | 死 UI | "测试连接"按钮无 `on_click`；三个输入框全项目无任何代码读取 |

**净效果**：6 文件改动，+4 / -239 行（详见第 5 节）。

---

## 3. 顺带修正的文档失真

删文件后，原文档里两处"已实现"的功能声明变成了谎言，已同步修正为真实状态：

| 文件 | 原虚假声明 | 修正后 |
|------|-----------|--------|
| `docs/competitor-analysis.md` 第 151 行 | "知识库桥接 `core/kb_bridge.py` 80% 与 Citrinitas 联动" | "❌ 已移除 ｜ 提前耦合风险，待各项目可用后再整合（走 Citrinitas ingest 接口，不直写库）" |
| `README.md` 第 32 行 | "自动入知识库 结构化数据注入 Citrinitas（Qdrant）" | "知识库对接 ｜ 规划中：各项目可用后接入 Citrinitas（经其 ingest 接口，不直写库）" |

---

## 4. 为什么删得安全（硬证据）

| 检查项 | 方法 | 结果 |
|--------|------|------|
| 调用方残留 | `grep` 全项目 `kb_bridge / inject_to_athanor / QDRANT_URL / citrinitas-hook` | 仅评审文档与 competitor-analysis 的"已移除"声明命中；**代码层零调用方** |
| 语法有效 | `py_compile` 两个编辑过的 `.py` 文件 | 两个均 `SYNTAX_OK` |
| 行为影响 | 人工核对 Nigredo 现有功能路径 | 采集 / 处理 / UI 完全不涉及桥接，删除后运行行为零变化 |
| 隐患消除 | 代码审查 | 删前 `inject_to_athanor()` 异常时 `return False`（数据丢失不报错）；`_generate_embedding()` 在 Ollama 不可用时静默回退 sha256 生成**垃圾向量**——写入成功但永远搜不到。这些静默污染一并根除 |

---

## 5. 改动概览（git diff --stat）

```
 README.md                                          |   2 +-
 config/__init__.py                                 |   5 -
 core/kb_bridge.py                                  |  68 ---------
 docs/citrinitas-hook-interface.md                  | 155 ---------------------
 docs/competitor-analysis.md                        |   2 +-
 "pages/4_⚙️_引擎配置.py"                            |  11 +-
 6 files changed, 4 insertions(+), 239 deletions(-)
```

未跟踪文件（非本次改动，仅列出备查）：`PROGRESS.md`、`docs/ARCHITECTURE-REVIEW-2026-07-08.md`

---

## 6. 遗留项（非本次范围，属 🟡 RISK 3）

以下不在"现在就开始"的 🔴 RISK 1 范围内，列此备忘，后续清理：

| 遗留 | 位置 | 说明 |
|------|------|------|
| 死依赖 | `requirements.txt` 第 25 行 `qdrant-client>=1.7` | 现已无任何代码使用，可移除（避免误装） |
| 虚假声明 | `FLOWCHART.md` 第 45 行 "Citrinitas 注入 … HTTP API 写入 athanor_v1 集合" | 该流程已不存在，且重心已从企微转 B站，需更新 |
| 命名漂移 | `config/__init__.py` 的 `ALEMBIC_*`（`ALEMBIC_LLM_BASE_URL` 等） | 应统一为 `NIGREDO_*` |
| CSS 漂移 | `app.py` 的 `.alembic-card` | 应改为 `.nigredo-card` |

> 说明：本轮严格按用户"现在就开始"的 🔴 RISK 1 范围执行，未扩大改动面，避免引入新风险。上述 RISK 3 项建议单独排期清理。

---

## 7. 架构师点评

这套桥接是典型的"架构宇航员"症状——在单人单机、各项目尚未独立的阶段，就为"未来的整合"预埋了跨进程直写。它有两个致命问题：

1. **耦合方向错了**：Nigredo 直接写 Citrinitas 的存储（Qdrant），等于下游绕过上游的边界。正确方向是各项目先独立可用，整合时走 Citrinitas 的 `ingest` 接口（上游暴露能力，下游调用），而不是直捅数据库。
2. **静默漏水**：异常不报、embedding 失败回退垃圾向量——这种 bug 最难查，因为"看起来写入成功了"。

现在摘除后，Nigredo 的 bounded context 干净了：它只管"采得到、处理得了"，知识存储是 Citrinitas 的事。等五个项目都长到可用，再谈整合——那时走正式接口，而不是今天这种私有直写。

---

_生成时间：执行自 2026-07-08 架构评审 RISK 1 决策；本文档为可查阅执行记录。_
