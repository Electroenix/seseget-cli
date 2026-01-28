import signal
import time
import multiprocessing

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from seseget.utils.trace import logger
from seseget.config.settings import WORKER_PROGRESS_TERMINAL_TIMEOUT
from seseget.cli import process_worker


if __name__ == "__main__":
    def handle_signal(signum, frame):
        wait_cnt = 0
        while wait_cnt < WORKER_PROGRESS_TERMINAL_TIMEOUT:
            if p_worker.is_alive():
                logger.debug(f"检测{wait_cnt}次，工作进程未退出")
                time.sleep(1)
                wait_cnt = wait_cnt + 1
            else:
                logger.debug(f"检测{wait_cnt}次，工作进程已退出")
                break
        else:
            logger.debug(f"强制关闭工作进程")
            p_worker.terminate()

        exit(0)

    signal.signal(signal.SIGINT, handle_signal)

    p_worker = multiprocessing.Process(target=process_worker, daemon=True)
    p_worker.start()
    while p_worker.is_alive():
        time.sleep(1)
