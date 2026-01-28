import subprocess
import logging
from .trace import logger, SSLogger
from ..config import settings


class CmdLogger(SSLogger):
    def rename(self, name: str):
        name_str = f"[{name}] " if settings.LOG_SHOW_LOGGER_NAME else ""
        asctime_str = "[%(asctime)s] " if settings.LOG_SHOW_TIMESTAMP else ""
        levelname_str = "[%(levelname)s] " if settings.LOG_SHOW_LEVEL else ""
        self.stream_handler.formatter._formats = {
            logging.DEBUG: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s",
            logging.INFO: f"{name_str}{asctime_str}{levelname_str}%(message)s",
            logging.WARNING: f"{name_str}{asctime_str}{levelname_str}%(message)s",
            logging.ERROR: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s",
            logging.CRITICAL: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s"
        }


cmd_logger = CmdLogger("exec_cmd")


def exec_cmd(command: list):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="ignore"
    )

    try:
        cmd_logger.rename(command[0])
        while True:
            line = process.stdout.readline()
            if line:
                cmd_logger.info(line, end="")
            if not line and process.poll() is not None:
                break

        return_code = process.wait()

        if return_code == 0:
            return True
        else:
            logger.error(f"命令执行失败，返回码[{return_code}]，命令{command}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("命令执行超时")
        process.kill()
        return False
    except FileNotFoundError:
        logger.error("找不到命令文件")
        return False
    except Exception as e:
        logger.error(f"执行命令时发生错误: {str(e)}")
        return False
