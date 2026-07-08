# wx_work_auto 完整源码分析

> 2026-06-30 | 馏析项目 — 步骤4深入调研
> 来源: https://github.com/yangyuexiong/wx_work_auto
> 最后更新: 2025-08-03 | MPL-2.0 协议 | 企微版本: 4.1.39.x

---

## 一、项目概述

这是一个专门针对**企业微信 PC 端 4.1.39.x** 的自动化工具。作者明确指出了核心难题：

> 企微 4.1 使用 **DirectUI**（自绘界面）技术，控件不暴露标准的 UI Automation Patterns（如 Invoke、Value、TextPattern），导致大多数自动化工具无法直接操控它。

作者提供了三种解决方案：
1. **组合键 + 穿透**（推荐）
2. **降级到 3.1.10**（老版本控件树完整）
3. **uiautomation + PyAutoGUI 图像识别**（不稳定，受分辨率影响）

---

## 二、完整源码

### 2.1 main.py — 核心自动化引擎

```python
# -*- coding: utf-8 -*-
import os
import time

import pyautogui
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys

ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets')


class WXWorkDict:
    """键盘快捷键常量"""
    ENTER = "{ENTER}"
    MESSAGE_KEY = "^1"        # Ctrl+1 → 切换到消息tab
    CONTACTS_KEY = "^8"       # Ctrl+8 → 切换到通讯录tab
    CF = "^f"                 # Ctrl+F → 搜索
    ESC = "{ESC}"
    DLG_DICT = {
        "主窗口": {
            "title": "企业微信",
            "class_name": "WeWorkWindow"
        },
        "通讯录": {
            "title": "企业微信-通讯录",
            "class_name": "WXworkWindow - 企业微信-通讯录"
        },
    }


class WXWorkAuto:
    """企业微信4.1.39.x"""

    def __init__(self, path: str):
        # 启动企微（backend='uia' 使用 Windows UI Automation 后端）
        self.app = Application(backend='uia').start(path)
        if not self.app.windows():
            # 如果已经运行，则连接现有进程
            self.app = Application(backend='uia').connect(path=path)

        self.main_dlg = None
        self.init_dlg = self.gen_dlg(widget_key="主窗口")

    def gen_dlg(self, widget_key: str):
        """切换当前窗口"""
        widget_obj = WXWorkDict.DLG_DICT.get(widget_key)
        if not widget_obj:
            raise KeyError("not widget_key")

        title = widget_obj.get('title')
        class_name = widget_obj.get('class_name')
        dlg_handles = findwindows.find_windows(title=title, class_name=class_name)

        if dlg_handles:
            self.main_dlg = self.app.window(handle=dlg_handles[0])
            self.main_dlg.wait('ready', timeout=10)
            self.main_dlg.restore()   # 恢复窗口（从最小化）
            self.main_dlg.set_focus() # 聚焦
            return self.main_dlg
        else:
            raise IndexError(f'获取 {title} 窗口失败')

    def close(self, *args, **kwargs):
        """最小化窗口"""
        send_keys(WXWorkDict.ESC)

    def find_and_click(self, image_name, confidence=0.8, click_offset=(0, 0)):
        """在屏幕上找图片，并点击（图像识别方案）"""
        image_path = os.path.join(ASSET_DIR, image_name)
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)

        if location is None:
            raise Exception(f'无法找到 {image_name}，请检查截图是否正确。')

        center_x, center_y = pyautogui.center(location)
        click_x = center_x + click_offset[0]
        click_y = center_y + click_offset[1]

        pyautogui.moveTo(click_x, click_y, duration=0.2)
        pyautogui.click()
        time.sleep(0.5)

    def message_tab(self):
        """切换到消息tab —— 用键盘快捷键 Ctrl+1"""
        self.main_dlg.type_keys(WXWorkDict.MESSAGE_KEY)

    def contacts_tab(self):
        """切换到通讯录tab —— 用键盘快捷键 Ctrl+8"""
        self.main_dlg.type_keys(WXWorkDict.CONTACTS_KEY)

    def send_message(self, name: str, message: str):
        """
        发送消息的完整流程（组合键方案）:
        1. Ctrl+1 → 消息tab
        2. Ctrl+F → 搜索框
        3. 输入联系人名称
        4. 回车 → 进入聊天
        5. 输入消息内容
        6. 回车 → 发送
        7. ESC → 最小化
        """
        self.message_tab()                    # 步骤1
        self.main_dlg.type_keys(WXWorkDict.CF)  # 步骤2
        send_keys(name)                       # 步骤3
        time.sleep(1)
        send_keys(WXWorkDict.ENTER)           # 步骤4
        send_keys(message)                    # 步骤5
        send_keys(WXWorkDict.ENTER)           # 步骤6
        print(f"{name} 消息已发完成")
        self.close()                          # 步骤7
        print("最小化")

    def test_c(self):
        """测试组合点击 —— 图像识别+键盘混合方案"""
        self.find_and_click("txl.png")        # 图像识别找到通讯录图标
        self.find_and_click("txl_search.png") # 图像识别找到搜索框
        send_keys("yyx")
        time.sleep(1)
        send_keys(WXWorkDict.ENTER)
        send_keys("组合测试")
        send_keys(WXWorkDict.ENTER)
```

