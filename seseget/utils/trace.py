import logging
from logging import Formatter, LogRecord, StreamHandler
from .output import ssg_stdout
from ..config import settings


class SSGFormatter(Formatter):
    COLOR_MAP = {
        logging.DEBUG: "\033[36m",  # 青色
        logging.INFO: "\033[0m",  # 默认
        logging.WARNING: "\033[33m",  # 黄色
        logging.ERROR: "\033[31m",  # 红色
        logging.CRITICAL: "\033[31;1m"  # 亮红色
    }
    RESET = "\033[0m"

    def __init__(self):
        # 定义不同等级的格式模板
        super().__init__()
        asctime_str = "[%(asctime)s] " if settings.LOG_SHOW_TIMESTAMP else ""
        levelname_str = "[%(levelname)s] " if settings.LOG_SHOW_LEVEL else ""
        self._formats = {
            logging.DEBUG: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s",
            logging.INFO: asctime_str + levelname_str + "%(message)s",
            logging.WARNING: asctime_str + levelname_str + "%(message)s",
            logging.ERROR: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s",
            logging.CRITICAL: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s"
        }

        # 统一日期格式
        self._datefmt = "%d/%b/%Y %H:%M:%S"

    def format(self, record: LogRecord) -> str:
        # 动态选择格式模板
        formatter = logging.Formatter(
            fmt=self._formats.get(record.levelno, self._formats[logging.DEBUG]),
            datefmt=self._datefmt
        )

        # 添加颜色
        color = self.COLOR_MAP.get(record.levelno, "")
        return f"{color}{formatter.format(record)}{self.RESET}"


class SSGStreamHandler(StreamHandler):
    def emit(self, record: LogRecord) -> None:
        try:
            # 获取 end 参数（默认为 \n）
            end = getattr(record, "end", "\n")
            msg = self.format(record) + end  # 添加自定义结尾

            # 输出到控制台
            ssg_stdout.write(msg)
            self.flush()
        except Exception as e:
            self.handleError(record)


class SSGLogger:
    def __init__(self, name, level=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level if level else settings.LOG_LEVEL)  # 设置日志级别
        self.stream_handler = SSGStreamHandler()
        formatter = SSGFormatter()

        name_str = f"[{name}] " if settings.LOG_SHOW_LOGGER_NAME else ""
        asctime_str = "[%(asctime)s] " if settings.LOG_SHOW_TIMESTAMP else ""
        levelname_str = "[%(levelname)s] " if settings.LOG_SHOW_LEVEL else ""
        formatter._formats = {
            logging.DEBUG: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s",
            logging.INFO: f"{name_str}{asctime_str}{levelname_str}%(message)s",
            logging.WARNING: f"{name_str}{asctime_str}{levelname_str}%(message)s",
            logging.ERROR: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s",
            logging.CRITICAL: f"{name_str}{asctime_str}{levelname_str}[%(filename)s:%(lineno)d] %(message)s"
        }

        # 创建控制台处理器
        self.stream_handler.setFormatter(formatter)  # 应用动态格式

        # 只保留一个处理器避免重复输出
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        self.logger.addHandler(self.stream_handler)

    def log(self, level, msg, end="\n", stacklevel=2, *args, ** kwargs):
        extra = {"end": end}
        self.logger.log(level, msg, extra=extra, stacklevel=stacklevel)

    def debug(self, msg: str, end="\n", *args, ** kwargs):
        self.log(logging.DEBUG, msg, end=end, stacklevel=3)

    def info(self, msg: str, end="\n", *args, ** kwargs):
        self.log(logging.INFO, msg, end=end, stacklevel=3)

    def warning(self, msg: str, end="\n", *args, ** kwargs):
        self.log(logging.WARNING, msg, end=end, stacklevel=3)

    def error(self, msg: str, end="\n", *args, ** kwargs):
        self.log(logging.ERROR, msg, end=end, stacklevel=3)

    def critical(self, msg: str, end="\n", *args, ** kwargs):
        self.log(logging.CRITICAL, msg, end=end, stacklevel=3)


logger = SSGLogger("seseGet")
