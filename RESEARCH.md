# Nigredo · 馏析 — 技术方案调研报告

> v1.0 | 2026-06-28 | wechat-decrypt + UIA自动化 深入调研

---

## 一、wechat-decrypt 方案（#12）

### 1.1 工具基本信息

| 项目 | 内容 |
|------|------|
| 仓库 | `ylytdeng/wechat-decrypt` |
| Stars | 4252 ⭐ |
| Forks | 2230 |
| 最后更新 | 2026-06-27（昨天！） |
| 开源协议 | **无**（商用需联系作者授权） |
| 语言 | Python |
| Windows支持 | ✅ 完整支持（需管理员权限） |

### 1.2 企微支持情况

| 项目 | 内容 |
|------|------|
| 支持状态 | ✅ Windows 企业微信 5.x 实测可用（实验性质） |
| Mac 企微 | ❌ 不支持（Issues #139/#130 确认） |
| Linux 企微 | ❌ 不支持 |
| 企微加密方案 | wxSQLite3（不同于个人微信的 SQLCipher 4） |
| 加密算法 | AES-128-CBC，MD5 per-page 派生，无 HMAC |
| Key 长度 | 16 字节 raw key（个人微信是 64hex+32hex） |

### 1.3 使用步骤

```bash
# 1. 以管理员身份打开终端（必须，读取进程内存需要）
# 2. 确保企业微信已登录且正在运行
# 3. 提取密钥
python find_wxwork_keys.py
# → 自动检测 Documents\WXWork\<id>\Data
# → 输出到 wxwork_keys.json

# 4. 解密数据库
python decrypt_wxwork_db.py
# → 解密到 wxwork_decrypted/

# 5. 导出消息（可选）
python export_wxwork_messages.py
# → 支持 CSV / HTML / JSON

# 6. Web UI（推荐）
python monitor_web.py
# → 自动打开 http://localhost:5678
# → 企微 Tab：解密 / 导出聊天
```

### 1.4 实时监控方案

`monitor_web.py` 提供 SSE（Server-Sent Events）实时消息推送：
- 监听数据库文件变化
- 新消息到达时推送到 Web UI
- 可以作为数据源接入 Nigredo 采集管道

### 1.5 风险分析

| 风险项 | 严重程度 | 说明 |
|--------|---------|------|
| **封号风险** | 🔴 高 | Issue #140 确认：使用工具后被微信判定为外挂封号 |
| **企微版本更新** | 🟡 中 | 如果企微改内存结构，密钥提取会失效（类似微信 4.1+ 的问题） |
| **无开源协议** | 🟡 中 | 商用需联系作者授权，否则侵权 |
| **明文密钥文件** | 🟡 中 | `wxwork_keys.json` 包含明文 key，需妥善保管 |
| **解密后数据合规** | 🟡 中 | 解密后的数据库包含完整聊天记录，需符合《个人信息保护法》 |

### 1.6 结论

| 优势 | 劣势 |
|------|------|
| ✅ 免费（个人使用） | ❌ 封号风险（真实案例） |
| ✅ 不需要企微窗口打开 | ❌ 企微版本更新可能失效 |
| ✅ 数据完整（含历史消息） | ❌ 无开源协议，商用需授权 |
| ✅ 有 Web UI 和 MCP Server | ❌ 仅 Windows 支持企微 |
| ✅ 活跃维护（昨天刚更新） | ❌ 实验性质，不稳定 |

---

## 二、UIA自动化方案（#13）

### 2.1 技术原理

Windows UI Automation（UIA）是微软提供的无障碍接口，允许程序读取和控制其他程序的 UI 元素。

企微使用标准 Windows UI 技术构建，且**尚未像个人微信那样屏蔽 UI 树**（知乎文章证实），所以可以用 `pywinauto` 或 `uiautomation` 库控制。

### 2.2 实现方案

```python
import pywinauto
from pywinauto import Desktop, Application

# 1. 连接企微窗口
app = Application(backend="uia").connect(title="企业微信")

# 2. 定位搜索框（需要知道 auto_id 或 search_properties）
search_box = app.window(title="企业微信").child_window(auto_id="SearchEdit")

# 3. 输入群名
search_box.type_keys("接单群")

# 4. 按回车
search_box.type_keys("{ENTER}")

# 5. 定位消息列表（需要先用 Inspect.exe 查看元素树）
msg_list = app.window(title="企业微信").child_window(auto_id="MessageList")

# 6. 读取消息（遍历 msg_list 的子元素）
messages = msg_list.children()
for msg in messages:
    print(msg.window_text())

# 7. 实时监控（轮询或事件监听）
# 方案 A：定时轮询消息列表
# 方案 B：Windows Event Hook（复杂）
```

