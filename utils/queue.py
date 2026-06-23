"""
⚗️ Nigredo — 任务队列管理器
"""
from collections import deque
from dataclasses import dataclass, field
from typing import Callable
import time
import json


@dataclass
class Task:
    url: str
    video_id: str
    platform: str
    status: str = "pending"  # pending / downloading / transcribing / done / failed
    error: str = ""
    progress: float = 0.0     # 0-100
    result: dict = field(default_factory=dict)


class TaskQueue:
    """简单的 FIFO 任务队列"""

    def __init__(self):
        self._queue: deque[Task] = deque()
        self._history: list[Task] = []
        self._current: Task | None = None

    def add(self, task: Task) -> int:
        """添加任务，返回队列位置"""
        self._queue.append(task)
        return len(self._queue)

    def next(self) -> Task | None:
        """取出下一个任务"""
        if self._queue:
            return self._queue.popleft()
        return None

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    @property
    def current(self) -> Task | None:
        return self._current

    def mark_done(self, task: Task, result: dict = None):
        task.status = "done"
        task.progress = 100
        if result:
            task.result = result
        self._history.append(task)

    def mark_failed(self, task: Task, error: str):
        task.status = "failed"
        task.error = error
        self._history.append(task)

    def status_report(self) -> str:
        done = sum(1 for t in self._history if t.status == "done")
        failed = sum(1 for t in self._history if t.status == "failed")
        return f"队列: {self.pending_count} 待处理 | {done} 完成 | {failed} 失败"
