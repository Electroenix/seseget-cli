import signal
import multiprocessing
import time

from core.config import init, settings
from core.utils.trace import *
from core.main import process_worker


if __name__ == "__main__":
    def handle_signal(signum, frame):
        wait_cnt = 0
        while wait_cnt < settings.WORKER_PROGRESS_TERMINAL_TIMEOUT:
            if p_worker.is_alive():
                SESE_TRACE(LOG_DEBUG, f"检测{wait_cnt}次，工作进程未退出")
                time.sleep(1)
                wait_cnt = wait_cnt + 1
            else:
                SESE_TRACE(LOG_DEBUG, f"检测{wait_cnt}次，工作进程已退出")
                break
        else:
            SESE_TRACE(LOG_DEBUG, f"强制关闭工作进程")
            p_worker.terminate()

        exit(0)

    signal.signal(signal.SIGINT, handle_signal)

    p_worker = multiprocessing.Process(target=process_worker, daemon=True)
    p_worker.start()
    while p_worker.is_alive():
        time.sleep(1)