### 2.3 需要解决的问题

| 问题 | 难度 | 说明 |
|------|------|------|
| **元素定位** | 🟡 中 | 需要用 Inspect.exe（Windows SDK）查看企微的 UI 树，找到搜索框、消息列表的 auto_id |
| **版本变化** | 🟡 中 | 企微更新可能改变 UI 元素结构，需要适配 |
| **实时监控** | 🟡 中 | 轮询有延迟，事件监听复杂 |
| **企微窗口必须打开** | 🟢 低 | 这是 UIA 的固有限制 |
| **群消息排序** | 🟡 中 | 需要判断新消息（时间戳 or 消息 ID） |

### 2.4 法律风险

✅ **低风险** — UIA 自动化是Windows 系统提供的正规接口，不破解、不解密，企微官方未明确禁止。

相比之下，wechat-decrypt 读取进程内存、解密数据库，法律风险更高。

### 2.5 结论

| 优势 | 劣势 |
|------|------|
| ✅ 免费（pywinauto 是开源库） | ❌ 需要企微窗口始终打开 |
| ✅ 低风险（系统正规接口） | ❌ 元素定位可能随版本变化 |
| ✅ 可以主动控制（发消息） | ❌ 实时监控有延迟（轮询） |
| ✅ MIT 协议（可商用） | ❌ 需要先用 Inspect.exe 分析企微 UI 树 |
| ✅ 不读内存、不解密，企微无法检测 | ❌ 只能读当前加载的消息（不能读历史） |

---

## 三、两个方案对比

| 对比项 | wechat-decrypt（本地数据库） | UIA自动化（pywinauto） |
|--------|---------------------------|---------------------------|
| **成本** | 免费（个人使用） | 免费（开源库） |
| **法律风险** | 🔴 高（封号案例） | 🟢 低（系统正规接口） |
| **企微版本依赖** | 🔴 高（版本更新可能失效） | 🟡 中（UI 变化需适配） |
| **是否需要企微窗口** | ✅ 不需要 | ❌ 需要 |
| **数据完整性** | ✅ 完整（含历史） | ❌ 仅当前加载的消息 |
| **实时监控** | ✅ 有（SSE 推送） | 🟡 轮询（有延迟） |
| **是否可以发消息** | ❌ 不能（只读） | ✅ 可以 |
| **开源协议** | ❌ 无（商用需授权） | ✅ MIT（可商用） |
| **维护状态** | ✅ 活跃（昨天更新） | ✅ pywinauto 活跃 |
| **产品化潜力** | ❌ 低（法律风险+无协议） | ✅ 高（低风险+MIT协议） |

---

## 四、推荐方案

### 推荐：UIA自动化（pywinauto）为主，wechat-decrypt 备用

**理由：**

1. **法律风险低**：UIA 是系统正规接口，企微无法检测，不会封号
2. **可以产品化**：MIT 协议，可以卖
3. **虽然需要企微窗口打开**，但这是可接受的限制（MVP 阶段）

**实施计划：**

| 阶段 | 方案 | 目的 |
|------|--------|------|
| **MVP（本周）** | UIA自动化 + 轮询 | 验证能不能读到消息 |
| **V2（下周）** | UIA自动化 + 事件监听 | 降低延迟 |
| **备用** | wechat-decrypt（如果 UIA 失效） | 读取历史消息或离线分析 |

---

## 五、下一步行动

1. ✅ **原型验证**：用 pywinauto 连接企微窗口，读取一个群的消息
2. ✅ **元素分析**：用 Inspect.exe 查看企微 UI 树，找到消息列表的元素属性
3. ✅ **实时监控**：实现轮询方案，每 5 秒检查新消息
4. ✅ **通知集成**：读到"好项目"关键词 → 手机通知
5. ⏳ **自动回复**（v0.2.0）：UIA 控制企微发送消息

---

## 六、参考资料

| 资源 | 链接 |
|------|------|
| wechat-decrypt 仓库 | https://github.com/ylytdeng/wechat-decrypt |
| wechat-cli（macOS 同类工具） | https://github.com/0xd219b/wechat-cli |
| pywinauto 文档 | https://pywinauto.readthedocs.io/ |
| Inspect.exe 下载（Windows SDK） | https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/ |
| 知乎：pywinauto 控制企微 | （搜索"pywinauto 企业微信"） |
| Issue #96：微信 4.1+ 密钥提取根因 | https://github.com/ylytdeng/wechat-decrypt/issues/96 |
| wcdb-key-tool（PBKDF2 方案） | https://github.com/TANGandXUE/wcdb-key-tool |

---

*本报告基于 2026-06-28 的公开资料整理。wechat-decrypt 的企微支持为实验性质，生产使用前需充分测试。*
