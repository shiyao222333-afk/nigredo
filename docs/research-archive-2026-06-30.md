# Nigredo (馏析) — 企微群消息采集研究归档

> 归档日期: 2026-06-30 | 项目版本: v0.1.0 | 企微版本: 5.0.9.6029
> 归档范围: 从项目启动到 2026-06-30 01:30 的全部研究、验证、发现
> 下次工作前必读本文档

---

## 目录

1. [项目背景与目标](#一项目背景与目标)
2. [研究全景：11+ 条技术路线](#二研究全景11-条技术路线)
3. [深入分析的两个免费方案](#三深入分析的两个免费方案)
4. [wx_work_auto 源码分析（企微 4.x 时代）](#四wx_work_auto-源码分析企微-4x-时代)
5. [验证阶段：脚本与结果](#五验证阶段脚本与结果)
6. [路线 A/A+ 彻底失败：原因与证据](#六路线-aa-彻底失败原因与证据)
7. [CEF 重大发现：企微 5.x 的真实架构](#七cef-重大发现企微-5x-的真实架构)
8. [路线 E (CEF/CDP) 理论分析](#八路线-e-cefcdp-理论分析)
9. [当前路线决策状态](#九当前路线决策状态)
10. [全部产出文件清单](#十全部产出文件清单)
11. [时间线](#十一时间线)
12. [经验教训](#十二经验教训)
13. [下一步计划](#十三下一步计划)

---

## 一、项目背景与目标

### 1.1 项目定位

Nigredo（馏析）是 OpusMagnum 一人公司项目群中的**外部数据采集引擎**。

```
外部世界 → Nigredo(采集) → Citrinitas(知识存储) → Rubedo(赚钱执行)
              ↑                                         │
              └────── Rubedo 调用 Nigredo API ──────────┘
```

### 1.2 当前重心

**企微群消息监控——从零调研。**

- 只研究企微群消息的监控方案
- 不预设任何方案，从头研究
- 不研究其他平台（小红书/B站/电商）
- 不假设企微方案能复用

### 1.3 验收标准

| # | 怎么算成功 |
|---|-----------|
| 1 | 企微接单群有新消息 → 自动捕获 → 手机通知，全程不需要人盯手机 |
| 2 | 最终能当产品卖——他人也能用、也愿意付费 |

### 1.4 核心原则

1. **采集优先** — 采集没做完，不做处理管道
2. **一对象一适配器** — 不做通用框架套所有平台
3. **先调研再动手** — 不凭感觉选方案，每个平台先广泛搜竞品/开源方案
4. **手脚+大脑分离** — 采集用代码（免费），理解用 LLM（按需）
5. **可产品化** — 代码质量和架构支撑未来"卖出去"的水平

### 1.5 用户环境

| 项目 | 值 |
|------|---|
| 企微版本 | **5.0.9.6029** |
| 操作系统 | Windows (Lenovo PC) |
| 企微安装路径 | `C:\Program Files (x86)\WXWork\5.0.9.6029\` |
| 企微用户数据 | `D:\Program Files\WX\WXWork` |
| GPU | RTX 3080 (CUDA 12.6) |
| Python | 3.13.12 (managed) / 3.14.0 (system) |

---

## 二、研究全景：11+ 条技术路线

### 2.1 研究过程

研究分 4 个步骤完成：

| 步骤 | 做什么 | 产出 | 状态 |
|:--:|------|------|:--:|
| 1 | 广泛搜索——企微群消息自动化的所有方案 | 方案全景图（7条路线） | ✅ |
| 2 | 逐一评估——可行性、成本、法律风险、维护难度 | 对比决策表（11条路线） | ✅ |
| 3 | 影刀RPA实测——下载社区版 → 搭建流程 → 验证核心环节 | 实测结论：可用但排除 | ✅ |
| 4 | 深入分析免费可行方案——wechat-decrypt + UIA自动化 | 技术方案详细设计 | ✅ |

### 2.2 方案全景图（11 条路线 + 2 条后续新增）

```
企微群消息采集
├── 一、官方 API 方案
│   ├── #7  智能机器人（WebSocket）        ← 已排除（必须@才触发）
│   ├── #8  会话存档 API（seq增量拉取）      ← 需付费
│   └── #9  wecom-cli 官方CLI工具           ← MIT开源，待验证@限制
├── 二、协议层拦截
│   ├── #1  PC Hook（DLL注入）              ← 商业依赖+版本锁定
│   └── #2  iPad协议（逆向Protobuf）         ← 法律风险高
├── 三、屏幕/UI 层读取
│   ├── #3  Android无障碍服务               ← 开源但停更2.5年
│   ├── #4  PC桌面自动化（OCR+模板匹配）     ← 控件树失效，开发量大
│   └── #5  PC屏幕框选采集                   ← 无回复能力
├── 四、RPA / AI 工作流
│   ├── #10 影刀RPA（社区版免费）            ← 实测可用但排除（付费风险）
│   ├── #11 WeCom Bot MCP Server            ← 底层继承@限制
│   └── #6  QiweAPI（商业RPA服务）           ← 商业依赖
├── 五、深入分析新增
│   ├── #12 wechat-decrypt（本地数据库解密）  ← 封号风险高，无开源协议
│   └── #13 UIA自动化（pywinauto）           ← 推荐，低风险，MIT协议
└── 六、验证阶段新增
    ├── 路线A+ (.NET UIA客户端)              ← 已验证失败
    ├── 路线D (DLL注入/内存读取)              ← 版本锁定，暂不考虑
    └── 路线E (CEF/CDP)                      ← 理论可行，待验证
```

### 2.3 排除方案汇总

| # | 方案 | 排除原因 |
|---|------|---------|
| 1 | PC Hook | 付费（100元/月）+ 版本锁定 |
| 2 | iPad协议 | 法律风险高 |
| 6 | QiweAPI | 商业服务依赖 |
| 7 | 官方智能机器人 | @限制，客户不会@机器人 |
| 8 | 会话存档API | 付费（约180元/坐席/年） |
| 10 | 影刀RPA | 未来可能付费（用户决定排除） |
| 11 | MCP Server | 底层仍是智能机器人，@限制 |
| 12 | wechat-decrypt | 封号风险（Issue #140真实案例）+ 无开源协议 |

### 2.4 完整对比决策表

| # | 方案 | 收消息 | 发消息 | 成本 | 封号风险 | 开发量 | 可产品化 | 来源 |
|---|------|:--:|:--:|:--:|:--:|:--:|:--:|------|
| 1 | PC Hook | ✅全部 | ✅ | 100元/月 | 低 | 低 | ❌ | 商业 |
| 2 | iPad协议 | ✅全部 | ✅ | 需问价 | ⚠️高 | 极高/低 | ⚠️法律风险 | 商业SDK |
| 3 | Android无障碍 | ✅可见 | ✅ | 免费 | 低 | 中 | ✅ | 开源(停更) |
| 4 | PC OCR自动化 | ⚠️有限 | ✅ | 免费 | 低 | 中高 | ✅ | 无现成 |
| 5 | PC屏幕框选 | ✅文本图片 | ❌ | 免费 | 低 | 零 | ❌无回复 | 开源.exe |
| 6 | QiweAPI | ✅全部 | ✅ | 需问价 | 未知 | 低 | ❌ | 商业 |
| 7 | 官方智能机器人 | ⚠️仅@ | ✅ | 免费 | ✅无 | 低 | ✅ | 官方 |
| 8 | 会话存档API | ✅全部 | ❌ | 需付费 | ✅无 | 中 | ✅ | 官方 |
| 9 | wecom-cli | ⚠️待验证 | ✅文本 | 免费 | ✅无 | 低 | ✅ | 官方MIT |
| 10 | 影刀RPA | ✅ | ✅ | 社区版免费 | 低 | 极低 | ⚠️需客户端 | RPA平台 |
| 11 | MCP Server | ⚠️待验证 | ✅ | 免费 | 取决底层 | 低 | ✅ | 开源 |
| 12 | wechat-decrypt | ✅完整 | ❌ | 免费 | 🔴高(封号) | 低 | ❌无协议 | 开源 |
| 13 | UIA自动化 | ❌5.x失败 | ✅ | 免费 | ✅无 | 中 | ✅MIT | 开源 |

> 注：#13 UIA自动化的"收消息"栏标注为"❌5.x失败"是基于验证结果的最新状态（详见第五、六章）。

---

## 三、深入分析的两个免费方案

### 3.1 方案 #12: wechat-decrypt（本地数据库解密）

| 项目 | 内容 |
|------|------|
| 仓库 | `ylytdeng/wechat-decrypt` |
| Stars | 4252 ⭐ |
| 最后更新 | 2026-06-27 |
| 开源协议 | **无**（商用需联系作者授权） |
| 企微支持 | ✅ Windows 企业微信 5.x 实验性可用 |
| 加密方案 | wxSQLite3，AES-128-CBC，MD5 per-page 派生 |
| Key 长度 | 16 字节 raw key |

**使用流程**：管理员权限 → `find_wxwork_keys.py` 提取密钥 → `decrypt_wxwork_db.py` 解密 → `monitor_web.py` Web UI + SSE 实时推送

**风险**：
- 🔴 **封号风险高** — Issue #140 确认使用后被微信判定为外挂封号
- 🔴 无开源协议，商用需授权
- 🟡 企微版本更新可能失效

**结论**：作为备用方案，不作为首选。

### 3.2 方案 #13: UIA自动化（pywinauto）

| 项目 | 内容 |
|------|------|
| 原理 | Windows UI Automation 接口读取/控制企微窗口 UI 元素 |
| 库 | pywinauto (MIT) / uiautomation |
| 法律风险 | ✅ 低 — 系统正规接口，不破解不解密 |
| 开源协议 | ✅ MIT（可商用） |
| 发消息 | ✅ 可以 |
| 限制 | 需要企微窗口打开、只能读当前加载消息 |

**初始预期**：RESEARCH.md 中推荐此方案为主，预期"企微尚未像个人微信那样屏蔽 UI 树"。

**实际结果**：企微 5.x 已完全屏蔽 UI 树，此方案在收消息方面**彻底失败**（详见第六章）。但发消息功能（键盘模拟）仍然可用。

---

## 四、wx_work_auto 源码分析（企微 4.x 时代）

### 4.1 项目概况

| 项目 | 内容 |
|------|------|
| 仓库 | `yangyuexiong/wx_work_auto` |
| 协议 | MPL-2.0 |
| 目标版本 | 企业微信 4.1.39.x |
| 最后更新 | 2025-08-03 |
| 核心难题 | 企微 4.1 使用 DirectUI（自绘界面），控件不暴露标准 UI Automation Patterns |

### 4.2 四个核心技术

#### 技术 #1: 组合键 + find_elements 穿透

```
Ctrl+1 (消息tab) → Ctrl+F (搜索) → 输入名 → 回车 → 输入消息 → 回车
```

- 最稳定的方案，不依赖控件树结构变化
- 只要企微保留键盘快捷键就能工作
- `pywinauto.keyboard.send_keys()` 发送组合键

#### 技术 #2: CChatCtrl 控件直接搜索

```python
find_elements(
    process=pid,
    class_name="CChatCtrl",    # 消息容器的类名
    control_type="Pane",
    depth=3
)
```

- 企微 4.1 虽然用了 DirectUI，但 CChatCtrl 仍暴露在 UIA 控件树中
- 可通过「进程ID + 类名」直接搜索，绕过 WeWorkWindow 装饰层
- **在企微 5.x 中此控件已不存在**（验证结果）

#### 技术 #3: 图像识别 (PyAutoGUI)

```python
pyautogui.locateOnScreen('txl.png', confidence=0.9)
```

- 不依赖任何控件树
- 受分辨率、窗口大小、遮挡影响
- 需提前截图

#### 技术 #4: QWidget 穿透

```python
main_window.child_window(class_name="QWidget", control_type="Pane")
```

- 企微底层用 Qt 框架（类名 QWidget）
- **在企微 5.x 中 QWidget 未找到**（验证结果）

### 4.3 消息读取技术链（4.x 版本，已失效）

```
1. pywinauto(backend='uia').connect → 连接企微进程
2. find_elements(process=pid, class_name="CChatCtrl") → 找到消息容器
3. container.descendants(name_re="[0-9]+条?未读?") → 找到未读标记
4. badge.parent().parent() → 向上两级找到消息项
5. msg_item.children()[0].window_text() → 发送人
6. msg_item.children()[1].window_text() → 消息内容
```

> ⚠️ 以上技术链在企微 5.x 中完全失效，因为 CChatCtrl 控件不存在。

### 4.4 分析产出文件

`docs/code-analysis-wx-work-auto.md` — 完整源码 + 分析注释，包括：
- main.py（核心自动化引擎，含 WXWorkAuto 类、send_message 流程）
- utils.py（get_pid 工具函数）
- test/t1.py（消息读取，get_real_content + get_unread_messages）
- test/t2.py（纯 uiautomation 方案）
- test/t3.py（PyAutoGUI 图像识别方案）
- test/test_get_properties.py（控件树侦查工具）
- test/test_send_message.py（消息发送示例）

---

## 五、验证阶段：脚本与结果

### 5.1 验证#1: 控件树侦查（路线 A）

**脚本**：`scripts/verify_01_control_tree.py`

**目的**：搞清楚企微 5.x 的控件结构

**方法**：
1. 用 pywinauto (backend='uia') 连接企微进程
2. BFS 遍历控件树（max_depth=7, max_controls=1000）
3. find_elements 专项搜索 CChatCtrl / QWidget
4. uiautomation 库补充检查

**结果**：

| 项目 | 结果 |
|------|------|
| 企微版本 | 5.0.9.6029 |
| 控件总数 | **仅 3 个** |
| 发现的控件 | WeWorkWindow / TitleBarWindow / PerryShadowWnd |
| CChatCtrl | ❌ 未找到 |
| QWidget | ❌ 未找到 |
| find_elements | 全空 |
| uiautomation 库 | 0 个二级子控件 |

**结论**：路线 A（UIA 直达）失败。控件树几乎空白。

---

### 5.2 讲述人测试

**目的**：验证"门卫检测"理论 — 是否因为 pywinauto 不被认可为合规 UIA 客户端

**方法**：启动 Windows 讲述人（Win+Ctrl+Enter）→ 保持运行 → 重跑 verify_01

**结果**：**完全相同**，仍然 3 个控件

**结论**：讲述人方案不可靠。但讲述人 ≠ C#/.NET UIA 客户端（检测路径可能不同），需进一步验证。

---

### 5.3 验证#1b: .NET UIA 客户端侦查（路线 A+）

**脚本**：`scripts/verify_01b_uia_pythonnet.py`

**目的**：用 pythonnet 加载 .NET UIAutomationClient.dll，触发企微暴露完整控件树

**理论依据**（来源：微信 4.1.5.16 UIA 研究，2026-03）：
> "当客户端程序引用 UIAutomationClient.dll 和 UIAutomationTypes.dll，
> 并成功附着到微信窗口，微信判断其为'无障碍场景'，加载完整控件 Provider。"

**关键区别**：
- pywinauto → COM IUIAutomation → 不被企微认可 → 只露 3 个空壳
- pythonnet → 加载 UIAutomationClient.dll (.NET managed) → 应被认可 → 暴露完整树

**DLL 加载问题及修复**：

首次运行报错 `UIAutomationClient.dll not found`。

根因：脚本只搜了 `Framework64\v4.0.30319\` 根目录，但 DLL 实际在 `WPF\` 子目录。

修复：4 级回退加载策略：
1. 完整 GAC assembly name → ✅ 成功
2. 简单 GAC name
3. 多个已知文件路径（含 WPF 子目录 + GAC v4 路径）
4. 动态 glob 搜索兜底

实际 DLL 位置：
- `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\WPF\UIAutomationClient.dll`
- `C:\Windows\Microsoft.NET\assembly\GAC_MSIL\UIAutomationClient\v4.0_4.0.0.0_31bf3856ad364e35\`

**最终结果**：

| 项目 | 结果 |
|------|------|
| pythonnet | ✅ 安装成功 |
| UIAutomationClient.dll | ✅ GAC 完整 assembly name 加载成功 |
| UIAutomationTypes.dll | ✅ 加载成功 |
| AutomationElement.FromHandle() | ✅ 成功附着 WeWorkWindow |
| 控件总数 | **仍然 3 个**（WeWorkWindow / TitleBarWindow / PerryShadowWnd） |
| 关键类名命中 | 0 |
| FindAll 搜索 CChatCtrl 等 | 全部 MISS |

**结论**：路线 A+ 彻底失败。.NET UIA "门卫检测"理论在企微 5.x 上不成立。

---

### 5.4 验证#2: 键盘快捷键（路线 B）

**脚本**：`scripts/verify_02_keyboard.py`

**目的**：测试 Ctrl+1（消息tab）、Ctrl+F（搜索）、Ctrl+A+C（剪贴板）是否可用

**测试项**：
- VP1: 窗口激活（set_focus + win32gui fallback）
- VP2: 键盘快捷键（Ctrl+1）
- VP3: 搜索对话框（Ctrl+F → 检测新窗口 → Esc）
- VP4: 剪贴板提取（Click+Ctrl+A+Ctrl+C → 三击+Ctrl+C fallback）

**状态**：脚本已创建，**用户尚未运行**

---

## 六、路线 A/A+ 彻底失败：原因与证据

### 6.1 失败总结

| 路线 | 方法 | 结果 | 控件数 |
|------|------|------|--------|
| A | pywinauto (COM IUIAutomation) | ❌ 失败 | 3 |
| A+ | pythonnet (.NET UIAutomationClient.dll) | ❌ 失败 | 3 |
| A+ (讲述人) | Windows 讲述人 + pywinauto | ❌ 失败 | 3 |

### 6.2 失败原因分析

**微信 4.1.5.16 的"门卫检测"理论不适用于企微 5.x。**

企微 5.0.9.6029 不是"检测谁来敲门"然后决定暴露多少控件。**它的原生 UI 层本身就是个空壳**——WeWorkWindow 只是一个容器窗口，真正的聊天界面根本不在 WXWork.exe 的控件树里。

这是因为在企微 5.x 中，聊天界面已经迁移到了 CEF（Chromium Embedded Framework）浏览器进程中（详见第七章）。无论用什么 UIA 客户端去敲门，看到的都只有 3 个原生窗口壳子，因为聊天内容在另一个进程的"浏览器"里。

### 6.3 与 4.x 的关键区别

| 特征 | 企微 4.1.39.x | 企微 5.0.9.6029 |
|------|--------------|----------------|
| UI 技术 | DirectUI 自绘 | DirectUI 外壳 + **CEF 内嵌浏览器** |
| CChatCtrl 控件 | ✅ 存在，可通过 find_elements 搜索 | ❌ 不存在 |
| QWidget 控件 | ✅ 存在 | ❌ 不存在 |
| 控件树 | 部分可遍历（需穿透装饰层） | 仅 3 个空壳 |
| 聊天界面渲染 | 原生 DirectUI | **CEF 浏览器（Chrome 129）** |
| UIA 可达性 | 有限（需特殊技巧） | 完全不可达 |

### 6.4 影刀佐证

影刀 RPA 有专门的"获取企业微信聊天记录"指令，能直接读取群聊消息。我们推测影刀很可能不是通过 UIA 控件树，而是通过以下方式之一实现的：
1. 连接企微内嵌的 CEF 浏览器的 DevTools 协议（路线 E）
2. 更底层的窗口消息拦截
3. DLL 注入 Hook

---

## 七、CEF 重大发现：企微 5.x 的真实架构

### 7.1 发现过程

在路线 A+ 彻底失败后，对企微进程进行了深入调查，发现了 CEF 架构。

### 7.2 双进程架构

| 进程 | 角色 | 技术 | UI 类 |
|------|------|------|-------|
| **WXWork.exe** | 原生外壳 | DirectUI 自绘 | WeWorkWindow |
| **WXWorkWeb.exe** | CEF 浏览器 | Chromium 129.0.6668.101 | — |
| └ renderer ×3 | 渲染聊天页面 | HTML/CSS/JS DOM | — |
| └ gpu-process | GPU 加速 | Chromium GPU | — |
| └ utility ×2 | 网络和存储 | Chromium Utility | — |
| └ crashpad-handler | 崩溃报告 | Chromium Crashpad | — |

### 7.3 WXWorkWeb.exe 进程详情

**主 CEF 进程 (PID 29356) 命令行参数**：
```
--user-data-dir=D:\Program Files\WX\WXWork
--noerrdialogs
--silent-launch
```

**子进程类型**（通过 `--type=` 参数识别）：
- 3 个 `--type=renderer` — 渲染聊天页面
- 1 个 `--type=gpu-process` — GPU 加速
- 1 个 `--type=utility` (network) — 网络服务
- 1 个 `--type=utility` (storage) — 存储服务
- 1 个 crashpad-handler — 崩溃报告

**User Agent**：Chrome 129.0.6668.101

### 7.4 CEF 文件位置

| 目录 | 内容 |
|------|------|
| `C:\Program Files (x86)\WXWork\5.0.9.6029\updated_web\` | libcef.dll, chrome_elf.dll, v8_context_snapshot.bin 等 CEF 核心文件 |
| `C:\Program Files (x86)\WXWork\5.0.9.6029\compatible_web\` | 兼容版 CEF 文件 |
| `C:\Program Files (x86)\WXWork\5.0.9.6029\qtCef\` | Qt + CEF 集成目录 |
| `D:\Program Files\WX\WXWork\` | CEF 用户数据目录（Local State, Profiles 等） |

### 7.5 端口扫描结果

**WXWork.exe (PID 18284) 监听端口**：

| 端口 | 用途 | HTTP 探测 |
|------|------|-----------|
| 9882 | 企微内部 IPC | ❌ 拒绝连接 |
| 9883 | 企微内部 IPC | ❌ 拒绝连接 |
| 50010 | 企微内部 IPC | ❌ 拒绝连接 |
| 50018 | 企微内部 IPC | ❌ 拒绝连接 |
| 5817 | 未知 | ⏱ 超时 |

**CDP 端口扫描**（9222-9230, 8315-8318）：**全部未开放**

**结论**：企微未开启 CDP 远程调试端口，无 DevToolsActivePort 文件。

### 7.6 架构示意图

```
┌─────────────────────────────────────────────┐
│              WXWork.exe (原生壳)              │
│  ┌─────────────────────────────────────────┐ │
│  │  WeWorkWindow (DirectUI 自绘)            │ │
│  │  ┌─────────────┐  ┌──────────────────┐  │ │
│  │  │ TitleBar     │  │  PerryShadowWnd  │  │ │
│  │  └─────────────┘  └──────────────────┘  │ │
│  │  ┌─────────────────────────────────────┐│ │
│  │  │    嵌入区域 (Windowless CEF)          ││ │
│  │  │    ↓ 传递渲染 ↓                       ││ │
│  │  └─────────────────────────────────────┘│ │
│  └─────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────┘
                       │ IPC (进程间通信)
┌──────────────────────▼──────────────────────┐
│           WXWorkWeb.exe (CEF 浏览器)          │
│  ┌─────────────────────────────────────────┐ │
│  │  Browser Process (主进程)                 │ │
│  │  --user-data-dir=D:\Program Files\WX\... │ │
│  └──────────┬──────────┬──────────┬────────┘ │
│  ┌──────────▼──┐ ┌─────▼─────┐ ┌──▼────────┐│
│  │ Renderer ×3 │ │ GPU Process│ │ Utility ×2││
│  │ (聊天页面)   │ │ (GPU加速)  │ │ (网络/存储) ││
│  │ HTML/CSS/JS │ │           │ │           ││
│  └─────────────┘ └───────────┘ └───────────┘│
└─────────────────────────────────────────────┘
```

### 7.7 关键洞察

**你看到的聊天界面本质上是一个网页**——由 WXWorkWeb.exe 这个"内嵌 Chrome 浏览器"渲染。这就是为什么 UIA 无论怎么搞都只能看到 3 个空壳：聊天内容在另一个进程的"浏览器"里，不在原生控件树里。

这也解释了：
1. 为什么 4.x 时代的 CChatCtrl / QWidget 控件全部消失——它们被 CEF 渲染的 HTML 元素取代了
2. 为什么"门卫检测"理论不成立——不是企微在隐藏控件，而是控件根本不存在于原生层
3. 为什么影刀能做到——它很可能通过 CEF 的 DevTools 协议直接读 DOM

---

## 八、路线 E (CEF/CDP) 理论分析

### 8.1 原理

如果能开启 CDP（Chrome DevTools Protocol），可以通过 WebSocket 连接到 CEF 浏览器进程，直接操作聊天界面的 DOM。

### 8.2 优势

| 特性 | 说明 |
|------|------|
| 精度 | **最高** — 直接读 DOM，精确到每个消息元素 |
| 实时性 | **高** — 可注入 MutationObserver 监听新消息，实时触发 |
| 干扰用户 | **无** — 后台静默操作，不抢焦点 |
| 抗版本更新 | **高** — DOM 结构比原生控件稳定（CSS class 名通常不变） |
| 数据完整性 | **高** — 发送人、内容、时间、消息类型全部可精确提取 |

### 8.3 开启 CDP 的可能方式

| # | 方法 | 风险 | 可行性 |
|---|------|------|--------|
| 1 | 在企微界面按 F12 / Ctrl+Shift+I | 零风险 | 未知 — 需测试 |
| 2 | 杀 WXWorkWeb.exe → 带 `--remote-debugging-port=9222` 重启 | 中等 | 可能被主进程检测 |
| 3 | DLL 注入 Hook CefSettings | 高 | 理论可行 |
| 4 | 环境变量 `CHROME_REMOTE_DEBUGGING_PORT` | 零风险 | 低概率 |

### 8.4 如果路线 E 可行的实现架构

```
Nigredo CDP 客户端
    │
    ├── WebSocket 连接 → ws://127.0.0.1:9222/devtools/page/<id>
    │
    ├── DOM 查询
    │   ├── document.querySelector('.chat-message-list')
    │   ├── 遍历 .message-item 获取发送人/内容/时间
    │   └── 提取新消息（最后一条消息 ID 对比）
    │
    ├── JS 注入
    │   ├── MutationObserver 监听 .chat-message-list 子节点变化
    │   ├── 新消息到达 → 回调通知
    │   └── 无需轮询，真正实时
    │
    └── 通知模块
        └── 新消息 → Server酱/Bark → 手机推送
```

### 8.5 路线对比总览

| | 路线 B (键盘) | 路线 E (CEF/CDP) | 路线 C (OCR) |
|---|---|---|---|
| **精度** | 中（剪贴板格式需解析） | **最高**（直接读 DOM） | 低（OCR 有误差） |
| **实时性** | 中（轮询抢焦点） | **高**（JS 监听实时触发） | 低（每轮 2-3 秒） |
| **干扰用户** | 有（操作时抢焦点） | **无**（后台静默） | 无 |
| **开发量** | 中 | 中（CDP 客户端） | 高 |
| **抗版本更新** | 中 | **高**（DOM 比控件稳定） | 高 |
| **风险** | 低 | 中（需开启调试端口） | 低 |

**路线 E 如果可行，是压倒性的最优解。**

---

## 九、当前路线决策状态

### 9.1 路线生死表

| 路线 | 方法 | 状态 | 说明 |
|------|------|:----:|------|
| A | pywinauto UIA 直达 | ☠️ 死亡 | 控件树仅 3 个空壳 |
| A+ | .NET UIA 客户端 | ☠️ 死亡 | 门卫理论在 5.x 不成立 |
| A+ (讲述人) | Windows 讲述人 | ☠️ 死亡 | 同样 3 个空壳 |
| B | 键盘 + 剪贴板 | ⏳ 待验证 | 脚本已就绪，用户未运行 |
| C | OCR 截图 | 🟡 备选 | 开发量大，精度有限 |
| D | DLL 注入/内存读取 | 🟡 远期 | 版本锁定问题 |
| E | CEF/CDP | 🔥 优先 | 理论最优，需验证可行性 |

### 9.2 当前优先级

1. **优先级 1**：运行验证#2（键盘快捷键，脚本已就绪，15 秒完成）
2. **优先级 2**：CEF DevTools 探索（F12 测试 + 可能的调试端口实验）
3. **优先级 3**：OCR 截图（路线 C，兜底方案）

### 9.3 决策矩阵（更新版）

| 验证#2 | F12/CDP | 选哪条路线 | 理由 |
|:------:|:------:|:---------:|------|
| ✅ | ✅ | **路线 E** | CDP 精度最高 + 键盘做发消息备份 |
| ✅ | ❌ | **路线 B** | 键盘方案可用，做收消息+发消息 |
| ❌ | ✅ | **路线 E** | CDP 可用就够了 |
| ❌ | ❌ | **路线 C** | 只能 OCR，开发量最大但兜底 |

---

## 十、全部产出文件清单

### 10.1 研究文档

| 文件 | 内容 | 字数 |
|------|------|------|
| `docs/wecom-research-v0.1.0.md` | 11 条路线全景调研报告 | ~8000 字 |
| `docs/code-analysis-wx-work-auto.md` | wx_work_auto 完整源码分析 | ~5000 字 |
| `docs/implementation-plan-v0.1.0.md` | 4 阶段实施计划 + 决策矩阵 | ~4000 字 |
| `RESEARCH.md` | wechat-decrypt + UIA 深入调研 | ~3000 字 |

### 10.2 验证脚本

| 文件 | 用途 | 状态 |
|------|------|:----:|
| `scripts/verify_01_control_tree.py` | 路线 A — pywinauto 控件树侦查 | ✅ 已运行 |
| `scripts/verify_01b_uia_pythonnet.py` | 路线 A+ — .NET UIA 客户端侦查 | ✅ 已运行 |
| `scripts/verify_01b_uia_csharp.cs` | 路线 A+ — C# 编译方案（备用） | 未使用 |
| `scripts/verify_02_keyboard.py` | 路线 B — 键盘快捷键 + 剪贴板 | ⏳ 待运行 |

### 10.3 运行器脚本

| 文件 | 用途 |
|------|------|
| `scripts/run_verify_01.bat` | 验证#1 一键运行（ASCII + CRLF + 扁平 goto） |
| `scripts/run_verify_01b.bat` | 验证#1b C# 方案运行器 |
| `scripts/run_verify_01b_py.bat` | 验证#1b Python 方案运行器（推荐） |
| `scripts/run_verify_02.bat` | 验证#2 一键运行 |

### 10.4 管理文件

| 文件 | 内容 |
|------|------|
| `BLUEPRINT.md` | 项目蓝图 v1.0（愿景/原则/重心/边界/验收） |
| `PROJECT_PLAN.md` | 项目计划 v0.1.1（步骤1-4完成，步骤5待执行） |
| `FLOWCHART.md` | 流程框图 v1.0（8节点定义表） |
| `CHANGELOG.md` | 变更记录 |

---

## 十一、时间线

| 时间 | 事件 |
|------|------|
| 2026-06-19 | Nigredo 项目创建，初始版本 v0.1.0（B站视频下载） |
| 2026-06-22 | v0.2.0 — Whisper ASR + 弹幕分析 |
| 2026-06-26 | 项目推倒重建，角色变为"外部数据采集引擎"，聚焦企微采集 |
| 2026-06-26 | 步骤1完成 — 7条路线全景图 |
| 2026-06-26 | 步骤2完成 — 11条路线对比决策表 |
| 2026-06-27 | 步骤3完成 — 影刀RPA实测（可用但排除） |
| 2026-06-28 | 步骤4完成 — wechat-decrypt + UIA 深入调研 |
| 2026-06-28 | 推荐 UIA 自动化为主方案 |
| 2026-06-30 00:08 | wx_work_auto 完整源码分析完成 |
| 2026-06-30 00:13 | 完整实施计划 + verify_01 脚本创建 |
| 2026-06-30 00:32 | run_verify_01.bat 闪退修复（CRLF + 扁平 goto） |
| 2026-06-30 00:19 | **验证#1 运行** — 仅 3 个控件，路线 A 失败 |
| 2026-06-30 00:39 | verify_02 键盘脚本创建 |
| 2026-06-30 00:41 | 路线 A"假死"分析 — 发现"门卫检测"理论 |
| 2026-06-30 00:48 | 讲述人测试 — 同样 3 个控件 |
| 2026-06-30 00:51 | verify_01b C# 方案创建 |
| 2026-06-30 00:54 | verify_01b Python 方案创建 |
| 2026-06-30 00:58 | verify_01b DLL 加载路径修复（WPF 子目录） |
| 2026-06-30 ~01:10 | **验证#1b 运行** — 仍然 3 个控件，路线 A+ 失败 |
| 2026-06-30 ~01:15 | **CEF 重大发现** — 企微 5.x 使用 Chrome 129 内嵌浏览器 |
| 2026-06-30 ~01:25 | CEF 架构深入调查（进程/端口/文件/配置） |
| 2026-06-30 ~01:30 | 路线 E (CEF/CDP) 理论分析 + 当前决策确定 |

---

## 十二、经验教训

### 12.1 技术教训

1. **企微 4.x → 5.x 是架构级变化**
   - 4.x: DirectUI 自绘 + CChatCtrl 控件暴露
   - 5.x: DirectUI 外壳 + CEF 内嵌浏览器
   - 所有基于 4.x 代码的方案在 5.x 上全部失效

2. **"门卫检测"理论有版本局限性**
   - 微信 4.1.5.16 的 UIA 检测机制研究（2026-03）确实有价值
   - 但企微 5.x 不是"检测后决定暴露多少"，而是"控件根本不在原生层"
   - 教训：不能盲目将一个版本的研究结论套到另一个版本

3. **CEF 架构改变了游戏规则**
   - CEF 意味着聊天界面是 HTML/CSS/JS
   - UIA 方案在 CEF 架构下天然无效（DOM 不在原生控件树里）
   - 但 CEF 也带来了 CDP 这条更精准的路线

4. **先搞清架构再选方案**
   - 如果在验证#1 之前就调查了企微进程架构，可能会更早发现 CEF
   - 下次遇到"控件树空白"的情况，第一时间检查进程列表和 DLL 加载

### 12.2 工程教训

1. **.bat 文件必须用 CRLF + 纯 ASCII + 扁平 goto**
   - LF 换行 → cmd.exe 闪退
   - 嵌套括号块中的 `%ERRORLEVEL%` → stale 值
   - 非 ASCII 字符 → CP936 乱码
   - 这个坑已踩两次（Citrinitas VFY-005 + Nigredo run_verify_01）

2. **pythonnet DLL 搜索要全面**
   - .NET Framework DLL 可能在 WPF 子目录
   - GAC v4 路径与 GAC v2 路径不同
   - 应使用多级回退策略

3. **managed Python venv 和 system Python 的包不同步**
   - `psutil` 在 system Python 中有，managed Python 中没有
   - 需要使用 venv Python: `C:\Users\Lenovo\.workbuddy\binaries\python\envs\default\Scripts\python.exe`

---

## 十三、下一步计划

### 13.1 即时行动（用户侧，共约 5 分钟）

**行动 1：运行验证#2（键盘快捷键）**
- 路径：`D:\nigredo\scripts\run_verify_02.bat`
- 前置条件：打开一个有消息的群聊
- 运行中：不要碰键盘鼠标（约 15 秒）
- 产出：`scripts/output/verify_02_keyboard.txt`

**行动 2：在企微中按 F12**
- 打开企微 → 进入一个群聊 → 按 F12（或 Ctrl+Shift+I）
- 观察是否弹出 DevTools 开发者工具窗口
- 如果弹出 → 路线 E 大幅可行
- 如果无反应 → 继续其他 CDP 开启方式

### 13.2 短期计划（AI 侧）

1. **分析验证#2 结果** — 根据报告判断路线 B 可行性
2. **CEF DevTools 深入探索** — 如果 F12 无效，研究其他开启 CDP 的方式
3. **如果路线 E 可行** — 设计 CDP 客户端架构，编写 DOM 查询脚本
4. **如果路线 B 可行** — 设计键盘+剪贴板方案的完整实现

### 13.3 中期计划

1. **Phase 3: 完整实现** — 按选定路线实现 6 大模块
   - 连接模块 / 读取模块 / 监控模块 / 解析模块 / 通知模块 / 接口模块
2. **Phase 4: 验收** — 6 项验收标准测试
   - 自动捕获 / 消息提取 / 手机通知 / 不打扰 / 稳定性 / 多群支持

### 13.4 版本路线

| 版本 | 状态 | 内容 |
|------|:--:|------|
| v0.1.0 | 🔄 | 企微群消息采集方案调研（当前） |
| v0.2.0 | ⬜ | 自动回复 |
| 后续 | ⬜ | 其他平台采集（小红书/B站/电商） |

---

*本归档基于 2026-06-30 01:30 前的全部研究、验证和发现整理。下次工作前必读。*
