"""
⚗️ Nigredo — 任务队列（方案A：AI 写入，用户开机自动处理）

设计：共享队列文件 data/queue.json。AI（或任何外部程序）调用 enqueue(url)
把待处理地址写入队列；用户双击 run.bat 时，run_queue.py 在启动 UI 前
drain 队列逐个处理，无需手动粘贴。
"""
import json
from pathlib import Path

QUEUE_FILE = Path(__file__).resolve().parent.parent / "data" / "queue.json"


def enqueue(url: str) -> int:
    """把待处理地址写入共享队列，返回队列长度（去重）"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    items = _read()
    if url not in items:
        items.append(url)
        _write(items)
    return len(items)


def drain_queue() -> list:
    """取出队列中所有地址并清空（供开机自动处理）"""
    items = _read()
    _write([])
    return items


def _read() -> list:
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(items: list) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
