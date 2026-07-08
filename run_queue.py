"""
⚗️ Nigredo — 队列处理器（方案A）

由 run.bat 在启动 UI 前调用：drain 队列里所有待处理地址，自动调用蒸馏
管道处理，无需用户手动粘贴。单个地址处理失败不影响后续地址与 UI 启动。
"""
import sys
import logging
from pathlib import Path

# 允许从项目根目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.queue import drain_queue
from core.downloader import DownloadManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_queue")


def main() -> int:
    urls = drain_queue()
    if not urls:
        logger.info("队列为空，无待处理任务。")
        return 0
    logger.info(f"队列中有 {len(urls)} 个待处理地址，开始自动处理...")
    dm = DownloadManager()
    ok = 0
    for url in urls:
        try:
            logger.info(f"处理: {url}")
            result = dm.process(url)
            logger.info(f"完成: {url} -> status={result.get('status')}")
            ok += 1
        except Exception as e:
            logger.error(f"处理失败 {url}: {e}")
    logger.info(f"队列处理结束：成功 {ok}/{len(urls)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