### 2.2 utils.py — 工具函数

```python
# -*- coding: utf-8 -*-
import psutil


def get_pid(name: str):
    """通过进程名获取进程ID"""
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == name.lower():
                print(proc.pid)
                return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return -1
```

### 2.3 test/t1.py — 核心：消息读取（最关键的文件）

```python
# -*- coding: utf-8 -*-
import time

from pywinauto.timings import Timings
from main import WXWorkAuto
from utils import get_pid

# 设置全局超时时间
Timings.window_find_timeout = 2  # 单位：秒


# ============================================================
# 核心技术 #1: 通过进程ID + 类名直接查找 DirectUI 控件
# ============================================================
def get_real_content(main_win):
    """
    绕过企微的 WeWorkWindow 装饰层，直接找到消息容器的 CChatCtrl 控件。
    
    关键发现: 企微 4.1 虽然用了 DirectUI，但 CChatCtrl 控件仍暴露在
    UIA 控件树中（只是不暴露标准 Patterns）。可以通过进程ID + 类名搜索到。
    """
    from pywinauto.findwindows import find_elements

    content_window = find_elements(
        process=main_win.process_id(),   # 按进程ID搜索（不依赖窗口层级）
        class_name="CChatCtrl",           # 消息容器的类名
        control_type="Pane",              # 控件类型是面板
        depth=3                           # 搜索深度（不用太深）
    )
    return content_window[0] if content_window else None


# ============================================================
# 核心技术 #2: 坐标穿透（最后手段）
# ============================================================
def click_through_decorations():
    """
    企微 4.1.39 内容区域典型坐标——硬编码点击位置。
    这是 DirectUI 无法通过控件树定位时的最后手段。
    """
    rect = main_win.rectangle()
    click_points = [
        (rect.left + 100, rect.top + 150),   # 左侧导航
        (rect.left + 300, rect.top + 200)    # 主消息区
    ]
    for x, y in click_points:
        main_win.click_input(coords=(x, y))
        time.sleep(0.5)


# ============================================================
# 核心技术 #3: 读取未读消息
# ============================================================
def get_unread_messages():
    """
    完整的消息读取流程:
    1. 切换到消息tab
    2. 找到 CChatCtrl 消息容器
    3. 滚动加载更多消息
    4. 通过正则匹配找到未读标记
    5. 提取发送人和消息内容
    """
    try:
        # 步骤1: 激活消息标签
        try:
            main_win.child_window(
                title="消息",
                control_type="TabItem"
            ).click_input()
        except:
            main_win.type_keys("^t")  # Ctrl+T 切换

        time.sleep(1)

        # 步骤2: 获取消息容器
        container = get_real_content()
        if not container:
            # 如果 CChatCtrl 找不到，使用坐标穿透
            click_through_decorations()
            container = get_real_content()

        if container:
            # 步骤3: 滚动加载
            for _ in range(2):
                container.scroll("down", "page")
                time.sleep(0.5)

            # 步骤4: 识别未读消息（正则匹配数字+未读文本）
            unreads = []
            badges = container.descendants(
                control_type="Text",
                name_re="[0-9]+条?未读?"
            )

            # 步骤5: 提取每条未读消息的详细信息
            for badge in badges:
                try:
                    msg_item = badge.parent().parent()  # 向上两级找到消息项
                    sender = msg_item.children()[0].window_text()   # 发送人
                    content = msg_item.children()[1].window_text()  # 消息内容
                    count = int(''.join(filter(str.isdigit, badge.window_text())))

                    unreads.append({
                        "sender": sender,
                        "preview": content,
                        "count": count,
                        "element": badge
                    })
                except Exception as e:
                    print(f"解析错误: {str(e)}")

            return unreads

    except Exception as e:
        print(f"致命错误: {str(e)}")
        return []


# ============================================================
# 主入口：调试代码
# ============================================================
if __name__ == '__main__':
    app_path = "D:\WXWork\WXWork.exe"
    app_pid = get_pid(name='WXWork.exe')
    wx_work_auto = WXWorkAuto(path=app_path)

    main_win = wx_work_auto.main_dlg

    print("主窗口标题:", main_win.window_text())
    print("窗口句柄:", main_win.handle)

    # 打印控件树（注释掉的调试代码）
    # all_controls = main_win.descendants()
    # for i, ctrl in enumerate(all_controls[:20]):
    #     print(f"控件 {i}:")
    #     print(f"  类名: {ctrl.class_name()}")
    #     print(f"  类型: {ctrl.friendly_class_name()}")
    #     print(f"  标题: {ctrl.window_text()}")
    #     print(f"  AutomationID: {ctrl.automation_id()}")

    print(get_real_content(main_win))
```

