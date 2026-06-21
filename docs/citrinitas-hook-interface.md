# 远期任务：Citrinitas 预存储钩子 — 连接熔知知识库

> 状态：⏳ 远期规划 | 依赖：Citrinitas B4 完成（空插槽就位）
> 创建日期：2026-06-21

---

## 目标

让 Nigredo 处理完的视频内容能**自动流入 Citrinitas（熔知）的知识库**，经过熔知的分类、去重、字段规范化、置信度打分后入库，用户可以直接在熔知里搜索到视频中的知识点。

---

## 当前问题

Nigredo 的 `kb_bridge.py` 直接写 Qdrant 数据库，跳过了 Citrinitas 的整套加工流程：

| 跳过的环节 | 后果 |
|-----------|------|
| 去重检查 | 同一个视频可能被重复入库 |
| 四维分面分类 | content_type / domain / temporal_nature / epistemic_status 全部缺失 |
| 字段规范化 | LLM 输出的中英文混用不会被标准化 |
| 置信度打分 | 没有可信度标记 |
| 语言检测 | 不会自动标记中英文 |

**结果**：Nigredo 入库的内容质量和覆盖面远不如手动在 Citrinitas 里摄入的内容。

---

## 解决方案概述

Citrinitas 在摄入管线的「嵌入完成」和「写入 Qdrant」之间留了一个**空插槽**（叫 `pre_store_hook`）。

这个插槽的规格文件在：`D:\citrinitas\docs\pre_store_hook_spec.md`

Nigredo 要实现的是一个钩子函数，插到这个空工位上。流程图：

```
Citrinitas 管线:
  读取 → 去重 → 切块 → 嵌入 → [空工位] → 构建Payload → 写入Qdrant
                                    ↑
                            Nigredo 钩子插在这里
```

---

## 具体任务

### 第一步：理解插槽规格

阅读 Citrinitas 侧的合约文档和代码：

| 文件 | 内容 |
|------|------|
| `D:\citrinitas\docs\pre_store_hook_spec.md` | 钩子函数的输入/输出规格 |
| `D:\citrinitas\config\hooks.py` | 钩子注册表（`register_hook()` 函数） |
| `D:\citrinitas\kb_query.py` 中的 `_step_pre_store_hooks()` | 钩子被调用的位置 |

### 第二步：实现钩子函数

在 Nigredo 中新建文件（建议放在 `core/citrinitas_hook.py`），实现一个函数：

**函数签名**：
```python
def nigredo_pre_store(state: dict) -> dict:
    """
    参数 state 包含:
        - text:       原始文本（字幕或结构化笔记）
        - chunks:     已切块的文本列表
        - vectors:    已生成的嵌入向量
        - metadata:   元数据字典
        - source:     来源标识
        - file_path:  源文件路径
        - collection: 目标知识库名称
        - model:      嵌入模型名
    
    返回值: 修改后的 state 字典（和输入格式一样）
    """
```

**钩子内部要做的事**：

| 步骤 | 做什么 | 示例 |
|------|--------|------|
| 1 | 读入 state 中的原始内容 | 拿到字幕文本 |
| 2 | 判断是否来自 Nigredo 处理的视频 | 检查 metadata 中的 `source_project` 标记 |
| 3 | 补充视频专属元数据 | `video_title`, `video_url`, `video_author`, `view_count` 等 |
| 4 | （可选）用结构化笔记替换原始字幕 | 调用 Nigredo 的 `documenter.py` 生成更好的文本 |
| 5 | 如果替换了文本，重新设置 chunks 和 vectors 标记 | 让 Citrinitas 知道需要重新切块/嵌入 |
| 6 | 返回 state | 交回 Citrinitas 继续入库 |

### 第三步：注册钩子

在 Nigredo 启动时调用 Citrinitas 的注册函数：

```python
# 在 Nigredo 启动代码中
from citrinitas.config.hooks import register_hook
from nigredo.core.citrinitas_hook import nigredo_pre_store

register_hook(nigredo_pre_store)
```

注册后，Nigredo 推送的内容每次途经 Citrinitas 管线时，都会自动经过这个钩子。

### 第四步：修改 kb_bridge.py

当前的 `kb_bridge.py` 直接写 Qdrant，需要改为**调用 Citrinitas 的 `ingest()` 函数**：

```python
# 旧方式（直接写 Qdrant — 删掉）
# qdrant_client.upsert(...)

# 新方式（走 Citrinitas 管线）
from citrinitas.kb_query import ingest
result = ingest(
    text=structured_notes,
    metadata={"source_project": "nigredo", "video_title": title, ...},
    source="nigredo",
)
```

这样 Nigredo 的每一份内容都会经过完整的 Citrinitas 管线（含我们自己的钩子）。

### 第五步：测试

1. 在 Nigredo 中处理一个 B站视频
2. 确认内容出现在 Citrinitas 的知识库里（在「智能检索」页面搜索）
3. 确认四维分面分类已自动填充（content_type、domain、temporal_nature、epistemic_status）
4. 确认字段规范化生效（中英文混杂被标准化）
5. 确认去重工作（同一个视频不会重复入库）
6. 确认视频专属元数据在知识卡片中可见（标题、UP主、网址）

---

## 依赖条件

| 条件 | 状态 |
|------|:--:|
| Citrinitas B4 完成（空插槽 + 钩子注册表就位） | ⏳ 等待中 |
| Citrinitas `ingest()` 函数对外可调用 | ⏳ 等待 B1 管道化完成 |
| Nigredo 文档生成功能稳定 | ⏳ 开发中 |
| Nigredo 能够 import Citrinitas 的模块 | 需要配置 Python 路径 |

---

## 参考文件

| 文件 | 内容 |
|------|------|
| `D:\citrinitas\docs\pre_store_hook_spec.md` | 钩子合约规格（B4 完成后生成） |
| `D:\citrinitas\config\hooks.py` | 钩子注册表（B4 完成后生成） |
| `D:\citrinitas\kb_query.py` | 入口函数 `ingest()`（B1 重构后） |
| `D:\nigredo\kb_bridge.py` | 当前的桥接代码（需要改掉） |
| `D:\nigredo\core\documenter.py` | LLM 文档化引擎（用于生成结构化笔记） |
