"""
⚗️ Nigredo — 队列常驻消费器（模块 B2 / B3 / B4）

由巨作 launcher 以 DETACHED 启动：关巨作网页也不会杀掉本进程（薄壳原则）。
单消费者：用「角色(role) + 心跳(hb)」锁(data/queue_consumer.lock) 保证只有一个消费进程常驻。
   - 锁文件写 {"pid", "role": "nigredo", "hb", "started"}（JSON），不再只写裸 PID。
   - 心跳由独立线程每几秒刷新，故下载/语音识别等长时间处理期间锁依然新鲜，
     总管不会误判「僵尸」而杀掉正在干活的消费者。
   - 身份判定用「角色 + 心跳」而非裸 PID，根治 PID 复用 / SIGKILL 孤儿锁 / 僵尸 三类击穿（缺陷 A）。
循环逻辑：
  1. recover_stale()       回收崩溃残留的 processing 项
  2. claim_next(pid)       取一个 pending → processing
  3. dm.process(url)        真实处理（馏析全链路）
  4. complete(url)         成功才出队（B3：不写 done 记录）
     fail(url)             失败重试，超限丢弃（B4）
无待处理时短暂 sleep，不退出（常驻，满足"馏析跑完一个就录入下一个"）。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

# 允许从项目根直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.queue import (  # noqa: E402
    claim_next,
    complete,
    fail,
    recover_stale,
    _pid_alive,
)
from core.downloader import DownloadManager  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_queue")

PID_FILE = Path(__file__).resolve().parent / "data" / "queue_consumer.lock"
# 角色标识：写入锁文件，供总管用「角色 + 心跳」识别本服务实例（根治 PID 复用误判）
ROLE = "nigredo"
HB_INTERVAL = 5.0      # 心跳线程刷新间隔（秒）
HB_TIMEOUT = 60.0      # _already_running 判定「锁有效」的心跳新鲜阈值（秒）
EMPTY_SLEEP = 2.0        # 空队列轮询间隔
RECOVER_EVERY = 30       # 每 30 个空轮做一次 stale 回收
SUCCESS_STATUS = ("done", "cached")
FAIL_STATUS = ("failed", "error", "fail", "failed_subtitle")

_hb_stop = threading.Event()


def _write_lock() -> None:
    """写入/刷新「角色 + 心跳」锁文件。"""
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "pid": os.getpid(),
            "role": ROLE,
            "hb": time.time(),
            "started": time.time(),
        }
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def _read_lock():
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return None
        try:
            d = json.loads(raw)
            if isinstance(d, dict) and "pid" in d:
                d.setdefault("role", None)
                d.setdefault("hb", 0.0)
                d.setdefault("started", 0.0)
                return d
        except Exception:
            # 兼容旧格式（纯整数 PID）
            return {"pid": int(raw), "role": None, "hb": 0.0, "started": 0.0}
    except Exception:
        return None
    return None


def _hb_loop() -> None:
    """心跳线程：进程活着就持续刷新锁的 hb，让「心跳」成为可靠的存活信号。"""
    while not _hb_stop.is_set():
        _write_lock()
        _hb_stop.wait(HB_INTERVAL)


def _already_running() -> bool:
    """用「角色 + 心跳」判定是否已有本服务实例在跑（不再只认裸 PID）。

    只有「锁里角色匹配本服务 且 PID 存活 且 心跳新鲜」才算真在跑；
    PID 被复用 / 进程已死 / 心跳超时 都视为锁已失效 → 本进程可安全接管。
    """
    info = _read_lock()
    if not info:
        return False
    pid = info.get("pid")
    if pid is None or pid == os.getpid():
        return False
    if info.get("role") != ROLE:
        # 角色不符（外来进程复用 PID 占用锁文件）→ 锁失效，可接管
        return False
    if not _pid_alive(pid):
        return False
    if (time.time() - info.get("hb", 0)) > HB_TIMEOUT:
        # 心跳超时（僵尸/孤儿）→ 锁失效，可接管
        return False
    return True


def main() -> int:
    if _already_running():
        logger.warning("队列消费器已在运行（角色+心跳锁有效），本进程退出，避免双消费者串处理。")
        return 0

    _write_lock()
    _hb_stop.clear()
    threading.Thread(target=_hb_loop, daemon=True).start()
    logger.info(f"队列消费器启动（pid={os.getpid()}）。")
    try:
        dm = DownloadManager()
        recover_stale()
        empty_rounds = 0
        while True:
            url = claim_next(pid=os.getpid())
            if url is None:
                empty_rounds += 1
                if empty_rounds >= RECOVER_EVERY:
                    n = recover_stale()
                    if n:
                        logger.info(f"回收崩溃残留 {n} 项 → pending")
                    empty_rounds = 0
                time.sleep(EMPTY_SLEEP)
                continue

            empty_rounds = 0
            logger.info(f"▶ 开始处理: {url}")
            try:
                result = dm.process(url)
                status = result.get("status") if isinstance(result, dict) else "done"
                if status in FAIL_STATUS:
                    will_retry = fail(url)
                    logger.warning(
                        f"✗ 处理未成功(status={status})，"
                        f"{'退回重试' if will_retry else '已超限丢弃'}: {url}"
                    )
                else:
                    complete(url)
                    logger.info(f"✓ 完成并出队: {url} (status={status})")
            except Exception as e:
                will_retry = fail(url)
                logger.error(
                    f"✗ 处理异常: {e}，"
                    f"{'退回重试' if will_retry else '已超限丢弃'}: {url}"
                )
    finally:
        _hb_stop.set()
        try:
            info = _read_lock()
            if info and info.get("pid") == os.getpid() and info.get("role") == ROLE:
                PID_FILE.unlink()
        except OSError:
            pass
        logger.info("队列消费器退出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