### 2.4 test/t2.py — 纯 uiautomation 方案

```python
# -*- coding: utf-8 -*-
"""
使用 uiautomation 库直接操作企微（不需要 pywinauto 包装层）。
这个方案在企业微信 3.x 版本效果最好，4.x 需要测试。
"""
import uiautomation as auto

# 连接企业微信主窗口
wx = auto.WindowControl(searchDepth=1, ClassName="WeWorkWindow")
wx.SetActive()

# 找到搜索框
search_box = wx.EditControl(Name='搜索')
search_box.Click()
search_box.SendKeys('同事名字', waitTime=0.5)

# 等待搜索结果弹出，找到第一个联系人
contact = wx.ListItemControl(foundIndex=1)
contact.Click()

# 找到输入框
input_box = wx.EditControl(foundIndex=2)
input_box.Click()
input_box.SendKeys('你好，这是自动发送的消息', waitTime=0.5)

# 找到发送按钮并点击
send_button = wx.ButtonControl(Name='发送')
send_button.Click()

if __name__ == '__main__':
    pass
```

### 2.5 test/t3.py — PyAutoGUI 图像识别方案

```python
# -*- coding: utf-8 -*-
"""
图像识别 + 键盘模拟的混合方案。
适用于 DirectUI 控件完全不可访问时的降级方案。
"""
import os
import time

import pyautogui
import uiautomation as auto

ASSET_DIR = os.path.join(os.path.dirname(__file__), '../assets')


def find_and_click(image_name, confidence=0.8, click_offset=(0, 0)):
    """在屏幕上找图片并点击"""
    image_path = os.path.join(ASSET_DIR, image_name)
    location = pyautogui.locateOnScreen(image_path, confidence=confidence)

    if location is None:
        raise Exception(f'无法找到 {image_name}，请检查截图是否正确。')

    center_x, center_y = pyautogui.center(location)
    click_x = center_x + click_offset[0]
    click_y = center_y + click_offset[1]

    pyautogui.moveTo(click_x, click_y, duration=0.2)
    pyautogui.click()
    time.sleep(0.5)


def main():
    print("开始执行企业微信自动发消息...")

    # 确保企业微信窗口置前
    wx_window = auto.GetForegroundControl()
    print(f"当前前台窗口: {wx_window.Name} | {wx_window.ClassName}")

    time.sleep(1)

    # 1. 通过图像识别点击通讯录图标
    find_and_click('txl.png', confidence=0.9)

    # 2. 键盘输入联系人名称
    pyautogui.write('测试联系人', interval=0.05)
    pyautogui.press('enter')
    time.sleep(1)

    print("消息发送完成！")


if __name__ == "__main__":
    main()
```

### 2.6 test/test_get_properties.py — 控件树侦查工具

```python
# -*- coding: utf-8 -*-
"""
调试工具：枚举企微窗口的所有子控件，查看其属性和类型。
用于发现可用的控件定位方式。
"""

def test(wx_work_auto):
    """调试代码"""
    print(wx_work_auto.main_dlg)
    print(wx_work_auto.main_dlg.children())

    # 逐个打印子控件的属性
    for child in wx_work_auto.main_dlg.children():
        print(f"get_properties: {child.get_properties()}")
        print(f"控件类型: {child.friendly_class_name()}")
        print(f"标题: {child.window_text()}")
        print(f"自动化ID: {child.automation_id()}")
        print("-" * 50)

    main_window = wx_work_auto.app.window(
        class_name="WeWorkWindow",
        visible_only=True
    )
    print(main_window)

    # 方法：直接查找 QWidget 内容区（企微4.1典型结构）
    content = main_window.child_window(
        class_name="QWidget",      # 企业微信主内容区类名
        control_type="Pane",
        found_index=0
    )
    print(content)

    if content.exists():
        real_content = content.wrapper_object()
        print("成功穿透装饰层，内容区域属性：")
        print(f"类名: {real_content.class_name()}")
        print(f"矩形区域: {real_content.rectangle()}")
        print(f"子控件数: {len(real_content.children())}")
    else:
        print("穿透失败，尝试备用方案...")


if __name__ == '__main__':
    pass
```

### 2.7 test/test_send_message.py — 消息发送示例

```python
# -*- coding: utf-8 -*-
import datetime

from main import WXWorkAuto
from utils import get_pid

if __name__ == '__main__':
    app_path = "D:\WXWork\WXWork.exe"
    app_pid = get_pid(name='WXWork.exe')
    wx_work_auto = WXWorkAuto(path=app_path)

    # 发送文本消息
    # wx_work_auto.send_message("yyx", f"你好:{datetime.datetime.now()}")

    # 或者用图像识别+键盘的组合方案
    wx_work_auto.test_c()
```

---

## 三、核心技术总结

### 技术 #1: 组合键 + find_elements 穿透

```
Ctrl+1 (消息tab) → Ctrl+F (搜索) → 输入名 → 回车 → 输入消息 → 回车
```

这是最稳定的方案，不依赖控件树结构变化，只要企微保留键盘快捷键就能工作。

### 技术 #2: CChatCtrl 控件直接搜索

```python
find_elements(
    process=pid,
    class_name="CChatCtrl",
    control_type="Pane",
    depth=3
)
```

**关键发现**：虽然企微 4.1 用了 DirectUI 隐藏大部分控件，但 `CChatCtrl` 控件仍然暴露在 UIA 控件树中。可以通过「进程ID + 类名」直接搜索到，绕过 WeWorkWindow 的装饰层。

### 技术 #3: 图像识别 (PyAutoGUI)

```python
pyautogui.locateOnScreen('txl.png', confidence=0.9)
```

优点是不依赖任何控件树，缺点是受分辨率、窗口大小、遮挡影响，`confidence=0.9` 需要提前截图。

### 技术 #4: QWidget 穿透

```python
main_window.child_window(class_name="QWidget", control_type="Pane")
```

企微底层用 Qt 框架（类名 QWidget），可以通过类名穿透 DirectUI 装饰层。

---

## 四、对我们项目的启示

### 可用的技术路线

| 技术 | 难度 | 稳定性 | 适用 |
|------|------|--------|------|
| **组合键** (Ctrl+1/2/8 + Ctrl+F) | 低 | ⭐⭐⭐⭐⭐ | 发消息、导航 |
| **find_elements + CChatCtrl** | 中 | ⭐⭐⭐ | 读消息列表 |
| **QWidget 穿透** | 中 | ⭐⭐⭐ | 读取内容区 |
| **图像识别** (PyAutoGUI) | 低 | ⭐⭐ | 点击固定元素 |
| **坐标硬编码** | 低 | ⭐ | 最后手段 |

### 读取消息的完整技术链

```
1. pywinauto(backend='uia').connect → 连接企微进程
2. find_elements(process=pid, class_name="CChatCtrl") → 找到消息容器
3. container.descendants(name_re="[0-9]+条?未读?") → 找到未读标记
4. badge.parent().parent() → 向上两级找到消息项
5. msg_item.children()[0].window_text() → 发送人
6. msg_item.children()[1].window_text() → 消息内容
```

### 需要验证的问题

1. **CChatCtrl 在当前企微版本（5.x）是否仍然存在？** — 企微可能已经改变类名或控件结构
2. **descendants() 能否遍历到消息列表中的每条消息？** — t1.py 中只读了未读标记，没读完整消息
3. **QWidget 穿透在当前版本是否工作？** — Qt 版本可能升级
4. **send_keys() 的稳定性？** — 中英文输入、特殊字符

---

## 五、下一步

基于 wx_work_auto 的代码，我们的验证计划：

1. 写一个 **侦查脚本**：枚举当前企微的所有控件（类名、类型、标题），确认 CChatCtrl 是否存在
2. 写一个 **读取原型**：基于 t1.py 的 get_real_content + get_unread_messages 逻辑
3. 写一个 **发送原型**：基于 main.py 的 send_message 逻辑（组合键方案）
4. 测试稳定性：跑 24 小时看看会不会崩溃

*本分析基于 2026-06-30 从 GitHub 获取的完整源码。*
